# cron_daily.py
import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables (for local testing)
load_dotenv()

from database import fetch_active_users, log_daily_mailing, get_setting, set_setting
from ai_service import generate_daily_content
from telegram_service import send_telegram_message
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo # For python < 3.9 if needed, though 3.9 has it natively

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_cron_mailing():
    """Main entry point for the daily automated mailing."""
    logger.info("--- Starting Daily Automated Mailing Check ---")
    
    # 1. Check Schedule from DB
    mailing_time_str = get_setting("mailing_time", "19:15")
    last_run_date = get_setting("last_run_date", "")
    
    belgrade_tz = ZoneInfo("Europe/Belgrade")
    now = datetime.now(belgrade_tz)
    today_str = now.strftime("%Y-%m-%d")
    current_time_str = now.strftime("%H:%M")
    
    logger.info(f"Target Time: {mailing_time_str} | Current Time (Belgrade): {current_time_str} | Last Run: {last_run_date}")

    # Temporal Gate: Only run if it's past the time AND we haven't run today
    if current_time_str < mailing_time_str:
        logger.info("Too early. Skipping execution.")
        return
    
    if last_run_date == today_str:
        logger.info("Already ran today. Skipping execution.")
        return

    # 2. Configuration from DB (with ENV fallbacks)
    provider = get_setting("ai_provider") or os.getenv("AI_PROVIDER", "Gemini")
    model = get_setting("ai_model") or os.getenv("AI_MODEL_NAME", "gemini-2.0-flash")
    api_key = os.getenv("GEMINI_API_KEY") if provider == "Gemini" else os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        logger.error(f"Missing API Key for {provider}. Automation aborted.")
        return

    users = fetch_active_users()
    logger.info(f"Initiating mailing for {len(users)} users.")

    if not users:
        logger.info("No active users found. Marking as run for today.")
        set_setting("last_run_date", today_str)
        return

    successful_sends = 0
    total_users = len(users)

    for user in users:
        tg_id = user['tg_id']
        logger.info(f"Processing: {user['name']} ({tg_id})")
        
        try:
            result = await generate_daily_content(
                user, 
                provider=provider, 
                api_key=api_key, 
                model_name=model
            )
            
            if result and result.get('html'):
                success = await send_telegram_message(tg_id, result['html'], color_hex=result.get('color'))
                if success:
                    log_daily_mailing(
                        tg_id, 
                        result['psych'], 
                        result['stylist'], 
                        result['nutr'], 
                        result['color']
                    )
                    successful_sends += 1
                    logger.info(f"Successfully sent for {user['name']}")
                else:
                    logger.error(f"Failed to send to {user['name']}")
            else:
                logger.error(f"Failed to generate for {user['name']}")
                
        except Exception as e:
            logger.error(f"Error processing {user['name']}: {e}")
            
    # 3. Update Last Run - Only if at least one was successful
    # This prevents marking the day as 'run' if a systemic error (like API leak) occurred.
    if successful_sends > 0:
        set_setting("last_run_date", today_str)
        logger.info(f"--- Daily Mailing Finished. {successful_sends}/{total_users} sent. Last run marked as {today_str} ---")
    else:
        logger.error(f"--- Daily Mailing FAILED. 0/{total_users} sent. Status NOT updated. ---")
        # Exit with error code to notify GitHub Actions
        exit(1)

if __name__ == "__main__":
    asyncio.run(run_cron_mailing())
