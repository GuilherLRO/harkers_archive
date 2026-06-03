"""Track processed transcript sources for incremental rebuilds."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

from models import JournalEntry, Segment


MANIFEST_VERSION = 1
MANIFEST_NAME = ".van_helsings_dossier_manifest.json"


@dataclass
class SourceRecord:
    content_hash: str
    size: int
    mtime: float
    entry_ids: list[str] = field(default_factory=list)
    days: list[str] = field(default_factory=list)
    segments_hash: str | None = None


@dataclass
class Manifest:
    version: int = MANIFEST_VERSION
    sources: dict[str, SourceRecord] = field(default_factory=dict)
    entries: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> Manifest:
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        sources = {
            name: SourceRecord(**record)
            for name, record in data.get("sources", {}).items()
        }
        return cls(
            version=data.get("version", MANIFEST_VERSION),
            sources=sources,
            entries=data.get("entries", {}),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "sources": {name: asdict(record) for name, record in self.sources.items()},
            "entries": self.entries,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def segment_sidecar(path: Path) -> Path | None:
    sidecar = path.with_name(f"{path.stem}_segments.txt")
    return sidecar if sidecar.exists() else None


def source_snapshot(path: Path) -> tuple[str, str | None, int, float]:
    segments_path = segment_sidecar(path)
    segments_hash = file_hash(segments_path) if segments_path else None
    stat = path.stat()
    return file_hash(path), segments_hash, stat.st_size, stat.st_mtime


def entry_to_dict(entry: JournalEntry) -> dict:
    return {
        "entry_id": entry.entry_id,
        "day": entry.day_iso,
        "moment": entry.moment.isoformat(),
        "source_type": entry.source_type,
        "source_file": entry.source_file,
        "segment_file": entry.segment_file,
        "original_source": entry.original_source,
        "body": entry.body,
        "content_hash": entry.content_hash,
        "extra_sources": entry.extra_sources,
        "segments": [
            {"start": segment.start, "end": segment.end, "text": segment.text}
            for segment in entry.segments
        ],
    }


def entry_from_dict(data: dict) -> JournalEntry:
    return JournalEntry(
        entry_id=data["entry_id"],
        day=date.fromisoformat(data["day"]),
        moment=datetime.fromisoformat(data["moment"]),
        source_type=data["source_type"],
        source_file=data["source_file"],
        segment_file=data.get("segment_file"),
        original_source=data["original_source"],
        body=data["body"],
        content_hash=data["content_hash"],
        extra_sources=list(data.get("extra_sources", [])),
        segments=[
            Segment(
                start=segment["start"],
                end=segment["end"],
                text=segment["text"],
            )
            for segment in data.get("segments", [])
        ],
    )


def remove_source(manifest: Manifest, source_name: str) -> set[str]:
    record = manifest.sources.pop(source_name, None)
    dirty_days: set[str] = set()
    if record is None:
        return dirty_days

    dirty_days.update(record.days)
    for entry_id in record.entry_ids:
        manifest.entries.pop(entry_id, None)
    return dirty_days


def register_source(
    manifest: Manifest,
    source_name: str,
    record: SourceRecord,
    entries: list[JournalEntry],
) -> set[str]:
    remove_source(manifest, source_name)
    manifest.sources[source_name] = record
    dirty_days = set(record.days)
    for entry in entries:
        manifest.entries[entry.entry_id] = entry_to_dict(entry)
    return dirty_days
