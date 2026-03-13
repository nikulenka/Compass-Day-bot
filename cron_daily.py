# cron_daily.py
import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables (for local testing)
load_dotenv()

from database import fetch_active_users, log_daily_mailing
from ai_service import generate_daily_content
from telegram_service import send_telegram_message

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_cron_mailing():
    """Main entry point for the daily automated mailing."""
    logger.info("--- Starting Daily Automated Mailing ---")
    
    # Configuration: Priority 1: ENV (GitHub Secrets), Priority 2: config_ui.json (Streamlit), Priority 3: Defaults
    import json
    ui_cfg = {}
    if os.path.exists("config_ui.json"):
        try:
            with open("config_ui.json", "r") as f: ui_cfg = json.load(f)
        except: pass

    provider = os.getenv("AI_PROVIDER") or ui_cfg.get("provider") or "Gemini"
    model = os.getenv("AI_MODEL_NAME") or ui_cfg.get("model") or "gemini-2.0-flash"
    api_key = os.getenv("GEMINI_API_KEY") if provider == "Gemini" else os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        logger.error(f"Missing API Key for {provider}. Automation aborted.")
        return

    users = fetch_active_users()
    logger.info(f"Found {len(users)} active users.")

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
                    logger.info(f"Successfully sent and logged for {user['name']}")
                else:
                    logger.error(f"Failed to send Telegram message to {user['name']}")
            else:
                logger.error(f"Failed to generate AI content for {user['name']}")
                
        except Exception as e:
            logger.error(f"Error processing {user['name']}: {e}")
            
    logger.info("--- Daily Automated Mailing Finished ---")

if __name__ == "__main__":
    asyncio.run(run_cron_mailing())
