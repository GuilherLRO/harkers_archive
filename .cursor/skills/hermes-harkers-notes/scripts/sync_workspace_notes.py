#!/usr/bin/env python3
"""Materialize Harker's `documents` table into a local Markdown notes cache."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import psycopg
    import yaml
except ImportError as exc:
    print(
        "Missing dependency. Install with: pip install 'psycopg[binary]' pyyaml\n"
        f"Import error: {exc}",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


def database_url() -> str:
    url = os.environ.get("HARKERS_DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("HARKERS_DATABASE_URL is not set")
    return url


def render_markdown(frontmatter: dict, body_md: str) -> str:
    fm = yaml.safe_dump(frontmatter or {}, sort_keys=False, allow_unicode=True).strip()
    body = body_md or ""
    if not body.endswith("\n"):
        body += "\n"
    return f"---\n{fm}\n---\n\n{body}"


def sync(out_dir: Path) -> dict:
    dossier_dir = out_dir / "dossier"
    weekly_dir = out_dir / "weekly"
    dossier_dir.mkdir(parents=True, exist_ok=True)
    weekly_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / ".sync_manifest.json"
    previous = {}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))

    counts = {"written": 0, "unchanged": 0, "deleted": 0}
    keep: dict[str, str] = {}

    with psycopg.connect(database_url(), connect_timeout=10) as conn:
        rows = conn.execute(
            """
            SELECT kind, doc_key, title, frontmatter, body_md, content_hash, synced_at
            FROM documents
            ORDER BY kind, doc_key
            """
        ).fetchall()

    for kind, doc_key, title, frontmatter, body_md, content_hash, synced_at in rows:
        rel = f"{kind}/{doc_key}.md"
        target = out_dir / kind / f"{doc_key}.md"
        keep[rel] = content_hash
        if previous.get(rel) == content_hash and target.exists():
            counts["unchanged"] += 1
            continue

        fm = dict(frontmatter or {})
        fm.setdefault("kind", kind)
        fm.setdefault("doc_key", doc_key)
        if title and "title" not in fm:
            fm["title"] = title
        fm["content_hash"] = content_hash
        fm["synced_at"] = synced_at.isoformat() if synced_at else None

        target.write_text(render_markdown(fm, body_md), encoding="utf-8")
        counts["written"] += 1

    for rel in list(previous):
        if rel not in keep:
            path = out_dir / rel
            if path.exists():
                path.unlink()
            counts["deleted"] += 1

    manifest_path.write_text(
        json.dumps(keep, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "ok": True,
        "out_dir": str(out_dir),
        "documents": len(keep),
        **counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/workspace/notes"),
        help="Output notes directory (default: /workspace/notes)",
    )
    parser.add_argument("--json-summary", action="store_true")
    args = parser.parse_args()

    try:
        summary = sync(args.out.resolve())
    except Exception as exc:
        print(f"sync failed: {exc}", file=sys.stderr)
        if args.json_summary:
            print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    if args.json_summary:
        print(json.dumps(summary))
    else:
        print(
            f"Synced {summary['documents']} docs → {summary['out_dir']} "
            f"(written={summary['written']}, unchanged={summary['unchanged']}, "
            f"deleted={summary['deleted']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
