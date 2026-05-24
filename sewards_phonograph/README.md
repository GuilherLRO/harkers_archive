# Dr. Seward's Phonograph

![Dr. Seward's Phonograph](seward-phonograph/seward-phonograph-primary.png)

Part of [Harker's Archive](../README.md). Companion to [Mina's Typewriter](../mina_typewriter): a Telegram bot that **captures voice messages** and saves them to the shared record base. Each voice note becomes an `.ogg` file named with date, time, and the sender's Telegram user id.

In *Dracula*, Seward dictated his diary into a phonograph; Mina typed the transcripts. This project pair mirrors that flow: **record here → transcribe there**.

## Prerequisites

| Requirement | Why |
|-------------|-----|
| **Python 3.13+** | Project dependency (`requires-python` in `pyproject.toml`) |
| **[uv](https://docs.astral.sh/uv/)** | Installs dependencies and runs the bot in a virtualenv |
| **Telegram bot token** | Create a bot via [@BotFather](https://t.me/BotFather) and copy the token |

## Quick start

1. From the [monorepo root](../README.md), install workspace dependencies:

   ```bash
   uv sync
   ```

2. Configure environment (use an **absolute** path for `SAVE_DIR`):

   ```bash
   cd sewards_phonograph
   cp .env.example .env
   # Edit TELEGRAM_BOT_TOKEN and SAVE_DIR
   ```

   Example `SAVE_DIR` (shared archive at repo root):

   ```bash
   SAVE_DIR=/absolute/path/to/harkers_archive/voice_archive
   ```

   Or export in your shell:

   ```bash
   export TELEGRAM_BOT_TOKEN="your-token-from-botfather"
   export SAVE_DIR="/absolute/path/to/harkers_archive/voice_archive"
   ```

3. Run the bot:

   ```bash
   uv run python bot.py
   ```

   You should see `Bot started` in the logs. The process must stay running while you use Telegram.

4. In Telegram, open **your** bot (username from BotFather) and send a **voice message** (hold the mic, record, release). The bot replies with the saved filename.

5. Transcribe with [Mina's Typewriter](../mina_typewriter) when you are ready (transcription is **not** automatic):

   ```bash
   cd ../mina_typewriter
   uv run python transcribe.py
   ```

   Or use the Streamlit app with input `../voice_archive` and output `../transcripts`.

## What the bot does

1. Loads `TELEGRAM_BOT_TOKEN` and `SAVE_DIR` from the environment (`.env` via `python-dotenv`, or exported variables).
2. Long-polls the Telegram Bot API for updates.
3. On a **voice message**, downloads the Opus audio and writes `{YYYYMMDD}_{HHMMSS}_{user_id}.ogg` under `SAVE_DIR` (creates the folder if needed).
4. Replies in chat with the saved filename.
5. Ignores text, photos, audio files, and video notes. Responds to `/start` and `/help` with usage instructions.

## Filename format

Voice files use local time (24-hour) and the sender's numeric Telegram user id:

```text
{YYYYMMDD}_{HHMMSS}_{telegram_user_id}.ogg
```

| Part | Example | Meaning |
|------|---------|---------|
| Date | `20260524` | Year, month, day |
| Time | `151230` | Hour, minute, second |
| User id | `123456789` | `update.effective_user.id` |
| Extension | `.ogg` | Telegram voice format (Opus) |

Example: `20260524_151230_123456789.ogg`

If two voice notes from the same user arrive in the same second, the bot appends `_2`, `_3`, … before `.ogg` to avoid overwriting.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and usage |
| `/help` | Same as `/start` |

Only **voice messages** are saved.

## Pipeline with Mina's Typewriter

```text
Telegram voice → sewards_phonograph → voice_archive/*.ogg
                                      → mina_typewriter → transcripts/*.txt
```

| Step | Tool | Automatic? |
|------|------|--------------|
| Capture | This bot | Yes, while `bot.py` is running |
| Transcribe | `mina_typewriter` | No — run CLI or Streamlit manually |

Point `SAVE_DIR` at the same folder `mina_typewriter` reads (`../voice_archive` by default). See the [root README](../README.md).

## Configuration reference

| Setting | Variable | Where |
|---------|----------|--------|
| Bot token | `TELEGRAM_BOT_TOKEN` | `.env` or shell |
| Voice archive | `SAVE_DIR` | Absolute path; e.g. `harkers_archive/voice_archive` |

Run with `uv run python bot.py` from this directory (or `uv run --directory sewards_phonograph python bot.py` from the repo root).

## Project layout

```text
sewards_phonograph/
├── bot.py                    # Telegram handlers and long polling
├── save_voice.py             # Download and filename logic
├── config.py                 # TELEGRAM_BOT_TOKEN, SAVE_DIR from env
├── pyproject.toml
├── uv.lock
├── .env.example
├── README.md                 # This file
└── seward-phonograph/        # Artwork and AI prompt notes
    ├── seward-phonograph-primary.png   # README hero
    ├── seward-phonograph-logo.png      # Icon (1:1)
    ├── seward-phonograph-banner.png    # Banner (16:9)
    ├── seward-phonograph-dictation.png
    ├── seward-phonograph-study.png
    └── PROMPTS.md            # Image generation prompts
```

## Artwork

Victorian-themed illustrations use a **purple / violet / indigo** palette (paired with Mina's gold in [Mina's Typewriter](../mina_typewriter)). Prompts and file roles are documented in [`seward-phonograph/PROMPTS.md`](seward-phonograph/PROMPTS.md).

| File | Use |
|------|-----|
| `seward-phonograph-primary.png` | README hero — recording at the phonograph |
| `seward-phonograph-logo.png` | Icon variant (1:1) |
| `seward-phonograph-banner.png` | Wide banner (16:9) |
| `seward-phonograph-dictation.png` | Close-up — dictation in progress |
| `seward-phonograph-study.png` | Full study scene |

### Palette

| Color | Hex |
|-------|-----|
| Purple | `#7B4FBF` |
| Violet | `#9B59B6` |
| Indigo | `#4A3270` |
| Lavender accent | `#B57EDC` |
| Background | `#1a1a2e` |

## Running in the background

Keep the process running while you use the bot:

```bash
nohup uv run python bot.py >> bot.log 2>&1 &
```

Stop with `kill` on the process id. For a persistent setup, use launchd (macOS) or systemd (Linux).

## Manual test plan

1. Create a bot via [@BotFather](https://t.me/BotFather); set `TELEGRAM_BOT_TOKEN` and `SAVE_DIR` in `.env`.
2. Run `uv run python bot.py` — the process should stay up and log "Bot started".
3. Send `/start` — bot should reply with instructions.
4. Send a voice note from your account — a file `YYYYMMDD_HHMMSS_<your_id>.ogg` should appear in `SAVE_DIR`; bot confirms the filename.
5. If you have a second Telegram account, send a voice note — filename should contain that account's user id.
6. Send plain text or a photo — bot should not save anything (no reply unless you use `/start`).
7. Stop the bot; open the `.ogg` in QuickTime or VLC, or verify with `ffmpeg -i <file>`.
8. Run `mina_typewriter` on `SAVE_DIR` and confirm a `.txt` transcript is produced.

## Troubleshooting

### `ConfigurationError: TELEGRAM_BOT_TOKEN is not set`

Set `TELEGRAM_BOT_TOKEN` in `.env` or export it before starting the bot (see `.env.example`).

### `ConfigurationError: SAVE_DIR is not set`

Set `SAVE_DIR` to an **absolute** path. The directory is created automatically if it does not exist.

### Bot does not respond

- Confirm the bot process is running (`uv run python bot.py`).
- Confirm the token is correct (no extra spaces).
- In Telegram, open a chat with **your** bot (search its username from BotFather).

### `Unauthorized` or invalid token

Regenerate the token in BotFather if needed and update `TELEGRAM_BOT_TOKEN`.

### Cannot write to `SAVE_DIR`

Use a path your user can create and write to (e.g. `harkers_archive/voice_archive` under your home directory).

### `ModuleNotFoundError` or wrong Telegram package

Run via uv from this directory:

```bash
uv run python bot.py
```

Not:

```bash
python3 bot.py   # may use a different Python without dependencies
```

This project uses **`python-telegram-bot`** (`from telegram import ...`). The PyPI package **`telegram`** (stub) is not used.

### Voice saves but nothing transcribes

Transcription is a separate step. Run [Mina's Typewriter](../mina_typewriter) after capture; see **Pipeline** above.

## License

Add a license here if you publish or share this repo.
