"""Track compiled weekly notes for incremental rebuilds."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from validate import validate_weekly_note
from weeks import dossier_relpaths_for_week

MANIFEST_VERSION = 1


@dataclass
class DossierSnapshot:
    content_hash: str
    size: int
    mtime: float


@dataclass
class WeekRecord:
    dossier_hashes: dict[str, str] = field(default_factory=dict)
    weekly_hash: str | None = None
    compiled_at: str | None = None


@dataclass
class Manifest:
    version: int = MANIFEST_VERSION
    weeks: dict[str, WeekRecord] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> Manifest:
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        weeks = {
            week_id: WeekRecord(**record)
            for week_id, record in data.get("weeks", {}).items()
        }
        return cls(version=data.get("version", MANIFEST_VERSION), weeks=weeks)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "weeks": {week_id: asdict(record) for week_id, record in self.weeks.items()},
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dossier_snapshot(path: Path) -> DossierSnapshot:
    stat = path.stat()
    return DossierSnapshot(
        content_hash=file_hash(path),
        size=stat.st_size,
        mtime=stat.st_mtime,
    )


def current_dossier_hashes(dossier_files: list[Path]) -> dict[str, str]:
    return {f"dossier/{path.name}": file_hash(path) for path in dossier_files}


@dataclass
class DirtyWeek:
    week_id: str
    reason: str
    dossier_files: list[Path]


def discover_dirty_weeks(
    *,
    manifest: Manifest,
    dossier_files_by_week: dict[str, list[Path]],
    weekly_dir: Path,
    force: bool = False,
    all_weeks: bool = False,
    target_week: str | None = None,
) -> list[DirtyWeek]:
    dirty: list[DirtyWeek] = []
    week_ids = sorted(dossier_files_by_week)
    if target_week is not None:
        week_ids = [target_week] if target_week in dossier_files_by_week else []

    for week_id in week_ids:
        dossier_files = dossier_files_by_week[week_id]
        if not dossier_files:
            continue

        weekly_path = weekly_dir / f"{week_id}.md"
        hashes = current_dossier_hashes(dossier_files)
        record = manifest.weeks.get(week_id)
        reason = _dirty_reason(
            week_id=week_id,
            dossier_files=dossier_files,
            hashes=hashes,
            weekly_path=weekly_path,
            record=record,
            force=force,
            all_weeks=all_weeks,
        )
        if reason is not None:
            dirty.append(DirtyWeek(week_id=week_id, reason=reason, dossier_files=dossier_files))
    return dirty


def _dirty_reason(
    *,
    week_id: str,
    dossier_files: list[Path],
    hashes: dict[str, str],
    weekly_path: Path,
    record: WeekRecord | None,
    force: bool,
    all_weeks: bool,
) -> str | None:
    if force or all_weeks:
        return "forced rebuild" if force else "full-corpus rebuild"

    if not weekly_path.exists():
        return "weekly note missing"

    expected_relpaths = set(dossier_relpaths_for_week(week_id, dossier_files))
    validation = validate_weekly_note(
        weekly_path.read_text(encoding="utf-8"),
        week_id=week_id,
        expected_source_files=expected_relpaths,
    )
    if not validation.ok:
        return f"weekly note invalid: {'; '.join(validation.errors)}"

    if record is None:
        return "no manifest record for week"

    if record.dossier_hashes != hashes:
        changed = [
            path
            for path, digest in hashes.items()
            if record.dossier_hashes.get(path) != digest
        ]
        if changed:
            return f"dossier changed: {', '.join(sorted(changed))}"
        return "dossier set changed"

    if record.weekly_hash != file_hash(weekly_path):
        return "weekly note changed outside manifest"

    return None


def update_week_record(
    manifest: Manifest,
    week_id: str,
    dossier_files: list[Path],
    weekly_path: Path,
    *,
    compiled_at: str,
) -> None:
    manifest.weeks[week_id] = WeekRecord(
        dossier_hashes=current_dossier_hashes(dossier_files),
        weekly_hash=file_hash(weekly_path) if weekly_path.exists() else None,
        compiled_at=compiled_at,
    )
