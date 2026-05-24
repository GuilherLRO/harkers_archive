# Dr. Seward's Phonograph

Part of [Harker's Archive](../README.md). Companion to [Mina's Typewriter](../mina_typewriter): a Telegram bot that records voice messages to disk. Each voice note is saved as an `.ogg` file named with date, time, and the sender's Telegram user id.

## Prerequisites

| Requirement | Why |
|-------------|-----|
| **Python 3.13+** | Project dependency (`requires-python` in `pyproject.toml`) |
| **[uv](https://docs.astral.sh/uv/)** | Installs dependencies and runs the bot in a virtualenv |
| **Telegram bot token** | Create a bot via [@BotFather](https://t.me/BotFather) and copy the token |

## Quick start

1. Clone or open this repo.

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Set environment variables:

   ```bash
   export TELEGRAM_BOT_TOKEN="your-token-from-botfather"
   export SAVE_DIR="/absolute/path/to/harkers_archive/voice_archive"
   ```

4. Run the bot:

   ```bash
   uv run python bot.py
   ```

5. In Telegram, open your bot and send a **voice message** (hold the mic, record, release). The bot replies with the saved filename.

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

Only **voice messages** are saved. Text, photos, audio files, and video notes are ignored.

## Transcribing with mina_typewriter

From the monorepo root, `mina_typewriter` defaults to `../voice_archive`. Set `SAVE_DIR` to that same folder. See the [root README](../README.md) for the full capture → transcribe workflow.

## Project layout

```text
sewards_phonograph/
├── bot.py           # Telegram handlers and long polling
├── save_voice.py    # Download and filename logic
├── config.py        # TELEGRAM_BOT_TOKEN, SAVE_DIR from env
├── pyproject.toml
├── .env.example
└── README.md
```

## Running in the background

Keep the process running while you use the bot:

```bash
nohup uv run python bot.py >> bot.log 2>&1 &
```

Stop with `kill` on the process id. For a persistent setup, use launchd (macOS) or systemd (Linux).

## Manual test plan

1. Create a bot via [@BotFather](https://t.me/BotFather); set `TELEGRAM_BOT_TOKEN` and `SAVE_DIR`.
2. Run `uv run python bot.py` — the process should stay up and log "Bot started".
3. Send `/start` — bot should reply with instructions.
4. Send a voice note from your account — a file `YYYYMMDD_HHMMSS_<your_id>.ogg` should appear in `SAVE_DIR`; bot confirms the filename.
5. If you have a second Telegram account, send a voice note — filename should contain that account's user id.
6. Send plain text or a photo — bot should not save anything (no reply unless you use `/start`).
7. Stop the bot; open the `.ogg` in QuickTime or VLC, or verify with `ffmpeg -i <file>`.

## Troubleshooting

### `ConfigurationError: TELEGRAM_BOT_TOKEN is not set`

Export `TELEGRAM_BOT_TOKEN` before starting the bot (see `.env.example`).

### `ConfigurationError: SAVE_DIR is not set`

Export `SAVE_DIR` to an absolute path. The directory is created automatically if it does not exist.

### Bot does not respond

- Confirm the bot process is running (`uv run python bot.py`).
- Confirm the token is correct (no extra spaces).
- In Telegram, you must open a chat with **your** bot (search its username from BotFather).

### `Unauthorized` or invalid token

Regenerate the token in BotFather if needed and update `TELEGRAM_BOT_TOKEN`.

### Cannot write to `SAVE_DIR`

Use a path your user can create and write to (e.g. under your home directory).

## License

Add a license here if you publish or share this repo.
