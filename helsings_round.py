#!/usr/bin/env python3
"""Run Seward's Phonograph and schedule Mina's Typewriter, Van Helsing's Dossier, and Rainfields Mind.

Root coordinator. Does not modify sub-projects: starts bot.py, transcribe.py,
compile.py, and compile_week.py via subprocess.

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
import json
import logging
import os
import re
import signal
import subprocess
import time
from datetime import date
from pathlib import Path

from archive_logging import configure_logging
from dotenv import load_dotenv
from telegram import Bot

REPO_ROOT = Path(__file__).resolve().parent
configure_logging(REPO_ROOT)
SEWARD_DIR = REPO_ROOT / "sewards_phonograph"
MINA_DIR = REPO_ROOT / "mina_typewriter"
DOSSIER_DIR = REPO_ROOT / "van_helsings_dossier"
RAINFIELDS_AGENT_DIR = REPO_ROOT / "rainfields_mind" / "agent"
VOICE_EXTENSIONS = (".ogg", ".m4a", ".mp4", ".wav", ".WAV")

DEFAULT_INTERVAL_MINUTES = 1440
DEFAULT_DOSSIER_INTERVAL_MINUTES = 1440
DEFAULT_PENDING_POLL_SECONDS = 60
MIN_PENDING_POLL_SECONDS = 10
MAX_PENDING_POLL_SECONDS = 600

logger = logging.getLogger(__name__)

_bot_proc: subprocess.Popen[bytes] | None = None
_shutting_down = False


class ConfigurationError(Exception):
    pass


class PassResult:
    __slots__ = ("pass_time", "transcribed_count")

    def __init__(self, pass_time: float, transcribed_count: int) -> None:
        self.pass_time = pass_time
        self.transcribed_count = transcribed_count


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name} is not set")
    return value


def _parse_positive_int(raw: str, *, name: str, default: int) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        logger.warning("Invalid %s=%r; using %d", name, raw, default)
        return default


def _parse_bounded_int(
    raw: str,
    *,
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
        if value < minimum or value > maximum:
            raise ValueError
        return value
    except ValueError:
        logger.warning(
            "Invalid %s=%r; using %d (allowed %d–%d)",
            name,
            raw,
            default,
            minimum,
            maximum,
        )
        return default


def _env_flag(name: str, *, default: bool = True) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


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
    raw = os.environ.get("HARKERS_TRANSCRIPTS_DIR", "").strip()
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise ConfigurationError("HARKERS_TRANSCRIPTS_DIR must be an absolute path")
        return path
    return voice_dir.parent / "transcripts"


def load_dossier_dir(voice_dir: Path) -> Path:
    raw = os.environ.get("HARKERS_DOSSIER_DIR", "").strip()
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise ConfigurationError("HARKERS_DOSSIER_DIR must be an absolute path")
        return path
    return voice_dir.parent / "dossier"


def load_rainfields_dir() -> Path:
    raw = os.environ.get("HARKERS_RAINFIELDS_DIR", "").strip()
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise ConfigurationError("HARKERS_RAINFIELDS_DIR must be an absolute path")
        return path
    return REPO_ROOT / "rainfields_mind"


def load_interval_minutes() -> int:
    return _parse_positive_int(
        os.environ.get("TRANSCRIBE_INTERVAL_MINUTES", "").strip(),
        name="TRANSCRIBE_INTERVAL_MINUTES",
        default=DEFAULT_INTERVAL_MINUTES,
    )


def load_pending_poll_seconds() -> int:
    return _parse_bounded_int(
        os.environ.get("TRANSCRIBE_PENDING_POLL_SECONDS", "").strip(),
        name="TRANSCRIBE_PENDING_POLL_SECONDS",
        default=DEFAULT_PENDING_POLL_SECONDS,
        minimum=MIN_PENDING_POLL_SECONDS,
        maximum=MAX_PENDING_POLL_SECONDS,
    )


def load_dossier_interval_minutes() -> int:
    return _parse_positive_int(
        os.environ.get("DOSSIER_INTERVAL_MINUTES", "").strip(),
        name="DOSSIER_INTERVAL_MINUTES",
        default=DEFAULT_DOSSIER_INTERVAL_MINUTES,
    )


def dossier_enabled() -> bool:
    return _env_flag("DOSSIER_ENABLED", default=True)


def rainfields_enabled() -> bool:
    return _env_flag("RAINFIELDS_ENABLED", default=True)


def startup_notify_enabled() -> bool:
    return _env_flag("STARTUP_NOTIFY_ENABLED", default=True)


def parse_user_id_from_voice_filename(name: str) -> int | None:
    """Extract telegram user id from YYYYMMDD_HHMMSS_{user_id}.ogg (optional _2 suffix)."""
    stem = Path(name).stem
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


def parse_user_id_from_typed_notes_filename(name: str) -> int | None:
    match = re.match(r"^typed_notes_\d{8}_(\d+)\.txt$", name)
    if not match:
        return None
    return int(match.group(1))


def iter_voice_files(voice_dir: Path) -> list[Path]:
    if not voice_dir.is_dir():
        return []
    return sorted(
        path
        for path in voice_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {ext.lower() for ext in VOICE_EXTENSIONS}
    )


def archive_user_ids(voice_dir: Path, transcripts_dir: Path) -> set[int]:
    user_ids: set[int] = set()
    for path in iter_voice_files(voice_dir):
        user_id = parse_user_id_from_voice_filename(path.name)
        if user_id is not None:
            user_ids.add(user_id)
    if transcripts_dir.is_dir():
        for path in transcripts_dir.glob("typed_notes_*.txt"):
            user_id = parse_user_id_from_typed_notes_filename(path.name)
            if user_id is not None:
                user_ids.add(user_id)
    return user_ids


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


def parse_iso_week_stem(stem: str) -> tuple[int, int] | None:
    match = re.match(r"^(\d{4})-W(\d{2})$", stem)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def latest_weekly_file(rainfields_dir: Path) -> Path | None:
    weekly_dir = rainfields_dir / "weekly"
    if not weekly_dir.is_dir():
        return None
    candidates: list[Path] = []
    for path in weekly_dir.glob("*.md"):
        if parse_iso_week_stem(path.stem) is not None:
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda item: parse_iso_week_stem(item.stem) or (0, 0))


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


def format_transcribe_failure_message(error: BaseException) -> str:
    return (
        "Mina's Typewriter — could not send the pass summary "
        f"({type(error).__name__}). Transcription may still have completed; "
        "check helsings_round.log if needed."
    )


def format_weekly_delivery_caption(path: Path) -> str:
    return (
        "Rainfields Mind — your most recent weekly note "
        f"({path.stem})."
    )


def format_weekly_delivery_failure_message(error: BaseException) -> str:
    return (
        "Rainfields Mind — could not deliver the weekly note "
        f"({type(error).__name__}). Check helsings_round.log if needed."
    )


def format_dossier_delivery_caption(path: Path) -> str:
    return f"Van Helsing's Dossier — today's note ({path.stem})."


def format_dossier_delivery_failure_message(error: BaseException) -> str:
    return (
        "Van Helsing's Dossier — could not deliver today's note "
        f"({type(error).__name__}). Check helsings_round.log if needed."
    )


def todays_dossier_file(
    dossier_dir: Path,
    *,
    day: date | None = None,
) -> Path | None:
    target = day or date.today()
    path = dossier_dir / f"{target.isoformat()}.md"
    return path if path.is_file() else None


def format_startup_message(
    *,
    pending_poll_seconds: int,
    interval_minutes: int,
    dossier_interval_minutes: int,
    run_dossier: bool,
    run_rainfields: bool,
) -> str:
    lines = [
        "Harker's Archive — archive runner started.",
        (
            f"Transcription when new voice files arrive (check every "
            f"{pending_poll_seconds} second(s)); full pass backstop every "
            f"{interval_minutes} minute(s)."
        ),
    ]
    if run_dossier:
        lines.append(
            "Van Helsing's Dossier — compile on new voice transcripts or every "
            f"{dossier_interval_minutes} minute(s); deliver today's note when "
            "a daily file is written."
        )
    else:
        lines.append("Van Helsing's Dossier is disabled.")
    if run_rainfields:
        lines.append(
            "Rainfields Mind — refresh weekly notes after each transcription pass "
            "when dossiers change; deliver the latest weekly note every "
            f"{dossier_interval_minutes} minute(s)."
        )
    else:
        lines.append(
            "Rainfields Mind refresh is disabled; latest weekly note delivery still "
            f"runs every {dossier_interval_minutes} minute(s)."
        )
    return "\n".join(lines)


async def _send_messages(token: str, user_ids: set[int], text: str) -> None:
    bot = Bot(token=token)
    async with bot:
        for user_id in sorted(user_ids):
            try:
                await bot.send_message(chat_id=user_id, text=text)
                logger.info("Notified user %s", user_id)
            except Exception:
                logger.exception("Failed to notify user %s", user_id)


async def _send_documents(
    token: str,
    user_ids: set[int],
    path: Path,
    caption: str,
    *,
    kind: str,
) -> None:
    bot = Bot(token=token)
    async with bot:
        for user_id in sorted(user_ids):
            try:
                with path.open("rb") as handle:
                    await bot.send_document(
                        chat_id=user_id,
                        document=handle,
                        filename=path.name,
                        caption=caption,
                    )
                logger.info("Delivered %s %s to user %s", kind, path.name, user_id)
            except Exception:
                logger.exception("Failed to deliver %s to user %s", kind, user_id)


async def _send_weekly_documents(
    token: str,
    user_ids: set[int],
    path: Path,
    caption: str,
) -> None:
    await _send_documents(
        token,
        user_ids,
        path,
        caption,
        kind="weekly note",
    )


async def _send_dossier_documents(
    token: str,
    user_ids: set[int],
    path: Path,
    caption: str,
) -> None:
    await _send_documents(
        token,
        user_ids,
        path,
        caption,
        kind="dossier note",
    )


def notify_users(token: str, user_ids: set[int], message: str) -> None:
    if not user_ids:
        logger.info("No users to notify")
        return

    logger.info("Notifying %d user(s)", len(user_ids))
    try:
        asyncio.run(_send_messages(token, user_ids, message))
    except Exception as exc:
        logger.exception("Summary notification failed: %s", exc)
        try:
            failure_text = format_transcribe_failure_message(exc)
            asyncio.run(_send_messages(token, user_ids, failure_text))
            logger.info("Sent failure notice to %d user(s)", len(user_ids))
        except Exception:
            logger.exception("Failure notification also failed")


def notify_startup(
    token: str,
    voice_dir: Path,
    transcripts_dir: Path,
    *,
    pending_poll_seconds: int,
    interval_minutes: int,
    dossier_interval_minutes: int,
    run_dossier: bool,
    run_rainfields: bool,
) -> None:
    if not startup_notify_enabled():
        logger.info("Startup notification disabled")
        return

    user_ids = archive_user_ids(voice_dir, transcripts_dir)
    if not user_ids:
        logger.info("No archive users to notify on startup")
        return

    message = format_startup_message(
        pending_poll_seconds=pending_poll_seconds,
        interval_minutes=interval_minutes,
        dossier_interval_minutes=dossier_interval_minutes,
        run_dossier=run_dossier,
        run_rainfields=run_rainfields,
    )
    logger.info("Sending startup notification to %d user(s)", len(user_ids))
    try:
        asyncio.run(_send_messages(token, user_ids, message))
    except Exception:
        logger.exception("Startup notification failed")


def deliver_weekly_file(token: str, user_ids: set[int], path: Path) -> None:
    if not user_ids:
        logger.info("No archive users to receive weekly delivery")
        return

    caption = format_weekly_delivery_caption(path)
    logger.info(
        "Delivering weekly note %s to %d user(s)",
        path.name,
        len(user_ids),
    )
    try:
        asyncio.run(_send_weekly_documents(token, user_ids, path, caption))
    except Exception as exc:
        logger.exception("Weekly delivery failed: %s", exc)
        try:
            failure_text = format_weekly_delivery_failure_message(exc)
            asyncio.run(_send_messages(token, user_ids, failure_text))
        except Exception:
            logger.exception("Weekly delivery failure notification also failed")


def deliver_dossier_file(token: str, user_ids: set[int], path: Path) -> None:
    if not user_ids:
        logger.info("No archive users to receive dossier delivery")
        return

    caption = format_dossier_delivery_caption(path)
    logger.info(
        "Delivering dossier note %s to %d user(s)",
        path.name,
        len(user_ids),
    )
    try:
        asyncio.run(_send_dossier_documents(token, user_ids, path, caption))
    except Exception as exc:
        logger.exception("Dossier delivery failed: %s", exc)
        try:
            failure_text = format_dossier_delivery_failure_message(exc)
            asyncio.run(_send_messages(token, user_ids, failure_text))
        except Exception:
            logger.exception("Dossier delivery failure notification also failed")


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


def run_dossier_compile(transcripts_dir: Path, dossier_dir: Path) -> tuple[int, list[str]]:
    logger.info("Running Van Helsing's Dossier (compile.py)")
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "compile.py",
            "--transcripts-dir",
            str(transcripts_dir),
            "--dossier-dir",
            str(dossier_dir),
            "--json-summary",
        ],
        cwd=DOSSIER_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(
            "compile.py exited with code %s\nstdout: %s\nstderr: %s",
            result.returncode,
            result.stdout.strip(),
            result.stderr.strip(),
        )
        return 0, []

    summary_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    try:
        payload = json.loads(summary_line)
        written = int(payload.get("written", 0))
        raw_days = payload.get("days", [])
        days = [str(day) for day in raw_days] if isinstance(raw_days, list) else []
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Could not parse dossier compile summary: %r", summary_line)
        written = 0
        days = []

    logger.info("Dossier compile complete — %d daily file(s) updated", written)
    return written, days


def run_rainfields_compile(dossier_dir: Path, rainfields_dir: Path) -> None:
    logger.info("Running Rainfields Mind (compile_week.py)")
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "compile_week.py",
            "--dossier-dir",
            str(dossier_dir),
            "--rainfields-dir",
            str(rainfields_dir),
            "--json-summary",
        ],
        cwd=RAINFIELDS_AGENT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(
            "compile_week.py exited with code %s\nstdout: %s\nstderr: %s",
            result.returncode,
            result.stdout.strip(),
            result.stderr.strip(),
        )
        return

    summary_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    try:
        payload = json.loads(summary_line)
    except json.JSONDecodeError:
        logger.warning("Could not parse Rainfields compile summary: %r", summary_line)
        return

    if payload.get("skipped"):
        logger.info("Rainfields compile complete — no weekly updates needed")
        return

    compiled = payload.get("compiled", [])
    if compiled:
        weeks = ", ".join(item.get("week", "?") for item in compiled)
        logger.info(
            "Rainfields compile complete — %d weekly file(s) updated (%s)",
            len(compiled),
            weeks,
        )
    elif payload.get("errors"):
        logger.warning(
            "Rainfields compile finished with errors: %s",
            payload.get("errors"),
        )


def _handle_shutdown(signum: int, _frame: object) -> None:
    global _shutting_down
    if _shutting_down:
        raise SystemExit(1)
    _shutting_down = True
    logger.info("Shutdown requested (signal %s)", signum)
    stop_bot(_bot_proc)
    raise SystemExit(0)


def maybe_run_dossier_compile(
    transcripts_dir: Path,
    dossier_dir: Path,
    *,
    new_transcripts: bool,
    last_compile_time: float,
    dossier_interval_seconds: float,
) -> tuple[float, list[str]]:
    now = time.time()
    compile_due = new_transcripts or (
        now - last_compile_time >= dossier_interval_seconds
    )
    if not compile_due:
        return last_compile_time, []

    _written, days = run_dossier_compile(transcripts_dir, dossier_dir)
    return now, days


def maybe_deliver_todays_dossier(
    token: str,
    voice_dir: Path,
    transcripts_dir: Path,
    dossier_dir: Path,
    written_days: list[str],
    *,
    day: date | None = None,
) -> None:
    target = day or date.today()
    day_iso = target.isoformat()
    if day_iso not in written_days:
        if written_days:
            logger.info(
                "Dossier wrote %d day(s) (%s); today's note (%s) unchanged — skip delivery",
                len(written_days),
                ", ".join(written_days),
                day_iso,
            )
        return

    path = todays_dossier_file(dossier_dir, day=target)
    if path is None:
        logger.info(
            "Dossier listed today (%s) as written, but file is missing",
            day_iso,
        )
        return

    deliver_dossier_file(
        token,
        archive_user_ids(voice_dir, transcripts_dir),
        path,
    )


def maybe_deliver_weekly(
    token: str,
    voice_dir: Path,
    transcripts_dir: Path,
    rainfields_dir: Path,
    *,
    last_delivery_time: float,
    delivery_interval_seconds: float,
) -> float:
    now = time.time()
    if now - last_delivery_time < delivery_interval_seconds:
        return last_delivery_time

    latest = latest_weekly_file(rainfields_dir)
    if latest is None:
        logger.info("Weekly delivery due, but no weekly Markdown files found")
    else:
        deliver_weekly_file(
            token,
            archive_user_ids(voice_dir, transcripts_dir),
            latest,
        )
    return now


def run_pass(
    token: str,
    voice_dir: Path,
    transcripts_dir: Path,
    dossier_dir: Path,
    rainfields_dir: Path,
    since_epoch: float,
    *,
    dossier_interval_seconds: float,
    last_dossier_compile_time: float,
    last_weekly_delivery_time: float,
    run_dossier: bool,
    run_rainfields: bool,
) -> tuple[PassResult, float, float]:
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
    transcribed_count = len(
        [name for name in pending_before if name not in pending_after]
    )
    message = format_notify_message(
        transcribed_before=pending_before,
        transcribed_after=pending_after,
    )
    notify_users(token, notify_ids, message)

    compile_time = last_dossier_compile_time
    delivery_time = last_weekly_delivery_time
    written_days: list[str] = []
    if run_dossier:
        compile_time, written_days = maybe_run_dossier_compile(
            transcripts_dir,
            dossier_dir,
            new_transcripts=transcribed_count > 0,
            last_compile_time=last_dossier_compile_time,
            dossier_interval_seconds=dossier_interval_seconds,
        )
        maybe_deliver_todays_dossier(
            token,
            voice_dir,
            transcripts_dir,
            dossier_dir,
            written_days,
        )

    if run_rainfields:
        run_rainfields_compile(dossier_dir, rainfields_dir)

    delivery_time = maybe_deliver_weekly(
        token,
        voice_dir,
        transcripts_dir,
        rainfields_dir,
        last_delivery_time=last_weekly_delivery_time,
        delivery_interval_seconds=dossier_interval_seconds,
    )

    return (
        PassResult(time.time(), transcribed_count),
        compile_time,
        delivery_time,
    )


def _ensure_bot_running() -> None:
    if _bot_proc is None or _bot_proc.poll() is not None:
        code = None if _bot_proc is None else _bot_proc.returncode
        logger.error("Bot process exited with code %s", code)
        raise SystemExit(1)


def _sleep_seconds(seconds: int) -> None:
    slept = 0
    while slept < seconds and not _shutting_down:
        _ensure_bot_running()
        time.sleep(1)
        slept += 1


def _sleep_until_pending_or_backstop(
    voice_dir: Path,
    transcripts_dir: Path,
    *,
    last_pass_time: float,
    interval_seconds: float,
) -> None:
    while not _shutting_down:
        _ensure_bot_running()
        if missing_transcripts(voice_dir, transcripts_dir):
            return
        if time.time() - last_pass_time >= interval_seconds:
            return
        time.sleep(1)


def _log_runner_mode(
    *,
    pending_poll_seconds: int,
    interval_minutes: int,
    dossier_interval_minutes: int,
    run_dossier: bool,
    run_rainfields: bool,
) -> None:
    transcribe_line = (
        "Archive runner active — transcribe when pending every %d second(s), "
        "full pass backstop every %d minute(s)"
    ) % (pending_poll_seconds, interval_minutes)
    if run_dossier and run_rainfields:
        logger.info(
            "%s, dossier compile on new transcripts or every %d minute(s), "
            "deliver today's dossier when written, "
            "Rainfields weekly refresh after each pass, "
            "weekly note delivery every %d minute(s)",
            transcribe_line,
            dossier_interval_minutes,
            dossier_interval_minutes,
        )
    elif run_dossier:
        logger.info(
            "%s, dossier compile on new transcripts or every %d minute(s), "
            "deliver today's dossier when written, "
            "weekly note delivery every %d minute(s), Rainfields disabled",
            transcribe_line,
            dossier_interval_minutes,
            dossier_interval_minutes,
        )
    elif run_rainfields:
        logger.info(
            "%s, dossier disabled, Rainfields weekly refresh after each pass, "
            "weekly note delivery every %d minute(s)",
            transcribe_line,
            dossier_interval_minutes,
        )
    else:
        logger.info(
            "%s, dossier and Rainfields refresh disabled, "
            "weekly note delivery every %d minute(s)",
            transcribe_line,
            dossier_interval_minutes,
        )


def main() -> None:
    global _bot_proc

    load_dotenv(REPO_ROOT / ".env")

    try:
        token = load_bot_token()
        voice_dir = load_save_dir()
        transcripts_dir = load_transcripts_dir(voice_dir)
        dossier_dir = load_dossier_dir(voice_dir)
        rainfields_dir = load_rainfields_dir()
    except ConfigurationError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    interval_minutes = load_interval_minutes()
    interval_seconds = interval_minutes * 60
    pending_poll_seconds = load_pending_poll_seconds()
    dossier_interval_minutes = load_dossier_interval_minutes()
    dossier_interval_seconds = dossier_interval_minutes * 60
    run_dossier = dossier_enabled()
    run_rainfields = rainfields_enabled()

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    _bot_proc = start_bot()
    _log_runner_mode(
        pending_poll_seconds=pending_poll_seconds,
        interval_minutes=interval_minutes,
        dossier_interval_minutes=dossier_interval_minutes,
        run_dossier=run_dossier,
        run_rainfields=run_rainfields,
    )

    notify_startup(
        token,
        voice_dir,
        transcripts_dir,
        pending_poll_seconds=pending_poll_seconds,
        interval_minutes=interval_minutes,
        dossier_interval_minutes=dossier_interval_minutes,
        run_dossier=run_dossier,
        run_rainfields=run_rainfields,
    )

    last_pass_time = time.time() - interval_seconds
    last_dossier_compile_time = time.time()
    last_weekly_delivery_time = time.time()

    try:
        while not _shutting_down:
            _ensure_bot_running()

            pending = missing_transcripts(voice_dir, transcripts_dir)
            backstop_due = time.time() - last_pass_time >= interval_seconds

            if pending or backstop_due:
                pass_result, last_dossier_compile_time, last_weekly_delivery_time = run_pass(
                    token,
                    voice_dir,
                    transcripts_dir,
                    dossier_dir,
                    rainfields_dir,
                    last_pass_time,
                    dossier_interval_seconds=dossier_interval_seconds,
                    last_dossier_compile_time=last_dossier_compile_time,
                    last_weekly_delivery_time=last_weekly_delivery_time,
                    run_dossier=run_dossier,
                    run_rainfields=run_rainfields,
                )
                last_pass_time = pass_result.pass_time

                if missing_transcripts(voice_dir, transcripts_dir):
                    logger.info(
                        "Pending transcripts remain; next check in %d second(s)",
                        pending_poll_seconds,
                    )
                    _sleep_seconds(pending_poll_seconds)
                else:
                    remaining_minutes = max(
                        1,
                        int((interval_seconds - (time.time() - last_pass_time)) / 60),
                    )
                    logger.info(
                        "No pending transcripts; checking for new voice every second "
                        "(backstop pass in up to %d minute(s))",
                        remaining_minutes,
                    )
                    _sleep_until_pending_or_backstop(
                        voice_dir,
                        transcripts_dir,
                        last_pass_time=last_pass_time,
                        interval_seconds=interval_seconds,
                    )
                continue

            remaining_minutes = max(
                1,
                int((interval_seconds - (time.time() - last_pass_time)) / 60),
            )
            logger.info(
                "Idle — checking for new voice every second "
                "(backstop pass in up to %d minute(s))",
                remaining_minutes,
            )
            _sleep_until_pending_or_backstop(
                voice_dir,
                transcripts_dir,
                last_pass_time=last_pass_time,
                interval_seconds=interval_seconds,
            )
    finally:
        stop_bot(_bot_proc)


if __name__ == "__main__":
    main()
