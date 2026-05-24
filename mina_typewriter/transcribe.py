"""Batch-transcribe audio and video files in a folder using OpenAI Whisper."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import whisper
from whisper.utils import format_timestamp

# --- Configuration (edit before running) ---

INPUT_DIR = Path("/path/to/your/audio/folder")
MODEL_NAME = "medium"
SUPPORTED_EXTENSIONS = (".mp4", ".m4a", ".wav")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


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
) -> None:
    """Transcribe one media file and write plain-text and segment outputs."""
    source_path = input_dir / filename
    out = output_dir or input_dir
    logger.info("Transcribing file: %s", source_path)

    result = model.transcribe(
        str(source_path),
        word_timestamps=True,
        fp16=False,
        verbose=True,
    )

    base = source_path.stem
    transcript_path = out / f"{base}.txt"
    transcript_path.write_text(result["text"], encoding="utf-8")
    logger.info("Transcription saved to: %s", transcript_path)

    segments_path = out / f"{base}_segments.txt"
    save_segments_txt(result, segments_path)
    logger.info("Timestamped segments saved to: %s", segments_path)


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
    logger.info("Loading Whisper model: %s", MODEL_NAME)
    model = whisper.load_model(MODEL_NAME)
    logger.info("Model loaded.")

    logger.info("Scanning directory: %s", INPUT_DIR)
    for filename in iter_media_files(INPUT_DIR):
        logger.info("Found audio/video file: %s", filename)
        transcribe_file(model, INPUT_DIR, filename)


if __name__ == "__main__":
    main()
