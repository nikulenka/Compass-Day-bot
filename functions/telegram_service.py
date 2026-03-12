# telegram_service.py
from telegram import Bot
from telegram.constants import ParseMode
import os
import logging

async def send_telegram_message(tg_id, html_content):
    """Sends HTML message to user via Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN not found in environment variables.")
        return False
    
    bot = Bot(token=token)
    try:
        await bot.send_message(
            chat_id=tg_id,
            text=html_content,
            parse_mode=ParseMode.HTML
        )
        return True
    except Exception as e:
        logging.error(f"Error sending Telegram message to {tg_id}: {e}")
        return False
