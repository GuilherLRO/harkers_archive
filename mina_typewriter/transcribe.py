"""Batch-transcribe audio and video files in a folder using OpenAI Whisper."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import whisper
from dotenv import load_dotenv
from whisper.utils import format_timestamp

# --- Configuration (edit before running) ---

_ARCHIVE_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ARCHIVE_ROOT / ".env")
INPUT_DIR = Path(
    os.environ.get("HARKERS_INPUT_DIR", _ARCHIVE_ROOT / "voice_archive")
)
OUTPUT_DIR = Path(
    os.environ.get("HARKERS_OUTPUT_DIR", _ARCHIVE_ROOT / "transcripts")
)
MODEL_NAME = "medium"
SUPPORTED_EXTENSIONS = (".mp4", ".m4a", ".wav", ".ogg")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


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


def _audio_duration(result: dict) -> float:
    segments = result.get("segments") or []
    if not segments:
        return 0.0
    return float(segments[-1]["end"])


def _progress_label(index: int | None, total: int | None) -> str:
    if index is not None and total is not None:
        return f"[{index}/{total}] "
    return ""


def save_segments_txt(result: dict, output_path: Path) -> None:
    """Write timestamped segments in Whisper's verbose console format."""
    with output_path.open("w", encoding="utf-8") as file:
        for segment in result["segments"]:
            start = format_timestamp(segment["start"])
            end = format_timestamp(segment["end"])
            text = segment["text"].strip()
            if text:
                file.write(f"[{start} --> {end}] {text}\n")


def transcribe_file(
    model: whisper.Whisper,
    input_dir: Path,
    filename: str,
    output_dir: Path | None = None,
    *,
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
    result = model.transcribe(
        str(source_path),
        word_timestamps=True,
        fp16=False,
        verbose=False,
    )
    elapsed = time.perf_counter() - started

    base = source_path.stem
    transcript_path = out / f"{base}.txt"
    transcript_text = result["text"]
    transcript_path.write_text(transcript_text, encoding="utf-8")

    segments_path = out / f"{base}_segments.txt"
    segments = result.get("segments") or []
    save_segments_txt(result, segments_path)

    language = result.get("language", "unknown")
    logger.info(
        "%sDone %s — language=%s, audio=%s, segments=%d, chars=%d, took=%s",
        prefix,
        filename,
        language,
        _format_seconds(_audio_duration(result)),
        len(segments),
        len(transcript_text),
        _format_seconds(elapsed),
    )
    logger.info("%sWrote %s", prefix, transcript_path)
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

    logger.info("Loading Whisper model: %s", MODEL_NAME)
    model_load_started = time.perf_counter()
    model = whisper.load_model(MODEL_NAME)
    logger.info("Model loaded in %s", _format_seconds(time.perf_counter() - model_load_started))

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
                model,
                INPUT_DIR,
                filename,
                OUTPUT_DIR,
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
