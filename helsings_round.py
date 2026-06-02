#!/usr/bin/env python3
"""Run Seward's Phonograph and schedule Mina's Typewriter — root coordinator.

Does not modify sub-projects: starts bot.py and transcribe.py via subprocess.

Run from the repo root (where .env lives):

    uv run python helsings_round.py

Run in the background (survives closing the terminal):

    ./helsings_roundctl.sh start

    helsings_round.log       — coordinator and bot activity
    helsings_round_http.log  — Telegram HTTP polling (httpx)

Or manually:

    nohup uv run python helsings_round.py >> helsings_round.log 2>&1 &

Stop / restart / status:

    ./helsings_roundctl.sh stop
    ./helsings_roundctl.sh restart
    ./helsings_roundctl.sh status

SIGTERM/SIGINT shut down the bot subprocess cleanly. Use ``kill -9`` only if a normal
``kill`` does not exit within a few seconds.

Do not run ``bot.py`` separately while this script is active — both would use the
same Telegram token.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import time
from pathlib import Path

from archive_logging import configure_logging
from dotenv import load_dotenv
from telegram import Bot

REPO_ROOT = Path(__file__).resolve().parent
configure_logging(REPO_ROOT)
SEWARD_DIR = REPO_ROOT / "sewards_phonograph"
MINA_DIR = REPO_ROOT / "mina_typewriter"
VOICE_EXTENSIONS = (".ogg", ".m4a", ".mp4", ".wav")

DEFAULT_INTERVAL_MINUTES = 480

logger = logging.getLogger(__name__)

_bot_proc: subprocess.Popen[bytes] | None = None
_shutting_down = False


class ConfigurationError(Exception):
    pass


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


def load_transcripts_dir(voice_dir: Path) -> Path:
    raw = os.environ.get("TRANSCRIPTS_DIR", "").strip()
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise ConfigurationError("TRANSCRIPTS_DIR must be an absolute path")
        return path
    return voice_dir.parent / "transcripts"


def load_interval_minutes() -> int:
    raw = os.environ.get("TRANSCRIBE_INTERVAL_MINUTES", "").strip()
    if not raw:
        return DEFAULT_INTERVAL_MINUTES
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        logger.warning(
            "Invalid TRANSCRIBE_INTERVAL_MINUTES=%r; using %d",
            raw,
            DEFAULT_INTERVAL_MINUTES,
        )
        return DEFAULT_INTERVAL_MINUTES


def parse_user_id_from_voice_filename(name: str) -> int | None:
    """Extract telegram user id from YYYYMMDD_HHMMSS_{user_id}.ogg (optional _2 suffix)."""
    if not name.endswith(".ogg"):
        return None
    stem = name.removesuffix(".ogg")
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


def iter_voice_files(voice_dir: Path) -> list[Path]:
    if not voice_dir.is_dir():
        return []
    return sorted(
        path
        for path in voice_dir.iterdir()
        if path.is_file() and path.name.endswith(VOICE_EXTENSIONS)
    )


def missing_transcripts(voice_dir: Path, transcripts_dir: Path) -> list[str]:
    return [
        path.name
        for path in iter_voice_files(voice_dir)
        if not (transcripts_dir / f"{path.stem}.txt").is_file()
    ]


def recent_voice_user_ids(voice_dir: Path, since_epoch: float) -> set[int]:
    """Users with voice files added or updated since since_epoch."""
    user_ids: set[int] = set()
    for path in iter_voice_files(voice_dir):
        if path.stat().st_mtime >= since_epoch:
            user_id = parse_user_id_from_voice_filename(path.name)
            if user_id is not None:
                user_ids.add(user_id)
    return user_ids


def format_notify_message(
    *,
    transcribed_before: list[str],
    transcribed_after: list[str],
) -> str:
    done = [name for name in transcribed_before if name not in transcribed_after]

    if not done:
        return "Mina's Typewriter — scheduled pass complete. Nothing new to transcribe."

    file_list = ", ".join(done[:5])
    if len(done) > 5:
        file_list += f", … (+{len(done) - 5} more)"
    return f"Mina's Typewriter — scheduled pass complete. Transcribed {len(done)} file(s): {file_list}."


def format_failure_message(error: BaseException) -> str:
    return (
        "Mina's Typewriter — could not send the pass summary "
        f"({type(error).__name__}). Transcription may still have completed; "
        "check helsings_round.log if needed."
    )


async def _send_messages(token: str, user_ids: set[int], text: str) -> None:
    bot = Bot(token=token)
    async with bot:
        for user_id in sorted(user_ids):
            try:
                await bot.send_message(chat_id=user_id, text=text)
                logger.info("Notified user %s", user_id)
            except Exception:
                logger.exception("Failed to notify user %s", user_id)


def notify_users(token: str, user_ids: set[int], message: str) -> None:
    if not user_ids:
        logger.info("No voice users to notify")
        return

    logger.info("Notifying %d user(s)", len(user_ids))
    try:
        asyncio.run(_send_messages(token, user_ids, message))
    except Exception as exc:
        logger.exception("Summary notification failed: %s", exc)
        try:
            failure_text = format_failure_message(exc)
            asyncio.run(_send_messages(token, user_ids, failure_text))
            logger.info("Sent failure notice to %d user(s)", len(user_ids))
        except Exception:
            logger.exception("Failure notification also failed")


def start_bot() -> subprocess.Popen[bytes]:
    logger.info("Starting Seward's Phonograph (bot.py)")
    return subprocess.Popen(
        ["uv", "run", "python", "bot.py"],
        cwd=SEWARD_DIR,
    )


def stop_bot(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    logger.info("Stopping Seward's Phonograph")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def run_transcribe() -> int:
    logger.info("Running Mina's Typewriter (transcribe.py)")
    result = subprocess.run(
        ["uv", "run", "python", "transcribe.py"],
        cwd=MINA_DIR,
    )
    return result.returncode


def _handle_shutdown(signum: int, _frame: object) -> None:
    global _shutting_down
    if _shutting_down:
        raise SystemExit(1)
    _shutting_down = True
    logger.info("Shutdown requested (signal %s)", signum)
    stop_bot(_bot_proc)
    raise SystemExit(0)


def run_pass(
    token: str,
    voice_dir: Path,
    transcripts_dir: Path,
    since_epoch: float,
) -> float:
    pending_before = missing_transcripts(voice_dir, transcripts_dir)
    notify_ids = recent_voice_user_ids(voice_dir, since_epoch)
    for name in pending_before:
        user_id = parse_user_id_from_voice_filename(name)
        if user_id is not None:
            notify_ids.add(user_id)

    exit_code = run_transcribe()
    if exit_code != 0:
        logger.warning("transcribe.py exited with code %s", exit_code)

    pending_after = missing_transcripts(voice_dir, transcripts_dir)
    message = format_notify_message(
        transcribed_before=pending_before,
        transcribed_after=pending_after,
    )
    notify_users(token, notify_ids, message)
    return time.time()


def main() -> None:
    global _bot_proc

    load_dotenv(REPO_ROOT / ".env")

    try:
        token = load_bot_token()
        voice_dir = load_save_dir()
        transcripts_dir = load_transcripts_dir(voice_dir)
    except ConfigurationError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    interval_minutes = load_interval_minutes()
    interval_seconds = interval_minutes * 60

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    _bot_proc = start_bot()
    logger.info(
        "Archive runner active — transcribe every %d minute(s)",
        interval_minutes,
    )

    last_pass_time = time.time() - interval_seconds

    try:
        while not _shutting_down:
            if _bot_proc.poll() is not None:
                logger.error("Bot process exited with code %s", _bot_proc.returncode)
                raise SystemExit(1)

            last_pass_time = run_pass(
                token,
                voice_dir,
                transcripts_dir,
                last_pass_time,
            )

            logger.info("Next transcription pass in %d minute(s)", interval_minutes)
            slept = 0
            while slept < interval_seconds and not _shutting_down:
                if _bot_proc.poll() is not None:
                    logger.error("Bot process exited with code %s", _bot_proc.returncode)
                    raise SystemExit(1)
                time.sleep(1)
                slept += 1
    finally:
        stop_bot(_bot_proc)


if __name__ == "__main__":
    main()
