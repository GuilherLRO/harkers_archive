"""Dispatch dossier days and weekly notes into Postgres (Quincey's Dispatch)."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
import yaml
from dotenv import load_dotenv
from psycopg import OperationalError
from psycopg.types.json import Jsonb

_ARCHIVE_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ARCHIVE_ROOT / ".env")

MANIFEST_NAME = ".van_helsings_dossier_manifest.json"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
CONNECT_TIMEOUT_SECONDS = 10

DEFAULT_DOSSIER_DIR = Path(
    os.environ.get("HARKERS_DOSSIER_DIR", _ARCHIVE_ROOT / "dossier")
)
DEFAULT_RAINFIELDS_DIR = Path(
    os.environ.get("HARKERS_RAINFIELDS_DIR", _ARCHIVE_ROOT / "rainfields_mind")
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z",
    re.DOTALL,
)
WEEKLY_KEY_RE = re.compile(r"^(\d{4}-W\d{2})\.md$")
DOSSIER_KEY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


class ConfigurationError(Exception):
    """Missing or invalid local configuration."""


def load_database_url() -> str:
    url = os.environ.get("HARKERS_DATABASE_URL", "").strip()
    if not url:
        raise ConfigurationError(
            "HARKERS_DATABASE_URL is not set "
            "(e.g. postgresql://user:pass@localhost:5432/harkers)"
        )
    return url


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def parse_markdown(path: Path) -> tuple[dict[str, Any], str, str]:
    raw = path.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw, content_hash
    frontmatter_raw, body = match.group(1), match.group(2)
    try:
        loaded = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError:
        logger.warning("Could not parse frontmatter in %s; storing empty", path.name)
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {"_raw": loaded}
    return json_safe(loaded), body, content_hash


def title_from_frontmatter(frontmatter: dict[str, Any], fallback: str) -> str:
    title = frontmatter.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    week = frontmatter.get("week")
    if isinstance(week, str) and week.strip():
        return f"Rainfields Mind - {week.strip()}"
    return fallback


def ensure_schema(conn: psycopg.Connection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)
    conn.commit()
    logger.info("Schema ready")


def list_dossier_files(dossier_dir: Path) -> list[Path]:
    if not dossier_dir.is_dir():
        return []
    return sorted(
        path
        for path in dossier_dir.glob("*.md")
        if path.is_file() and DOSSIER_KEY_RE.match(path.name)
    )


def list_weekly_files(rainfields_dir: Path) -> list[Path]:
    weekly_dir = rainfields_dir / "weekly"
    if not weekly_dir.is_dir():
        return []
    return sorted(
        path
        for path in weekly_dir.glob("*.md")
        if path.is_file() and WEEKLY_KEY_RE.match(path.name)
    )


def load_manifest_entries(dossier_dir: Path) -> dict[str, dict[str, Any]]:
    manifest_path = dossier_dir / MANIFEST_NAME
    if not manifest_path.exists():
        logger.warning("Dossier manifest not found: %s", manifest_path)
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read dossier manifest %s: %s", manifest_path, exc)
        return {}
    entries = data.get("entries", {})
    if not isinstance(entries, dict):
        return {}
    return {str(key): value for key, value in entries.items() if isinstance(value, dict)}


def parse_moment(raw: str) -> datetime:
    moment = datetime.fromisoformat(raw)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def empty_counts() -> dict[str, int]:
    return {
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "deleted": 0,
        "errors": 0,
        "skipped": 0,
    }


def upsert_document(
    conn: psycopg.Connection,
    *,
    kind: str,
    doc_key: str,
    path: Path,
    frontmatter: dict[str, Any],
    body_md: str,
    content_hash: str,
) -> str:
    title = title_from_frontmatter(frontmatter, doc_key)
    existing = conn.execute(
        "SELECT content_hash FROM documents WHERE kind = %s AND doc_key = %s",
        (kind, doc_key),
    ).fetchone()
    if existing and existing[0] == content_hash:
        return "unchanged"

    conn.execute(
        """
        INSERT INTO documents (
            kind, doc_key, path, title, frontmatter, body_md, content_hash, synced_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, now()
        )
        ON CONFLICT (kind, doc_key) DO UPDATE SET
            path = EXCLUDED.path,
            title = EXCLUDED.title,
            frontmatter = EXCLUDED.frontmatter,
            body_md = EXCLUDED.body_md,
            content_hash = EXCLUDED.content_hash,
            synced_at = now()
        """,
        (
            kind,
            doc_key,
            str(path),
            title,
            Jsonb(frontmatter),
            body_md,
            content_hash,
        ),
    )
    return "inserted" if existing is None else "updated"


def upsert_entry(conn: psycopg.Connection, entry: dict[str, Any]) -> str:
    entry_id = str(entry["entry_id"])
    content_hash = str(entry.get("content_hash", ""))
    existing = conn.execute(
        "SELECT content_hash FROM entries WHERE entry_id = %s",
        (entry_id,),
    ).fetchone()
    if existing and existing[0] == content_hash:
        return "unchanged"

    day = date.fromisoformat(str(entry["day"]))
    moment = parse_moment(str(entry["moment"]))
    segments = entry.get("segments") or []
    if not isinstance(segments, list):
        segments = []

    conn.execute(
        """
        INSERT INTO entries (
            entry_id, day, moment, source_type, source_file, original_source,
            body, segments, content_hash, synced_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
        )
        ON CONFLICT (entry_id) DO UPDATE SET
            day = EXCLUDED.day,
            moment = EXCLUDED.moment,
            source_type = EXCLUDED.source_type,
            source_file = EXCLUDED.source_file,
            original_source = EXCLUDED.original_source,
            body = EXCLUDED.body,
            segments = EXCLUDED.segments,
            content_hash = EXCLUDED.content_hash,
            synced_at = now()
        """,
        (
            entry_id,
            day,
            moment,
            str(entry.get("source_type", "")),
            str(entry.get("source_file", "")),
            str(entry.get("original_source", "")),
            str(entry.get("body", "")),
            Jsonb(json_safe(segments)),
            content_hash,
        ),
    )
    return "inserted" if existing is None else "updated"


def sync_documents(
    conn: psycopg.Connection,
    *,
    kind: str,
    paths: list[Path],
    key_from_name,
) -> dict[str, int]:
    counts = empty_counts()
    keep_keys: set[str] = set()

    for path in paths:
        match = key_from_name(path.name)
        if not match:
            continue
        doc_key = match.group(1)
        keep_keys.add(doc_key)
        try:
            with conn.transaction():
                frontmatter, body_md, content_hash = parse_markdown(path)
                result = upsert_document(
                    conn,
                    kind=kind,
                    doc_key=doc_key,
                    path=path,
                    frontmatter=frontmatter,
                    body_md=body_md,
                    content_hash=content_hash,
                )
            counts[result] += 1
        except Exception:
            counts["errors"] += 1
            logger.exception("Failed to sync %s document %s", kind, path.name)

    try:
        with conn.transaction():
            rows = conn.execute(
                "SELECT doc_key FROM documents WHERE kind = %s",
                (kind,),
            ).fetchall()
            for (doc_key,) in rows:
                if doc_key not in keep_keys:
                    conn.execute(
                        "DELETE FROM documents WHERE kind = %s AND doc_key = %s",
                        (kind, doc_key),
                    )
                    counts["deleted"] += 1
    except Exception:
        counts["errors"] += 1
        logger.exception("Failed while pruning stale %s documents", kind)

    return counts


def sync_entries(
    conn: psycopg.Connection,
    entries: dict[str, dict[str, Any]],
) -> dict[str, int]:
    counts = empty_counts()
    keep_ids: set[str] = set()

    for entry_id, payload in entries.items():
        data = dict(payload)
        data.setdefault("entry_id", entry_id)
        if "day" not in data or "moment" not in data:
            counts["skipped"] += 1
            logger.warning("Skipping incomplete entry %s", entry_id)
            continue
        keep_ids.add(str(data["entry_id"]))
        try:
            with conn.transaction():
                result = upsert_entry(conn, data)
            counts[result] += 1
        except Exception:
            counts["errors"] += 1
            logger.exception("Failed to sync entry %s", entry_id)

    try:
        with conn.transaction():
            rows = conn.execute("SELECT entry_id FROM entries").fetchall()
            for (entry_id,) in rows:
                if entry_id not in keep_ids:
                    conn.execute(
                        "DELETE FROM entries WHERE entry_id = %s",
                        (entry_id,),
                    )
                    counts["deleted"] += 1
    except Exception:
        counts["errors"] += 1
        logger.exception("Failed while pruning stale entries")

    return counts


def run_sync(dossier_dir: Path, rainfields_dir: Path) -> dict[str, Any]:
    database_url = load_database_url()
    dossier_files = list_dossier_files(dossier_dir)
    weekly_files = list_weekly_files(rainfields_dir)
    manifest_entries = load_manifest_entries(dossier_dir)

    try:
        with psycopg.connect(
            database_url,
            connect_timeout=CONNECT_TIMEOUT_SECONDS,
        ) as conn:
            ensure_schema(conn)
            dossier_docs = sync_documents(
                conn,
                kind="dossier",
                paths=dossier_files,
                key_from_name=DOSSIER_KEY_RE.match,
            )
            weekly_docs = sync_documents(
                conn,
                kind="weekly",
                paths=weekly_files,
                key_from_name=WEEKLY_KEY_RE.match,
            )
            entries = sync_entries(conn, manifest_entries)
    except OperationalError as exc:
        raise ConfigurationError(
            f"Could not connect to Postgres ({exc}). "
            "Check HARKERS_DATABASE_URL and that pgvector-db is running."
        ) from exc

    summary = {
        "dossier_documents": dossier_docs,
        "weekly_documents": weekly_docs,
        "entries": entries,
        "dossier_files": len(dossier_files),
        "weekly_files": len(weekly_files),
        "manifest_entries": len(manifest_entries),
        "ok": (
            dossier_docs.get("errors", 0) == 0
            and weekly_docs.get("errors", 0) == 0
            and entries.get("errors", 0) == 0
        ),
    }
    logger.info(
        "Dispatch complete — dossier docs %s, weekly docs %s, entries %s",
        dossier_docs,
        weekly_docs,
        entries,
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dispatch dossier and weekly notes into Postgres.",
    )
    parser.add_argument(
        "--dossier-dir",
        type=Path,
        default=DEFAULT_DOSSIER_DIR,
        help="Folder containing daily dossier Markdown files",
    )
    parser.add_argument(
        "--rainfields-dir",
        type=Path,
        default=DEFAULT_RAINFIELDS_DIR,
        help="Rainfields Mind root (expects weekly/ underneath)",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print a single JSON object summarizing the sync",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dossier_dir = args.dossier_dir.resolve()
    rainfields_dir = args.rainfields_dir.resolve()

    if not dossier_dir.exists():
        logger.error("Dossier directory does not exist: %s", dossier_dir)
        if args.json_summary:
            print(json.dumps({"ok": False, "error": "dossier_missing"}))
        return 1

    logger.info("Dossier: %s", dossier_dir)
    logger.info("Rainfields: %s", rainfields_dir)

    try:
        summary = run_sync(dossier_dir, rainfields_dir)
    except ConfigurationError as exc:
        logger.error("%s", exc)
        if args.json_summary:
            print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    except Exception as exc:
        logger.exception("Quincey's Dispatch failed")
        if args.json_summary:
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 1

    if args.json_summary:
        print(json.dumps(summary))
    return 0 if summary.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
