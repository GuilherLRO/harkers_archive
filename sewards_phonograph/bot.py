"""Telegram bot that archives voice messages to a configured folder."""

from __future__ import annotations

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import ConfigurationError, load_bot_token, load_save_dir, load_transcripts_dir
from save_text_note import append_text_note
from save_voice import save_voice_message


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Dr. Seward's Phonograph archives your notes to disk.\n\n"
    "Voice message → voice_archive/:\n"
    "  YYYYMMDD_HHMMSS_<your_telegram_id>.ogg\n\n"
    "Plain text → transcripts/:\n"
    "  typed_notes_YYYYMMDD_<your_telegram_id>.txt\n"
    "  (one file per day; each line prefixed with [YYYYMMDD_HHMMSS])\n\n"
    "Run Mina's Typewriter to transcribe voice files."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(HELP_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    transcripts_dir: Path = context.bot_data["transcripts_dir"]
    user = update.effective_user
    user_id = user.id if user else None
    message = update.effective_message
    text = message.text if message else None

    if user_id is None or not text or not text.strip():
        return

    try:
        dest = append_text_note(transcripts_dir, user_id, text)
        logger.info("Saved text note from user %s to %s", user_id, dest)
        await update.effective_message.reply_text(f"Saved to {dest.name}")
    except Exception:
        logger.exception("Failed to save text note from user %s", user_id)
        await update.effective_message.reply_text(
            "Could not save that text message. Please try again."
        )


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    save_dir: Path = context.bot_data["save_dir"]
    user = update.effective_user
    user_id = user.id if user else "unknown"

    try:
        dest = await save_voice_message(update, context, save_dir)
        logger.info("Saved voice from user %s to %s", user_id, dest)
        await update.effective_message.reply_text(f"Saved as {dest.name}")
    except Exception:
        logger.exception("Failed to save voice from user %s", user_id)
        await update.effective_message.reply_text(
            "Could not save that voice message. Please try again."
        )


def main() -> None:
    try:
        token = load_bot_token()
        save_dir = load_save_dir()
        transcripts_dir = load_transcripts_dir(save_dir)
    except ConfigurationError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    application = (
        Application.builder()
        .token(token)
        .build()
    )
    application.bot_data["save_dir"] = save_dir
    application.bot_data["transcripts_dir"] = transcripts_dir

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VOICE, on_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    logger.info(
        "Bot started. Voice → %s, typed notes → %s",
        save_dir,
        transcripts_dir,
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
