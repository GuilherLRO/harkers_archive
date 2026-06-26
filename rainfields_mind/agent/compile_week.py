"""Compile Rainfields Mind weekly notes from daily dossiers."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from graph import run_week_pipeline
from manifest import Manifest, discover_dirty_weeks
from paths import ARCHIVE_ROOT, MANIFEST_PATH, RAINFIELDS_ROOT, RUNS_DIR
from run_log import RunLog
from weeks import group_dossiers_by_week

load_dotenv(ARCHIVE_ROOT / ".env")

DEFAULT_DOSSIER_DIR = Path(
    os.environ.get("HARKERS_DOSSIER_DIR", ARCHIVE_ROOT / "dossier")
)
DEFAULT_RAINFIELDS_DIR = Path(
    os.environ.get("HARKERS_RAINFIELDS_DIR", RAINFIELDS_ROOT)
)
DEFAULT_MODEL = os.environ.get("RAINFIELDS_MODEL", "o4-mini")
DEFAULT_TIMEZONE = os.environ.get("RAINFIELDS_TIMEZONE", "America/Fortaleza")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    pass


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise ConfigurationError("OPENAI_API_KEY is required for Rainfields Mind agent runs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Synthesize Rainfields Mind weekly notes from daily dossiers.",
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
        help="Rainfields Mind output folder",
    )
    parser.add_argument(
        "--week",
        metavar="YYYY-WNN",
        help="Process a single ISO week",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Rebuild every week represented in the dossier",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore manifest and rebuild targeted weeks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List dirty weeks without calling the OpenAI API",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print a single JSON object with run results",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model (default: {DEFAULT_MODEL})",
    )
    return parser


def compile_weeks(
    *,
    dossier_dir: Path,
    rainfields_dir: Path,
    model: str,
    week: str | None = None,
    all_weeks: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    dossier_dir = dossier_dir.resolve()
    rainfields_dir = rainfields_dir.resolve()
    weekly_dir = rainfields_dir / "weekly"

    by_week = group_dossiers_by_week(dossier_dir, timezone=DEFAULT_TIMEZONE)
    manifest = Manifest.load(MANIFEST_PATH)
    dirty_weeks = discover_dirty_weeks(
        manifest=manifest,
        dossier_files_by_week=by_week,
        weekly_dir=weekly_dir,
        force=force,
        all_weeks=all_weeks,
        target_week=week,
    )

    summary: dict = {
        "dirty_weeks": [item.week_id for item in dirty_weeks],
        "compiled": [],
        "skipped": False,
        "errors": [],
    }

    if not dirty_weeks:
        skip_log = RunLog.new(week=None, action="skip")
        skip_log.skip_reason = "no_dirty_weeks"
        skip_log.write(RUNS_DIR)
        logger.info("skipped: no dirty weeks")
        summary["skipped"] = True
        return summary

    if dry_run:
        for item in dirty_weeks:
            logger.info("dry-run: would compile %s (%s)", item.week_id, item.reason)
        summary["dry_run"] = True
        return summary

    _require_api_key()

    for item in dirty_weeks:
        logger.info("compiling %s (%s)", item.week_id, item.reason)
        run_log = RunLog.new(week=item.week_id, action="refresh")
        run_log.model = model
        run_log.dirty_reason = item.reason
        run_log.dossier_files = [f"dossier/{path.name}" for path in item.dossier_files]

        try:
            result = run_week_pipeline(
                week_id=item.week_id,
                dossier_files=item.dossier_files,
                rainfields_dir=rainfields_dir,
                dossier_dir=dossier_dir,
                model=model,
            )
        except Exception as exc:
            run_log.action = "error"
            run_log.error = str(exc)
            run_log.write(RUNS_DIR)
            summary["errors"].append({"week": item.week_id, "error": str(exc)})
            logger.exception("failed %s", item.week_id)
            continue

        if result.get("error"):
            run_log.action = "error"
            run_log.error = result["error"]
            run_log.reasoning = result.get("reasoning")
            run_log.validation = {
                "ok": False,
                "errors": result.get("validation_errors", []),
            }
            run_log.write(RUNS_DIR)
            summary["errors"].append({"week": item.week_id, "error": result["error"]})
            logger.error("failed %s: %s", item.week_id, result["error"])
            continue

        action = result.get("action", "refresh")
        run_log.action = action
        run_log.reasoning = result.get("reasoning")
        run_log.validation = {"ok": True, "errors": []}
        run_log.outputs = {
            "weekly_path": result.get("weekly_path"),
            "index_updated": result.get("index_updated", False),
            "tags_appended": result.get("tags_appended", []),
        }
        run_log.proposed_tags = [
            tag.model_dump() if hasattr(tag, "model_dump") else {"tag": tag.tag, "definition": tag.definition}
            for tag in result.get("proposed_tags", [])
        ]
        run_log.write(RUNS_DIR)

        logger.info("compiled %s (%s)", item.week_id, action)
        summary["compiled"].append(
            {
                "week": item.week_id,
                "action": action,
                "weekly_path": result.get("weekly_path"),
            }
        )

    return summary


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = compile_weeks(
            dossier_dir=args.dossier_dir,
            rainfields_dir=args.rainfields_dir,
            model=args.model,
            week=args.week,
            all_weeks=args.all,
            force=args.force,
            dry_run=args.dry_run,
        )
    except ConfigurationError as exc:
        logger.error("%s", exc)
        return 1

    if args.json_summary:
        print(json.dumps(summary))
    else:
        compiled = summary.get("compiled", [])
        if compiled:
            logger.info("Done. %d weekly file(s) updated.", len(compiled))
        elif summary.get("skipped"):
            logger.info("Done. No updates needed.")
        elif summary.get("dry_run"):
            logger.info("Done. Dry run only.")

    return 1 if summary.get("errors") else 0


if __name__ == "__main__":
    sys.exit(main())
