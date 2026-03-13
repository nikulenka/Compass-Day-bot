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
    
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_time_str = now.strftime("%H:%M")
    
    logger.info(f"Target Time: {mailing_time_str} | Current Time: {current_time_str} | Last Run: {last_run_date}")

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
                success = await send_telegram_message(tg_id, result['html'])
                if success:
                    log_daily_mailing(
                        tg_id, 
                        result['psych'], 
                        result['stylist'], 
                        result['nutr'], 
                        result['color']
                    )
                    logger.info(f"Successfully sent for {user['name']}")
                else:
                    logger.error(f"Failed to send to {user['name']}")
            else:
                logger.error(f"Failed to generate for {user['name']}")
                
        except Exception as e:
            logger.error(f"Error processing {user['name']}: {e}")
            
    # 3. Update Last Run
    set_setting("last_run_date", today_str)
    logger.info(f"--- Daily Mailing Finished. Last run marked as {today_str} ---")

if __name__ == "__main__":
    asyncio.run(run_cron_mailing())
