# Mina's Typewriter

![Mina's Typewriter](assets/mina.png)

Part of [Harker's Archive](../README.md). Batch-transcribe audio and video files using the [OpenAI Audio Transcriptions API](https://platform.openai.com/docs/guides/speech-to-text). Run from the **CLI** (`transcribe.py`) to read `voice_archive/` and write to `transcripts/`, or use the **Streamlit app** (`app.py`) to pick custom input/output folders.

## Prerequisites

| Requirement | Why |
|-------------|-----|
| **Python 3.13+** | Project dependency (`requires-python` in `pyproject.toml`) |
| **[uv](https://docs.astral.sh/uv/)** | Installs dependencies and runs the script in a virtualenv |
| **`OPENAI_API_KEY`** | Required in the repo root `.env` for API calls |

## Quick start

1. From the [monorepo root](../README.md), install workspace dependencies:

   ```bash
   uv sync --all-packages
   ```

2. Set `OPENAI_API_KEY` in the root `.env` (copy from `.env.example` if needed).

3. Run the CLI (reads `voice_archive/`, writes to `transcripts/` by default):

   ```bash
   cd mina_typewriter
   uv run python transcribe.py
   ```

   Override with `HARKERS_INPUT_DIR` and `HARKERS_OUTPUT_DIR` in the root `.env` if needed.

4. Find outputs in `transcripts/`, e.g. `20260524_151230_123456789.ogg` → `20260524_151230_123456789.txt` and `20260524_151230_123456789_segments.txt`.

   Note: typed notes from [Seward's Phonograph](../sewards_phonograph/) (`typed_notes_*.txt`) are saved directly to `transcripts/` and are not processed by this tool.

## Streamlit app

For separate input and output folders, use the web UI. It scans for media files that do not yet have a matching `.txt` transcript in the output folder and transcribes only those.

1. Install dependencies from the repo root:

   ```bash
   uv sync --all-packages
   ```

2. Run the app:

   ```bash
   cd mina_typewriter
   uv run streamlit run app.py
   ```

3. Enter the **input folder** (media files) and **output folder** (transcripts).
4. Choose an OpenAI model (`whisper-1` recommended — includes segment timestamps).
5. Click **Scan** to list pending files.
6. Click **Transcribe pending** to process them. Each file produces `<basename>.txt` and (with `whisper-1`) `<basename>_segments.txt` in the output folder.

The app uses a dark theme styled to match the project artwork (`assets/mina.png`). Theme colors are configured in `.streamlit/config.toml`.

## What the script does

1. Connects to the OpenAI Audio API using `OPENAI_API_KEY`.
2. Scans `INPUT_DIR` for files ending in `.m4a`, `.mp4`, `.wav`, or `.ogg`.
3. Skips files that already have a matching `.txt` in the output folder.
4. Transcribes each pending file and writes:
   - `<same-basename>.txt` — full transcript as plain UTF-8 text
   - `<same-basename>_segments.txt` — one line per segment with start/end timestamps (whisper-1 only)
5. Logs progress to the terminal (files found, transcribing, output paths).

Supported extensions are defined at the top of `transcribe.py`:

```python
SUPPORTED_EXTENSIONS = (".mp4", ".m4a", ".wav", ".ogg", ".WAV")
```

Add more extensions there if needed, as long as the OpenAI API accepts the format. Telegram voice notes from `sewards_phonograph` use `.ogg`.

## Models

Set the model in the root `.env`:

```bash
MINA_TRANSCRIBE_MODEL=whisper-1
```

| Model | Segments (`_segments.txt`) | Notes |
|-------|---------------------------|-------|
| `whisper-1` (default) | Yes | Uses `verbose_json` with segment timestamps |
| `gpt-4o-mini-transcribe` | No | Text-only; faster/cheaper but no timestamp sidecar |

The Streamlit app lets you pick between these models per session.

## Configuration reference

### CLI (`transcribe.py`)

| Setting | Variable | Default |
|---------|----------|---------|
| Input folder | `HARKERS_INPUT_DIR` | `voice_archive/` at repo root |
| Output folder | `HARKERS_OUTPUT_DIR` | `transcripts/` at repo root |
| Model | `MINA_TRANSCRIBE_MODEL` | `whisper-1` |
| API key | `OPENAI_API_KEY` | Required |
| API base URL | `OPENAI_API_BASE` | Optional (official OpenAI endpoint recommended for audio) |
| Transcript output | `<basename>.txt` | `OUTPUT_DIR` |
| Segment output | `<basename>_segments.txt` | `OUTPUT_DIR` (whisper-1 only) |
| File types | `SUPPORTED_EXTENSIONS` | `.mp4`, `.m4a`, `.wav`, `.ogg` |

Run with `uv run python transcribe.py`.

### Streamlit app (`app.py`)

| Setting | Where | Default |
|---------|-------|---------|
| Input folder | Text input in the UI | — |
| Output folder | Text input in the UI | — |
| Model | Selectbox in the UI | `whisper-1` |
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
├── pyproject.toml        # Dependencies (openai, streamlit)
├── transcribe.py         # Core transcription logic and CLI script
└── README.md             # This file
```

Dependencies are locked at the monorepo root (`../uv.lock`). Run `uv sync --all-packages` from the repo root.

## Limitations

- **25 MB file limit** — OpenAI rejects uploads larger than 25 MB. Long voice chains or large video files may fail; check logs for the affected filename.
- **Cost** — API billing is per audio minute. Monitor usage if transcription runs on a schedule via `helsings_round.py`.
- **Privacy** — audio is sent to OpenAI for processing (unlike the previous local Whisper setup).
- **Network** — the host or container must reach `api.openai.com` (or your configured `OPENAI_API_BASE` if it supports `/audio/transcriptions`).

## Troubleshooting

### `ConfigurationError: OPENAI_API_KEY is required`

Set `OPENAI_API_KEY` in the repo root `.env` file.

### `ModuleNotFoundError: No module named 'openai'`

Run via uv so the project virtualenv is used:

```bash
uv run python transcribe.py
```

### API errors (429, 5xx)

The script retries transient errors up to two times with backoff. Persistent failures are logged per file; the batch continues with remaining files.

### No files processed

- Confirm `INPUT_DIR` points to the correct directory.
- Confirm files use `.m4a`, `.mp4`, `.wav`, or `.ogg` (or extend the suffix check).
- Hidden or non-media files are skipped.

### Missing `_segments.txt`

Only `whisper-1` produces segment sidecars. If you set `MINA_TRANSCRIBE_MODEL=gpt-4o-mini-transcribe`, only `.txt` files are written.

## License

Add a license here if you publish or share this repo.
