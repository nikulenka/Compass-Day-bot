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

async def get_bot_status():
    """Verify bot token and connection."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return False, "Token missing"
    try:
        from telegram import Bot
        bot = Bot(token=token)
        me = await bot.get_me()
        return True, f"@{me.username}"
    except Exception as e:
        return False, str(e)
