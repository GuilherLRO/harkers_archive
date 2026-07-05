"""Batch-transcribe audio and video files in a folder using the OpenAI Audio API."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

# --- Configuration (edit before running) ---

_ARCHIVE_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ARCHIVE_ROOT / ".env")
INPUT_DIR = Path(
    os.environ.get("HARKERS_INPUT_DIR", _ARCHIVE_ROOT / "voice_archive")
)
OUTPUT_DIR = Path(
    os.environ.get("HARKERS_OUTPUT_DIR", _ARCHIVE_ROOT / "transcripts")
)
MODEL_NAME = os.environ.get("MINA_TRANSCRIBE_MODEL", "whisper-1").strip() or "whisper-1"
SUPPORTED_EXTENSIONS = (".mp4", ".m4a", ".wav", ".ogg", ".WAV")
SEGMENT_MODELS = frozenset({"whisper-1"})
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    pass


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _format_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remainder = divmod(int(seconds), 60)
    return f"{minutes}m {remainder}s"


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS.mmm (matches van_helsings_dossier segment parser)."""
    millis = int(round(max(0.0, seconds) * 1000))
    minutes, millis = divmod(millis, 60_000)
    seconds_part, millis_part = divmod(millis, 1000)
    return f"{minutes:02d}:{seconds_part:02d}.{millis_part:03d}"


def _audio_duration(segments: list) -> float:
    if not segments:
        return 0.0
    last = segments[-1]
    end = last.get("end") if isinstance(last, dict) else getattr(last, "end", 0.0)
    return float(end)


def _progress_label(index: int | None, total: int | None) -> str:
    if index is not None and total is not None:
        return f"[{index}/{total}] "
    return ""


def _segment_fields(segment) -> tuple[float, float, str]:
    if isinstance(segment, dict):
        return float(segment["start"]), float(segment["end"]), str(segment["text"]).strip()
    return float(segment.start), float(segment.end), str(segment.text).strip()


def supports_segments(model: str) -> bool:
    return model in SEGMENT_MODELS


def create_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            "OPENAI_API_KEY is required for Mina's Typewriter. "
            "Set it in the repo root .env file."
        )
    base_url = os.environ.get("OPENAI_API_BASE", "").strip()
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def save_segments_txt(segments: list, output_path: Path) -> None:
    """Write timestamped segments in Whisper's verbose console format."""
    with output_path.open("w", encoding="utf-8") as file:
        for segment in segments:
            start_s, end_s, text = _segment_fields(segment)
            if not text:
                continue
            start = format_timestamp(start_s)
            end = format_timestamp(end_s)
            file.write(f"[{start} --> {end}] {text}\n")


def transcribe_with_retries(
    client: OpenAI,
    source_path: Path,
    *,
    model: str,
) -> object:
    last_error: BaseException | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with source_path.open("rb") as audio:
                if supports_segments(model):
                    return client.audio.transcriptions.create(
                        model=model,
                        file=audio,
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                    )
                return client.audio.transcriptions.create(
                    model=model,
                    file=audio,
                    response_format="json",
                )
        except (RateLimitError, APIConnectionError, APIStatusError) as exc:
            last_error = exc
            status = getattr(exc, "status_code", None)
            retryable = isinstance(exc, (RateLimitError, APIConnectionError)) or (
                isinstance(exc, APIStatusError) and status is not None and status >= 500
            )
            if not retryable or attempt >= MAX_RETRIES:
                raise
            delay = RETRY_BACKOFF_SECONDS * (attempt + 1)
            logger.warning(
                "Transcription API error for %s (attempt %d/%d): %s — retrying in %.1fs",
                source_path.name,
                attempt + 1,
                MAX_RETRIES + 1,
                exc,
                delay,
            )
            time.sleep(delay)
    assert last_error is not None
    raise last_error


def transcribe_file(
    client: OpenAI,
    input_dir: Path,
    filename: str,
    output_dir: Path | None = None,
    *,
    model: str = MODEL_NAME,
    index: int | None = None,
    total: int | None = None,
) -> None:
    """Transcribe one media file and write plain-text and segment outputs."""
    source_path = input_dir / filename
    out = output_dir if output_dir is not None else input_dir
    out.mkdir(parents=True, exist_ok=True)
    prefix = _progress_label(index, total)
    file_size = source_path.stat().st_size

    if out != input_dir:
        logger.info(
            "%sTranscribing %s (%s) → %s",
            prefix,
            filename,
            _format_bytes(file_size),
            out,
        )
    else:
        logger.info(
            "%sTranscribing %s (%s)",
            prefix,
            filename,
            _format_bytes(file_size),
        )

    started = time.perf_counter()
    result = transcribe_with_retries(client, source_path, model=model)
    elapsed = time.perf_counter() - started

    base = source_path.stem
    transcript_path = out / f"{base}.txt"
    transcript_text = getattr(result, "text", "") or ""
    transcript_path.write_text(transcript_text, encoding="utf-8")

    segments = getattr(result, "segments", None) or []
    segments_path = out / f"{base}_segments.txt"
    if segments:
        save_segments_txt(segments, segments_path)
    elif supports_segments(model):
        segments_path.write_text("", encoding="utf-8")
    else:
        logger.warning(
            "%sModel %s does not support segment timestamps — skipping %s",
            prefix,
            model,
            segments_path.name,
        )

    language = getattr(result, "language", None) or "unknown"
    logger.info(
        "%sDone %s — language=%s, audio=%s, segments=%d, chars=%d, took=%s",
        prefix,
        filename,
        language,
        _format_seconds(_audio_duration(segments)),
        len(segments),
        len(transcript_text),
        _format_seconds(elapsed),
    )
    logger.info("%sWrote %s", prefix, transcript_path)
    if segments or supports_segments(model):
        logger.info("%sWrote %s", prefix, segments_path)


def iter_media_files(input_dir: Path) -> list[str]:
    """Return supported media filenames in lexicographic order."""
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {input_dir}")

    return sorted(
        name
        for name in os.listdir(input_dir)
        if name.endswith(SUPPORTED_EXTENSIONS)
    )


def missing_transcriptions(input_dir: Path, output_dir: Path) -> list[str]:
    """Return media filenames in input_dir with no matching .txt in output_dir."""
    return [
        name
        for name in iter_media_files(input_dir)
        if not (output_dir / f"{Path(name).stem}.txt").is_file()
    ]


def main() -> None:
    run_started = time.perf_counter()
    input_dir = INPUT_DIR.resolve()
    output_dir = OUTPUT_DIR.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Starting batch transcription — model=%s, input=%s, output=%s, extensions=%s",
        MODEL_NAME,
        input_dir,
        output_dir,
        ", ".join(SUPPORTED_EXTENSIONS),
    )

    client = create_client()
    if not supports_segments(MODEL_NAME):
        logger.warning(
            "Model %s does not support segment timestamps; only .txt files will be written",
            MODEL_NAME,
        )

    all_media = iter_media_files(INPUT_DIR)
    if not all_media:
        logger.warning(
            "No media files found in %s (supported: %s)",
            input_dir,
            ", ".join(SUPPORTED_EXTENSIONS),
        )
        return

    files = missing_transcriptions(INPUT_DIR, OUTPUT_DIR)
    skipped = len(all_media) - len(files)
    if skipped:
        logger.info(
            "Skipping %d file(s) that already have transcripts in %s",
            skipped,
            output_dir,
        )
    if not files:
        logger.info("Nothing to transcribe — all media files already have transcripts.")
        return

    logger.info("Found %d file(s) to transcribe", len(files))

    succeeded = 0
    failed = 0
    for index, filename in enumerate(files, start=1):
        try:
            transcribe_file(
                client,
                INPUT_DIR,
                filename,
                OUTPUT_DIR,
                model=MODEL_NAME,
                index=index,
                total=len(files),
            )
        except Exception:
            failed += 1
            logger.exception("[%d/%d] Failed: %s", index, len(files), filename)
        else:
            succeeded += 1

    logger.info(
        "Batch complete — %d succeeded, %d failed, total time %s",
        succeeded,
        failed,
        _format_seconds(time.perf_counter() - run_started),
    )


if __name__ == "__main__":
    main()
