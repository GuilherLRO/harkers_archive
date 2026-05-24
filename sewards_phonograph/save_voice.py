"""Download Telegram voice messages to disk with deterministic names."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes


def build_filename(user_id: int, when: datetime | None = None) -> str:
    """Return base filename without collision suffix: YYYYMMDD_HHMMSS_{user_id}.ogg"""
    moment = when or datetime.now()
    stamp = moment.strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{user_id}.ogg"


def resolve_destination(save_dir: Path, user_id: int, when: datetime | None = None) -> Path:
    """Pick a path under save_dir, adding _2, _3, ... if the file already exists."""
    save_dir.mkdir(parents=True, exist_ok=True)
    base_name = build_filename(user_id, when)
    dest = save_dir / base_name
    if not dest.exists():
        return dest

    stem = base_name.removesuffix(".ogg")
    suffix = 2
    while True:
        candidate = save_dir / f"{stem}_{suffix}.ogg"
        if not candidate.exists():
            return candidate
        suffix += 1


async def save_voice_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    save_dir: Path,
) -> Path:
    """Download the voice attachment and return the path written on disk."""
    message = update.effective_message
    if message is None or message.voice is None:
        raise ValueError("Update does not contain a voice message")

    user = update.effective_user
    if user is None:
        raise ValueError("Update does not contain a user")

    dest = resolve_destination(save_dir, user.id)
    tg_file = await context.bot.get_file(message.voice.file_id)
    await tg_file.download_to_drive(custom_path=dest)
    return dest
