"""Compile transcript sources into Obsidian-friendly daily Markdown notes."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from dedupe import dedupe_entries
from manifest import (
    MANIFEST_NAME,
    Manifest,
    SourceRecord,
    entry_from_dict,
    register_source,
    remove_source,
    source_snapshot,
)
from models import JournalEntry
from parsers import is_segment_file, parse_source_file
from writer import render_daily_file

_ARCHIVE_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ARCHIVE_ROOT / ".env")

DEFAULT_TRANSCRIPTS_DIR = Path(
    os.environ.get("HARKERS_TRANSCRIPTS_DIR", _ARCHIVE_ROOT / "transcripts")
)
DEFAULT_DOSSIER_DIR = Path(
    os.environ.get("HARKERS_DOSSIER_DIR", _ARCHIVE_ROOT / "dossier")
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def list_source_files(transcripts_dir: Path) -> list[Path]:
    if not transcripts_dir.exists():
        return []
    files = sorted(path for path in transcripts_dir.glob("*.txt") if path.is_file())
    return [path for path in files if not is_segment_file(path)]


def collect_all_entries(manifest: Manifest) -> list[JournalEntry]:
    return [entry_from_dict(data) for data in manifest.entries.values()]


def entries_for_day(entries: list[JournalEntry], day: date) -> list[JournalEntry]:
    return dedupe_entries([entry for entry in entries if entry.day == day])


def sync_manifest(
    transcripts_dir: Path,
    manifest: Manifest,
    *,
    force: bool = False,
) -> set[str]:
    dirty_days: set[str] = set()
    current_sources = {path.name for path in list_source_files(transcripts_dir)}

    for stale_source in set(manifest.sources) - current_sources:
        dirty_days.update(remove_source(manifest, stale_source))
        logger.info("Removed stale source: %s", stale_source)

    for path in list_source_files(transcripts_dir):
        source_name = path.name
        content_hash, segments_hash, size, mtime = source_snapshot(path)
        previous = manifest.sources.get(source_name)

        unchanged = (
            not force
            and previous is not None
            and previous.content_hash == content_hash
            and previous.segments_hash == segments_hash
            and previous.size == size
        )
        if unchanged:
            continue

        entries = parse_source_file(path, transcripts_dir)
        record_days = sorted({entry.day_iso for entry in entries})
        record = SourceRecord(
            content_hash=content_hash,
            segments_hash=segments_hash,
            size=size,
            mtime=mtime,
            entry_ids=[entry.entry_id for entry in entries],
            days=record_days,
        )
        dirty_days.update(register_source(manifest, source_name, record, entries))
        logger.info("Processed source: %s (%d entries)", source_name, len(entries))

    return dirty_days


def write_daily_files(
    dossier_dir: Path,
    all_entries: list[JournalEntry],
    dirty_days: set[str],
) -> int:
    dossier_dir.mkdir(parents=True, exist_ok=True)
    written = 0

    for day_iso in sorted(dirty_days):
        day = date.fromisoformat(day_iso)
        day_entries = entries_for_day(all_entries, day)
        output_path = dossier_dir / f"{day_iso}.md"
        output_path.write_text(
            render_daily_file(day, day_entries),
            encoding="utf-8",
        )
        logger.info("Wrote %s (%d entries)", output_path.name, len(day_entries))
        written += 1

    return written


def compile_dossier(
    transcripts_dir: Path,
    dossier_dir: Path,
    *,
    force: bool = False,
) -> tuple[int, list[str]]:
    manifest_path = dossier_dir / MANIFEST_NAME
    manifest = Manifest.load(manifest_path)

    dirty_days = sync_manifest(transcripts_dir, manifest, force=force)
    all_entries = collect_all_entries(manifest)

    if not dirty_days:
        logger.info("No changes detected. Dossier is up to date.")
        return 0, []

    days = sorted(dirty_days)
    written = write_daily_files(dossier_dir, all_entries, dirty_days)
    manifest.save(manifest_path)
    return written, days


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile transcripts into Obsidian-friendly daily Markdown notes.",
    )
    parser.add_argument(
        "--transcripts-dir",
        type=Path,
        default=DEFAULT_TRANSCRIPTS_DIR,
        help="Folder containing transcript .txt files",
    )
    parser.add_argument(
        "--dossier-dir",
        type=Path,
        default=DEFAULT_DOSSIER_DIR,
        help="Output folder for daily Markdown files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-parse all sources and rebuild affected daily files",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print a single JSON object with the number of files written",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    transcripts_dir = args.transcripts_dir.resolve()
    dossier_dir = args.dossier_dir.resolve()

    if not transcripts_dir.exists():
        logger.error("Transcripts directory does not exist: %s", transcripts_dir)
        return 1

    logger.info("Transcripts: %s", transcripts_dir)
    logger.info("Dossier output: %s", dossier_dir)

    written, days = compile_dossier(
        transcripts_dir,
        dossier_dir,
        force=args.force,
    )
    if args.json_summary:
        print(json.dumps({"written": written, "days": days}))
    else:
        logger.info("Done. %d daily file(s) updated.", written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
