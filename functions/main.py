# main.py
from firebase_functions import https_fn, options, scheduler_fn
from database import fetch_active_users, log_daily_mailing
from ai_service import generate_daily_content
from telegram_service import send_telegram_message
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

async def run_daily_loop():
    """Core logic to process all users."""
    users = fetch_active_users()
    logging.info(f"Fetched {len(users)} active users.")

    for user in users:
        tg_id = user['tg_id']
        logging.info(f"Processing user {tg_id} ({user['name']})")
        
        try:
            # Generate content using Prompt Chaining
            content = await generate_daily_content(user)
            
            if content:
                # Send to Telegram
                success = await send_telegram_message(tg_id, content)
                
                if success:
                    # Log to DB
                    log_daily_mailing(tg_id, content)
                    logging.info(f"Successfully sent and logged daily loop for user {tg_id}")
                else:
                    logging.error(f"Failed to send message to user {tg_id}")
            else:
                logging.error(f"Failed to generate content for user {tg_id}")
                
        except Exception as e:
            logging.error(f"Error in daily loop for user {tg_id}: {e}")

@https_fn.on_request()
def daily_loop_http(req: https_fn.Request) -> https_fn.Response:
    """HTTP Trigger for manual testing or debugging."""
    asyncio.run(run_daily_loop())
    return https_fn.Response("Daily loop executed.")

@scheduler_fn.on_schedule(schedule="15 20 * * *", time_zone="UTC")
def daily_loop_scheduled(event: scheduler_fn.ScheduledEvent) -> None:
    """
    Scheduled trigger (runs at 20:15 UTC, which is 21:15 in Serbia winter time).
    Note: Ideally, this should handle user-specific timezones, 
    but for the initial migration, we set a global time or 
    trigger a logic that checks user timezones in the DB.
    """
    asyncio.run(run_daily_loop())
