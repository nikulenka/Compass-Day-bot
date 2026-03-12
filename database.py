import pg8000.native
import os
import logging
from datetime import datetime

def get_db_connection():
    try:
        raw_host = os.getenv("DB_HOST", "compass-day-vitalyn.db-msk0.amvera.tech")
        clean_host = raw_host.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
        port = int(os.getenv("DB_PORT", "5432"))
        user = os.getenv("DB_USER", "compass-admin")
        password = os.getenv("DB_PASSWORD", "Land40Us")
        dbname = os.getenv("DB_NAME", "Compass-Day-DB")
        
        logging.info(f"Connecting to: {clean_host} via pg8000")
        
        conn = pg8000.native.Connection(
            user=user,
            password=password,
            host=clean_host,
            port=port,
            database=dbname,
            timeout=20
        )
        return conn
    except Exception as e:
        logging.error(f"Error connecting to database: {e}")
        return None

def fetch_active_users():
    conn = get_db_connection()
    if not conn:
        return []
    try:
        # Schema matches: tg_id, name, birth_date, occupation, onboarding_step
        rows = conn.run("""
            SELECT tg_id, name, birth_date, occupation 
            FROM users 
            WHERE onboarding_step = 'completed'
        """)
        users = []
        for r in rows:
            users.append({
                'tg_id': r[0],
                'name': r[1],
                'birth_date': r[2],
                'occupation': r[3]
            })
        return users
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        return []
    finally:
        conn.close()

def log_daily_mailing(tg_id, psych, stylist, nutr, color_hex=None):
    """Logs the structured expert recommendations to the DB."""
    conn = get_db_connection()
    if not conn:
        return
    try:
        # Schema: user_id, psychologist_output, stylist_output, nutritionist_output, color_hex, created_at
        conn.run("""
            INSERT INTO daily_logs 
            (user_id, psychologist_output, stylist_output, nutritionist_output, color_hex, created_at, log_date) 
            VALUES (:uid, :p_out, :s_out, :n_out, :color, NOW(), CURRENT_DATE)
        """, 
        uid=tg_id, 
        p_out=psych, 
        s_out=stylist, 
        n_out=nutr, 
        color=color_hex)
    except Exception as e:
        logging.error(f"Error logging mailing: {e}")
    finally:
        conn.close()

def fetch_user_history(tg_id, days=3):
    """Fetches and combines history for AI context."""
    conn = get_db_connection()
    if not conn:
        return ""
    try:
        # Schema columns: psychologist_output, stylist_output, nutritionist_output
        rows = conn.run("""
            SELECT psychologist_output, stylist_output, nutritionist_output 
            FROM daily_logs 
            WHERE user_id = :uid AND created_at > NOW() - INTERVAL '3 days'
            ORDER BY created_at DESC
        """, uid=tg_id)
        
        history_parts = []
        for r in rows:
            combined = f"Психолог: {r[0]}\nСтилист: {r[1]}\nНутрициолог: {r[2]}"
            history_parts.append(combined)
            
        return "\n---\n".join(history_parts)
    except Exception as e:
        logging.error(f"Error fetching user history: {e}")
        return ""
    finally:
        conn.close()
