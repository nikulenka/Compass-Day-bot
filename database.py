# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "compass-day-vitalyn.db-msk0.amvera.tech"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "compass-admin"),
            password=os.getenv("DB_PASSWORD", "Land40Us"),
            database=os.getenv("DB_NAME", "compass-admin")
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
