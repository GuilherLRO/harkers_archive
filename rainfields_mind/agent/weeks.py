"""ISO week helpers for Rainfields Mind (America/Fortaleza)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

DEFAULT_TIMEZONE = "America/Fortaleza"


@dataclass(frozen=True)
class WeekInfo:
    week_id: str
    start: date
    end: date

    @property
    def date_range(self) -> str:
        return f"{self.start.isoformat()} .. {self.end.isoformat()}"


def week_id_for_date(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def week_bounds(week_id: str) -> WeekInfo:
    year_str, week_str = week_id.split("-W", maxsplit=1)
    year = int(year_str)
    week = int(week_str)
    start = date.fromisocalendar(year, week, 1)
    end = date.fromisocalendar(year, week, 7)
    return WeekInfo(week_id=week_id, start=start, end=end)


def previous_week_id(week_id: str) -> str | None:
    info = week_bounds(week_id)
    prev_day = info.start - timedelta(days=1)
    return week_id_for_date(prev_day)


def dossier_path_for_day(dossier_dir: Path, day: date) -> Path:
    return dossier_dir / f"{day.isoformat()}.md"


def dossier_relpath_for_day(day: date) -> str:
    return f"dossier/{day.isoformat()}.md"


def list_dossier_files(dossier_dir: Path) -> list[Path]:
    if not dossier_dir.exists():
        return []
    return sorted(
        path
        for path in dossier_dir.glob("????-??-??.md")
        if path.is_file()
    )


def group_dossiers_by_week(
    dossier_dir: Path,
    *,
    timezone: str = DEFAULT_TIMEZONE,
) -> dict[str, list[Path]]:
    """Group dossier files by ISO week using local calendar date (filename)."""
    del timezone  # filenames are already local calendar days
    by_week: dict[str, list[Path]] = {}
    for path in list_dossier_files(dossier_dir):
        day = date.fromisoformat(path.stem)
        week_id = week_id_for_date(day)
        by_week.setdefault(week_id, []).append(path)
    return dict(sorted(by_week.items()))


def dossier_files_for_week(dossier_dir: Path, week_id: str) -> list[Path]:
    info = week_bounds(week_id)
    files: list[Path] = []
    day = info.start
    while day <= info.end:
        path = dossier_path_for_day(dossier_dir, day)
        if path.exists():
            files.append(path)
        day += timedelta(days=1)
    return files


def dossier_relpaths_for_week(week_id: str, dossier_files: list[Path]) -> list[str]:
    return [f"dossier/{path.name}" for path in dossier_files]
