# telegram_service.py
from telegram import Bot
from telegram.constants import ParseMode
import os
import logging

async def send_telegram_message(tg_id, html_content, color_hex=None):
    """Sends HTML message to user via Telegram, optionally with a color square."""
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
        
        if color_hex and isinstance(color_hex, str):
            clean_hex = color_hex.strip(' #')
            if len(clean_hex) in (3, 6):
                photo_url = f"https://singlecolorimage.com/get/{clean_hex}/400x400"
                await bot.send_photo(
                    chat_id=tg_id,
                    photo=photo_url,
                    caption=f"🎨 Цвет дня от стилиста: #{clean_hex}"
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
