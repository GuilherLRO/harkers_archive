"""Conservative deduplication for journal entries."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from models import JournalEntry


def _source_score(entry: JournalEntry) -> tuple[int, int]:
    has_segments = 1 if entry.segments else 0
    source_count = len(entry.extra_sources) + 1
    return (has_segments, source_count)


def dedupe_entries(entries: list[JournalEntry]) -> list[JournalEntry]:
    """Drop exact duplicate content on the same day, keeping the richer entry."""
    by_day: dict[date, dict[str, JournalEntry]] = defaultdict(dict)

    for entry in entries:
        day_bucket = by_day[entry.day]
        existing = day_bucket.get(entry.content_hash)
        if existing is None:
            day_bucket[entry.content_hash] = entry
            continue

        if _source_score(entry) > _source_score(existing):
            winner, loser = entry, existing
        else:
            winner, loser = existing, entry

        merged_sources = sorted(
            {winner.source_file, loser.source_file, *winner.extra_sources, *loser.extra_sources}
        )
        winner.extra_sources = [
            source for source in merged_sources if source != winner.source_file
        ]
        day_bucket[entry.content_hash] = winner

    deduped: list[JournalEntry] = []
    for day in sorted(by_day):
        deduped.extend(sorted(by_day[day].values(), key=lambda item: item.moment))
    return deduped
