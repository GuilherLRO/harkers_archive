"""Append plain-text Telegram messages to daily typed-note files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def build_typed_notes_path(
    transcripts_dir: Path,
    user_id: int,
    when: datetime | None = None,
) -> Path:
    """Return path for one user's daily typed-notes file."""
    moment = when or datetime.now()
    date_stamp = moment.strftime("%Y%m%d")
    return transcripts_dir / f"typed_notes_{date_stamp}_{user_id}.txt"


def format_entry(text: str, when: datetime | None = None) -> str:
    """Format one note: wall-clock stamp in brackets, then body (blank line after)."""
    moment = when or datetime.now()
    stamp = moment.strftime("%Y%m%d_%H%M%S")
    return f"[{stamp}] {text.strip()}\n\n"


def append_text_note(
    transcripts_dir: Path,
    user_id: int,
    text: str,
    when: datetime | None = None,
) -> Path:
    """Append a text note and return the file written."""
    if not text.strip():
        raise ValueError("Text note is empty")

    transcripts_dir.mkdir(parents=True, exist_ok=True)
    path = build_typed_notes_path(transcripts_dir, user_id, when)
    with path.open("a", encoding="utf-8") as file:
        file.write(format_entry(text, when))
    return path
