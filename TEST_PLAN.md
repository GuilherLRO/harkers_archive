# Harker's Archive Test Plan

Use this plan before release-like changes, after coordinator changes, or when moving the archive runner to a new machine. The repository currently has automated unit tests for Rainfields Mind; the Telegram, OpenAI transcription, and end-to-end flows still require smoke or manual checks because they depend on credentials, network access, and real files.

## Fast Checks

Run these after any Python or documentation change:

```bash
uv sync --all-packages
uv run python -m py_compile helsings_round.py archive_logging.py
cd rainfields_mind/agent && uv run pytest
```

Expected result:

- `py_compile` exits cleanly for the root coordinator and shared logging module.
- Rainfields Mind tests pass for week grouping, manifest dirty detection, validation, index writing, tag parsing, and the CLI dry-run path.

## Module Checks

### Seward's Phonograph

Purpose: confirm Telegram capture writes the expected raw archive files.

Checks:

- Start the bot from `sewards_phonograph/` with a real `TELEGRAM_BOT_TOKEN` and absolute `SAVE_DIR`.
- Send `/start` and confirm the bot responds.
- Send a voice note and confirm `voice_archive/YYYYMMDD_HHMMSS_<user_id>.ogg` appears.
- Send a plain text note and confirm `transcripts/typed_notes_YYYYMMDD_<user_id>.txt` is appended with a timestamp.
- Stop the process and confirm no duplicate bot process is left running.

### Mina's Typewriter

Purpose: confirm audio transcription via the OpenAI API is repeatable and idempotent.

Checks:

- Set `OPENAI_API_KEY` in the repo root `.env`.
- Place a small known audio file in `voice_archive/`.
- Run `cd mina_typewriter && uv run python transcribe.py`.
- Confirm `<basename>.txt` and `<basename>_segments.txt` appear in `transcripts/` (segments require `MINA_TRANSCRIBE_MODEL=whisper-1`).
- Re-run the command and confirm already-transcribed files are skipped rather than duplicated.
- With `helsings_round.py` running, drop a new `.ogg` in `voice_archive/` (or send a Telegram voice note) and confirm transcription starts within `TRANSCRIBE_PENDING_POLL_SECONDS` (default 60s).
- If Streamlit UI changes, run `uv run streamlit run app.py` and verify folder selection plus one transcription pass.

### Van Helsing's Dossier

Purpose: confirm transcripts become stable daily Markdown.

Checks:

- Create fixture transcripts for at least two dates, including one voice transcript and one `typed_notes_YYYYMMDD_<user_id>.txt`.
- Run `cd van_helsings_dossier && uv run python compile.py --json-summary`.
- Confirm `dossier/YYYY-MM-DD.md` files are written for the expected dates.
- Re-run and confirm unchanged days are skipped or reported as unchanged.
- Edit one source transcript and confirm only the affected day is rebuilt.

### Rainfields Mind

Purpose: confirm weekly synthesis updates only dirty weeks and preserves source provenance.

Checks:

- Run `cd rainfields_mind/agent && uv run pytest`.
- Run `uv run python compile_week.py --dry-run --json-summary` and confirm it reports dirty weeks without calling the LLM.
- With `OPENAI_API_KEY` configured, run `uv run python compile_week.py --week YYYY-WNN --json-summary`.
- Confirm `rainfields_mind/weekly/YYYY-WNN.md`, `rainfields_mind/index.md`, and any candidate tags are updated as expected.
- Re-run without changes and confirm the agent skips with `no_dirty_weeks`.

### Helsing's Round

Purpose: confirm the coordinator glues the modules together without blocking capture.

Checks:

- Set a test `.env` with absolute paths, `TRANSCRIBE_PENDING_POLL_SECONDS=10`, `TRANSCRIBE_INTERVAL_MINUTES=1440`, `DOSSIER_INTERVAL_MINUTES=1`, and a disposable Telegram bot token.
- Run `uv run python helsings_round.py` from the repo root.
- Confirm the bot starts, startup notification is sent when `STARTUP_NOTIFY_ENABLED=true`, and `SIGINT` stops the bot subprocess.
- Add a voice note and confirm transcription starts within the pending poll interval (not only on the daily backstop).
- After transcription, confirm the order: each new transcript `.txt` sent as a Telegram document, dossier compile, Rainfields compile, weekly note delivery on the dossier schedule.
- Confirm each newly transcribed voice file yields one Telegram document named like `YYYYMMDD_HHMMSS_<user_id>.txt`.
- Confirm the Telegram weekly document delivery sends the latest `rainfields_mind/weekly/YYYY-WNN.md`, not a daily dossier.
- Temporarily make `compile_week.py` fail and confirm the coordinator logs a warning and continues.

## End-to-End Acceptance

Use this when changing shared paths, scheduling, or delivery behavior:

1. Start `helsings_round.py` with a disposable archive directory.
2. Send one voice note and one typed Telegram note.
3. Wait for the pending poll (default ~60s) or backstop pass.
4. Verify files in order: `voice_archive/`, `transcripts/`, `dossier/`, `rainfields_mind/weekly/`.
5. Verify Telegram messages: each new transcript `.txt` as a document; latest weekly note document on the daily delivery schedule.
6. Restart with `./helsings_roundctl.sh restart` and confirm only one bot process remains.

## Gaps To Automate Later

- Unit tests for `helsings_round.py` scheduling decisions, latest weekly file selection, and failure handling.
- Fixture-based tests for `van_helsings_dossier/compile.py`.
- Small-audio fixture smoke tests for `mina_typewriter/transcribe.py` with the OpenAI API call mocked.
- Telegram bot handler tests with the Telegram API mocked.
