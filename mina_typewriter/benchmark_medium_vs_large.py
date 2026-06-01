#!/usr/bin/env python3
"""Isolated benchmark: compare Whisper medium vs large wall-clock time.

Does not use transcribe.py batch logic and does not write to transcripts/.
Run from mina_typewriter:

    uv run python benchmark_medium_vs_large.py
    uv run python benchmark_medium_vs_large.py --audio ../voice_archive/foo.ogg
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import whisper

_ARCHIVE_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_AUDIO = _ARCHIVE_ROOT / "voice_archive" / "20260524_221738_390353883.ogg"
_MODELS = ("medium", "large")


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


def _benchmark_model(model_name: str, audio_path: Path) -> dict[str, float]:
    load_started = time.perf_counter()
    model = whisper.load_model(model_name)
    load_elapsed = time.perf_counter() - load_started

    transcribe_started = time.perf_counter()
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        fp16=False,
        verbose=False,
    )
    transcribe_elapsed = time.perf_counter() - transcribe_started

    audio_seconds = _audio_duration(result)
    realtime_factor = (
        transcribe_elapsed / audio_seconds if audio_seconds > 0 else float("inf")
    )

    return {
        "load_s": load_elapsed,
        "transcribe_s": transcribe_elapsed,
        "total_s": load_elapsed + transcribe_elapsed,
        "audio_s": audio_seconds,
        "realtime_factor": realtime_factor,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Whisper medium vs large on one audio file."
    )
    parser.add_argument(
        "--audio",
        type=Path,
        default=_DEFAULT_AUDIO,
        help=f"Media file to transcribe (default: {_DEFAULT_AUDIO.name})",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        choices=_MODELS,
        default=list(_MODELS),
        help="Models to compare (default: medium large)",
    )
    args = parser.parse_args()

    audio_path = args.audio.resolve()
    if not audio_path.is_file():
        raise SystemExit(f"Audio file not found: {audio_path}")

    print(f"Benchmark audio: {audio_path} ({audio_path.stat().st_size / 1024:.1f} KB)")
    print(f"Models: {', '.join(args.models)}")
    print("(results are discarded; nothing is written to transcripts/)\n")

    results: dict[str, dict[str, float]] = {}
    for model_name in args.models:
        print(f"--- {model_name} ---")
        stats = _benchmark_model(model_name, audio_path)
        results[model_name] = stats
        print(
            f"  load={_format_seconds(stats['load_s'])}, "
            f"transcribe={_format_seconds(stats['transcribe_s'])}, "
            f"audio={_format_seconds(stats['audio_s'])}, "
            f"realtime_factor={stats['realtime_factor']:.1f}x"
        )
        print()

    if "medium" in results and "large" in results:
        medium, large = results["medium"], results["large"]
        print("--- comparison (large / medium) ---")
        for label, key in (
            ("load", "load_s"),
            ("transcribe", "transcribe_s"),
            ("total (load+transcribe)", "total_s"),
            ("realtime factor", "realtime_factor"),
        ):
            ratio = large[key] / medium[key] if medium[key] > 0 else float("inf")
            print(f"  {label}: {ratio:.2f}x")


if __name__ == "__main__":
    main()
