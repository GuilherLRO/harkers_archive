"""Parse transcript source files into normalized journal entries."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path

from models import JournalEntry, Segment

TYPED_NOTE_PATTERN = re.compile(
    r"^\[(?P<stamp>\d{8}_\d{6})\]\s*(?P<body>.+)$",
    re.MULTILINE,
)
SEGMENT_PATTERN = re.compile(
    r"^\[(?P<start>\d{2}:\d{2}\.\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}\.\d{3})\]\s*(?P<text>.+)$"
)
VOICE_WITH_USER_PATTERN = re.compile(
    r"^(?P<date>\d{8})_(?P<time>\d{6})_(?P<user_id>\d+)$"
)
VOICE_COMPACT_PATTERN = re.compile(r"^(?P<datetime>\d{14})$")
TYPED_NOTES_FILE_PATTERN = re.compile(
    r"^typed_notes_(?P<date>\d{8})_(?P<user_id>\d+)\.txt$"
)


def content_hash(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def make_entry_id(source_file: str, moment: datetime, body_hash: str) -> str:
    raw = f"{source_file}|{moment.isoformat()}|{body_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def parse_stamp(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y%m%d_%H%M%S")


def parse_voice_stem(stem: str) -> datetime | None:
    match = VOICE_WITH_USER_PATTERN.match(stem)
    if match:
        return datetime.strptime(
            f"{match.group('date')}_{match.group('time')}",
            "%Y%m%d_%H%M%S",
        )

    match = VOICE_COMPACT_PATTERN.match(stem)
    if match:
        return datetime.strptime(match.group("datetime"), "%Y%m%d%H%M%S")

    return None


def parse_segments(text: str) -> list[Segment]:
    segments: list[Segment] = []
    for line in text.splitlines():
        match = SEGMENT_PATTERN.match(line.strip())
        if not match:
            continue
        segments.append(
            Segment(
                start=match.group("start"),
                end=match.group("end"),
                text=match.group("text").strip(),
            )
        )
    return segments


def is_segment_file(path: Path) -> bool:
    return path.name.endswith("_segments.txt")


def is_typed_notes_file(path: Path) -> bool:
    return bool(TYPED_NOTES_FILE_PATTERN.match(path.name))


def segment_path_for_transcript(path: Path) -> Path:
    return path.with_name(f"{path.stem}_segments.txt")


def parse_typed_notes(path: Path, text: str) -> list[JournalEntry]:
    entries: list[JournalEntry] = []
    for match in TYPED_NOTE_PATTERN.finditer(text):
        moment = parse_stamp(match.group("stamp"))
        body = match.group("body").strip()
        if not body:
            continue
        body_hash = content_hash(body)
        entries.append(
            JournalEntry(
                entry_id=make_entry_id(path.name, moment, body_hash),
                day=moment.date(),
                moment=moment,
                source_type="typed_note",
                source_file=path.name,
                original_source="Telegram text",
                body=body,
                content_hash=body_hash,
            )
        )
    return entries


def parse_voice_transcript(
    path: Path,
    text: str,
    segments_text: str | None = None,
) -> JournalEntry | None:
    moment = parse_voice_stem(path.stem)
    if moment is None:
        return None

    body = text.strip()
    segments = parse_segments(segments_text) if segments_text else []
    if not body and segments:
        body = " ".join(segment.text for segment in segments)
    if not body:
        return None

    segment_file = None
    if segments_text is not None:
        segment_path = segment_path_for_transcript(path)
        if segment_path.exists():
            segment_file = segment_path.name

    body_hash = content_hash(body)
    return JournalEntry(
        entry_id=make_entry_id(path.name, moment, body_hash),
        day=moment.date(),
        moment=moment,
        source_type="voice_transcript",
        source_file=path.name,
        segment_file=segment_file,
        original_source="Telegram voice / OpenAI",
        body=body,
        content_hash=body_hash,
        segments=segments,
    )


def parse_source_file(path: Path, transcripts_dir: Path) -> list[JournalEntry]:
    if is_segment_file(path):
        return []

    text = path.read_text(encoding="utf-8")

    if is_typed_notes_file(path):
        return parse_typed_notes(path, text)

    segment_path = segment_path_for_transcript(path)
    segments_text = None
    if segment_path.exists():
        segments_text = segment_path.read_text(encoding="utf-8")

    entry = parse_voice_transcript(path, text, segments_text)
    return [entry] if entry else []
