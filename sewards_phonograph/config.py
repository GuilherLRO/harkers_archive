"""Load configuration from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name} is not set")
    return value


def load_bot_token() -> str:
    return _require_env("TELEGRAM_BOT_TOKEN")


def load_save_dir() -> Path:
    raw = _require_env("SAVE_DIR")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise ConfigurationError("SAVE_DIR must be an absolute path")
    return path


def load_transcripts_dir(save_dir: Path | None = None) -> Path:
    """Return the transcripts folder for typed notes (TRANSCRIPTS_DIR or sibling of SAVE_DIR)."""
    raw = os.environ.get("TRANSCRIPTS_DIR", "").strip()
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise ConfigurationError("TRANSCRIPTS_DIR must be an absolute path")
        return path

    voice_dir = save_dir or load_save_dir()
    return voice_dir.parent / "transcripts"
