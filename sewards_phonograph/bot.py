"""Telegram bot that archives voice messages to a configured folder."""

from __future__ import annotations
import os
from dotenv import load_dotenv
load_dotenv()
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import ConfigurationError, load_bot_token, load_save_dir
from save_voice import save_voice_message


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Dr. Seward's Phonograph records your voice notes to disk.\n\n"
    "Send a voice message and I will save it as:\n"
    "  YYYYMMDD_HHMMSS_<your_telegram_id>.ogg\n\n"
    "Only voice messages are archived; other message types are ignored."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(HELP_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


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
    except ConfigurationError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    application = (
        Application.builder()
        .token(token)
        .build()
    )
    application.bot_data["save_dir"] = save_dir

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VOICE, on_voice))

    logger.info("Bot started. Saving voice messages to %s", save_dir)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
