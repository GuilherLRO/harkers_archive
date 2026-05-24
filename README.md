# Harker's Archive

A personal **record base** built from many voice and text notes. Capture raw audio, transcribe with Whisper, and extend with more modules over time.

| Sub-project | Role |
|-------------|------|
| [`sewards_phonograph`](sewards_phonograph/) | Telegram bot — saves voice messages as `.ogg` files |
| [`mina_typewriter`](mina_typewriter/) | Whisper batch transcription (CLI + Streamlit) |

## Record base layout

```text
harkers_archive/
├── voice_archive/     # raw audio (.ogg from Telegram, etc.) — gitignored
├── transcripts/       # derived .txt from Whisper — gitignored
├── sewards_phonograph/
└── mina_typewriter/
```

## Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)**
- **ffmpeg** (for `mina_typewriter`; `brew install ffmpeg`)
- **Telegram bot token** (for `sewards_phonograph`)

## Quick start

1. Install all workspace dependencies from the repo root:

   ```bash
   uv sync
   ```

2. Copy environment template and set paths:

   ```bash
   cp .env.example .env
   # Edit SAVE_DIR and TELEGRAM_BOT_TOKEN
   ```

   Default voice archive path: `harkers_archive/voice_archive/` (absolute path in `SAVE_DIR`).

3. **Capture** — run the phonograph bot:

   ```bash
   cd sewards_phonograph
   cp .env.example .env   # if not using root .env
   uv run python bot.py
   ```

4. **Transcribe** — CLI (defaults to `../voice_archive`):

   ```bash
   cd mina_typewriter
   uv run python transcribe.py
   ```

   Or Streamlit (set input to `voice_archive`, output to `transcripts`):

   ```bash
   uv run streamlit run app.py
   ```

## Pipeline

```text
Telegram voice → sewards_phonograph → voice_archive/*.ogg
                                      → mina_typewriter → transcripts/*.txt
```

The CLI reads from `voice_archive/` by default. Override with `HARKERS_INPUT_DIR` if needed.

## Adding modules

Add a new top-level folder with its own `pyproject.toml`, then register it under `[tool.uv.workspace] members` in the root `pyproject.toml`. Shared data stays in `voice_archive/` and `transcripts/`.

## License

Add a license here if you publish or share this repo.
