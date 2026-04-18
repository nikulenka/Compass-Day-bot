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
    try:
        logger.info("--- Starting Daily Automated Mailing Check ---")
        
        # 1. Check Schedule from DB
        mailing_time_str = get_setting("mailing_time", "19:15")
        last_run_date = get_setting("last_run_date", "")
        
        try:
            belgrade_tz = ZoneInfo("Europe/Belgrade")
            now = datetime.now(belgrade_tz)
        except Exception as tz_err:
            logger.warning(f"Could not load Europe/Belgrade timezone: {tz_err}. Falling back to UTC.")
            now = datetime.now() # Fallback to system/UTC
            
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
        total_users = len(users)
        logger.info(f"Initiating mailing for {total_users} active users.")

        if total_users == 0:
            logger.info("No active users found. Marking as run for today to avoid repeated checks.")
            set_setting("last_run_date", today_str)
            return

        successful_sends = 0
        failed_sends = 0

        for user in users:
            tg_id = user['tg_id']
            logger.info(f"Processing user: {user['name']} (TG: {tg_id})")
            
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
                        logger.info(f"SUCCESS: Sent to {user['name']}")
                    else:
                        failed_sends += 1
                        logger.error(f"FAILURE: Telegram send failed for {user['name']}")
                else:
                    failed_sends += 1
                    logger.error(f"FAILURE: AI generation failed or returned empty for {user['name']}")
                    
            except Exception as e:
                failed_sends += 1
                logger.error(f"CRITICAL ERROR processing {user['name']}: {e}", exc_info=True)
                
        # 3. Update Last Run - Only if we didn't have a total system failure
        # If we have many users and ALL failed, something is systemically wrong.
        if successful_sends > 0:
            set_setting("last_run_date", today_str)
            logger.info(f"--- Daily Mailing Finished. {successful_sends}/{total_users} successful. ---")
        else:
            if total_users > 0:
                logger.error(f"--- Daily Mailing FAILED COMPLETELY. 0/{total_users} successful. ---")
                # We do NOT update last_run_date here so it can retry later,
                # but we exit with 1 to alert the admin via GitHub Actions.
                exit(1)
            else:
                logger.info("--- Daily Mailing Finished (No users to process). ---")

    except Exception as global_err:
        logger.critical(f"Global crash in run_cron_mailing: {global_err}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    asyncio.run(run_cron_mailing())
