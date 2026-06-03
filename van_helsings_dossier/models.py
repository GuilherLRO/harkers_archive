"""Shared data models for Van Helsing's Dossier."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time


@dataclass
class Segment:
    start: str
    end: str
    text: str


@dataclass
class JournalEntry:
    entry_id: str
    day: date
    moment: datetime
    source_type: str
    source_file: str
    original_source: str
    body: str
    content_hash: str
    segment_file: str | None = None
    segments: list[Segment] = field(default_factory=list)
    extra_sources: list[str] = field(default_factory=list)

    @property
    def time_label(self) -> str:
        return self.moment.strftime("%H:%M:%S")

    @property
    def day_iso(self) -> str:
        return self.day.isoformat()
