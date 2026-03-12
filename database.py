# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging

def get_db_connection():
    try:
        raw_host = os.getenv("DB_HOST", "compass-day-vitalyn.db-msk0.amvera.tech")
        # Sanitize host: remove http://, https://, and trailing slashes
        clean_host = raw_host.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
        
        logging.info(f"Connecting to host: {clean_host} (Port: {os.getenv('DB_PORT', '5432')}, DB: {os.getenv('DB_NAME', 'Compass-Day-DB')})")
        
        conn = psycopg2.connect(
            host=clean_host,
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "compass-admin"),
            password=os.getenv("DB_PASSWORD", "Land40Us"),
            database=os.getenv("DB_NAME", "Compass-Day-DB"),
            sslmode='disable',
            connect_timeout=20
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
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # onboarding_step == 'completed'
            cur.execute("""
                SELECT tg_id, name, birth_date, occupation 
                FROM users 
                WHERE onboarding_step = 'completed'
            """)
            users = cur.fetchall()
            return users
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        return []
    finally:
        conn.close()

def log_daily_mailing(tg_id, content):
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO daily_logs (tg_id, content, sent_at) 
                VALUES (%s, %s, NOW())
            """, (tg_id, content))
            conn.commit()
    except Exception as e:
        logging.error(f"Error logging mailing: {e}")
    finally:
        conn.close()

def fetch_user_history(tg_id, days=3):
    conn = get_db_connection()
    if not conn:
        return ""
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT content 
                FROM daily_logs 
                WHERE tg_id = %s AND sent_at > NOW() - INTERVAL '3 days'
                ORDER BY sent_at DESC
            """, (tg_id,))
            logs = cur.fetchall()
            # Combine all previous contents into a single history string
            history = "\n---\n".join([log[0] for log in logs])
            return history
    except Exception as e:
        logging.error(f"Error fetching user history: {e}")
        return ""
    finally:
        conn.close()
