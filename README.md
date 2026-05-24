# mina-typewriter

![Mina Typewriter](assets/mina.png)

Batch-transcribe audio and video files using [OpenAI Whisper](https://github.com/openai/whisper). Run from the **CLI** (`transcribe.py`) for same-folder output, or use the **Streamlit app** (`app.py`) to transcribe only missing files into a separate output folder.

## Prerequisites

| Requirement | Why |
|-------------|-----|
| **Python 3.13+** | Project dependency (`requires-python` in `pyproject.toml`) |
| **[uv](https://docs.astral.sh/uv/)** | Installs dependencies and runs the script in a virtualenv |
| **ffmpeg** | Whisper uses ffmpeg to decode `.m4a`, `.mp4`, `.wav`, and other formats |

Install ffmpeg on macOS:

```bash
brew install ffmpeg
```

Verify:

```bash
ffmpeg -version
```

## Quick start

1. Clone or open this repo.

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Edit `transcribe.py` and set `INPUT_DIR` to the folder that contains your media:

   ```python
   INPUT_DIR = Path("/path/to/your/audio/folder")
   ```

4. Run:

   ```bash
   uv run python transcribe.py
   ```

   The first run downloads the Whisper model weights (size depends on the model; see below).

5. Find outputs next to each source file, e.g. `recording.m4a` → `recording.txt` and `recording_segments.txt`.

## Streamlit app

For separate input and output folders, use the web UI. It scans for media files that do not yet have a matching `.txt` transcript in the output folder and transcribes only those.

1. Install dependencies (includes Streamlit):

   ```bash
   uv sync
   ```

2. Run the app:

   ```bash
   uv run streamlit run app.py
   ```

3. Enter the **input folder** (media files) and **output folder** (transcripts).
4. Click **Scan** to list pending files.
5. Click **Transcribe pending** to process them. Each file produces `<basename>.txt` and `<basename>_segments.txt` in the output folder.

The first run downloads the Whisper model weights. Transcription is slow on CPU; the model is loaded once per session and reused for all pending files.

The app uses a dark theme styled to match the project artwork (`assets/mina.png`). Theme colors are configured in `.streamlit/config.toml`.

## What the script does

1. Loads a Whisper model once at startup (default: `medium`).
2. Scans `INPUT_DIR` for files ending in `.m4a`, `.mp4`, or `.wav`.
3. Transcribes each match and writes:
   - `<same-basename>.txt` — full transcript as plain UTF-8 text
   - `<same-basename>_segments.txt` — one line per segment with start/end timestamps
4. Logs progress to the terminal (model load, files found, transcribing, output paths).

Supported extensions are defined at the top of `transcribe.py`:

```python
SUPPORTED_EXTENSIONS = (".mp4", ".m4a", ".wav")
```

Add more extensions there if needed (e.g. `.mp3`, `.webm`), as long as ffmpeg can read them.

## Whisper models

Change the model in `transcribe.py`:

```python
MODEL_NAME = "medium"  # ← change this string
```

### Available model names

| Model | Parameters | English-only variant | Relative speed | Relative accuracy | VRAM (GPU, approx.) |
|-------|------------|----------------------|------------------|-------------------|---------------------|
| `tiny` | ~39M | `tiny.en` | Fastest | Lowest | ~1 GB |
| `base` | ~74M | `base.en` | Fast | Low–medium | ~1 GB |
| `small` | ~244M | `small.en` | Medium | Medium | ~2 GB |
| `medium` | ~769M | `medium.en` | Slow | High | ~5 GB |
| `large` | ~1550M | — | Slowest | Highest | ~10 GB |

Your installed version also supports `large-v1`, `large-v2`, `large-v3`, `large-v3-turbo`, and `turbo`. Full list from this project’s environment:

```text
tiny.en, tiny, base.en, base, small.en, small, medium.en, medium,
large-v1, large-v2, large-v3, large, large-v3-turbo, turbo
```

Re-run after upgrading Whisper:

```bash
uv run python -c "import whisper; print(whisper.available_models())"
```

### Choosing a model

- **`base`**: Good balance for laptop CPU; fine for clear speech in one language.
- **`medium`** (current default): Higher accuracy than `base`; noticeably slower on CPU.
- **`tiny` / `tiny.en`**: Fastest; useful for drafts or very long files on CPU.
- **`.en` variants** (`tiny.en`, `base.en`, …): Trained only on English; often slightly better for English-only audio.
- **`small` / `medium`**: Better accuracy, noticeably slower on CPU and larger download.
- **`large`**: Best quality; practical mainly with a GPU and enough RAM/VRAM.

Models are downloaded automatically on first use into your user cache (typically `~/.cache/whisper/`).

### CPU warning

On CPU you may see:

```text
UserWarning: FP16 is not supported on CPU; using FP32 instead
```

That is expected and safe to ignore.

## Transcription options

The script currently calls:

```python
result = model.transcribe(
    str(source_path),
    word_timestamps=True,
    fp16=False,
    verbose=True,
)
```

Whisper’s `transcribe()` accepts many optional arguments. Common ones you can pass in `transcribe_file()`:

| Option | Type | Description |
|--------|------|-------------|
| `language` | `str` | Force language (ISO 639-1), e.g. `"en"`, `"pt"`. If omitted, Whisper detects language. |
| `task` | `str` | `"transcribe"` (default) — output in source language. `"translate"` — output English text. |
| `verbose` | `bool` | Print segment-level progress during decoding. |
| `temperature` | `float` or tuple | Sampling temperature; lower can reduce randomness (default pipeline uses a fallback schedule). |
| `initial_prompt` | `str` | Hint words/names/style to bias the model (useful for proper nouns or jargon). |
| `word_timestamps` | `bool` | Include per-word timing in the result (enabled; segment timestamps are written to `_segments.txt`). |
| `fp16` | `bool` | Use half-precision on GPU. Set to `False` on CPU to avoid warnings. |

### Examples

Force Portuguese and keep transcription in Portuguese:

```python
result = model.transcribe(path, language="pt", task="transcribe")
```

Transcribe any language but get English text:

```python
result = model.transcribe(path, task="translate")
```

Bias spelling of names or domain terms:

```python
result = model.transcribe(
    path,
    language="en",
    initial_prompt="Guilherme, market research, data analyst.",
)
```

Show Whisper’s internal progress:

```python
result = model.transcribe(path, verbose=True)
```

The return value is a dict. This project uses `result["text"]` for the `.txt` file and `result["segments"]` for the `_segments.txt` file. Other keys include `language`, per-word timing inside segments, etc., if you want to extend the script later (e.g. SRT subtitles).

## Configuration reference

### CLI (`transcribe.py`)

Edit constants at the top of the file:

| Setting | Variable | Default |
|---------|----------|---------|
| Input folder | `INPUT_DIR` | Must be set by you |
| Model | `MODEL_NAME` | `medium` |
| Transcript output | `<basename>.txt` | Same directory as source |
| Segment output | `<basename>_segments.txt` | Same directory as source |
| File types | `SUPPORTED_EXTENSIONS` | `.mp4`, `.m4a`, `.wav` |

Run with `uv run python transcribe.py`.

### Streamlit app (`app.py`)

| Setting | Where | Default |
|---------|-------|---------|
| Input folder | Text input in the UI | — |
| Output folder | Text input in the UI | — |
| Model | Selectbox in the UI | `medium` (from `MODEL_NAME` in `transcribe.py`) |
| Pending detection | Automatic on Scan | Missing `<basename>.txt` in output folder |

Run with `uv run streamlit run app.py`.

## Project layout

```text
mina_typewriter/
├── app.py                # Streamlit UI (input/output folders)
├── assets/               # Artwork (mina.png) and AI prompt notes
│   ├── mina.png          # Primary hero image
│   └── PROMPTS.md        # Image generation prompts
├── .streamlit/
│   └── config.toml       # Streamlit theme (dark + gold)
├── pyproject.toml        # Dependencies (openai-whisper, streamlit)
├── uv.lock               # Locked dependency versions
├── transcribe.py         # Core transcription logic and CLI script
└── README.md             # This file
```

## Troubleshooting

### `FileNotFoundError: 'ffmpeg'`

Install ffmpeg (`brew install ffmpeg`) and ensure `ffmpeg` is on your `PATH`.

### `ModuleNotFoundError: No module named 'whisper'`

Run via uv so the project virtualenv is used:

```bash
uv run python transcribe.py
```

Not:

```bash
python3 transcribe.py   # may use a different Python without dependencies
```

### Wrong package: `wisper`

The PyPI package **`wisper`** is unrelated (AWS/protobuf tooling). This project uses **`openai-whisper`** (`import whisper`). Dependencies are declared in `pyproject.toml` as `openai-whisper`.

### REPL vs shell

If your prompt shows `>>>`, you are inside the Python REPL, not the terminal shell. Exit with `exit()` or Ctrl+D, then run `uv run python transcribe.py` from the shell.

### No files processed

- Confirm `INPUT_DIR` points to the correct directory.
- Confirm files use `.m4a`, `.mp4`, or `.wav` (or extend the suffix check).
- Hidden or non-media files are skipped.

### Slow transcription

- Use a smaller model (`tiny`, `base`).
- Shorter files transcribe faster; CPU transcription is much slower than GPU.
- The model loads once per run; processing many files in one run avoids reloading.

## License

Add a license here if you publish or share this repo.
