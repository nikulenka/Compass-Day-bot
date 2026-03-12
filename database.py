import pg8000.native
import os
import logging

def get_db_connection():
    try:
        raw_host = os.getenv("DB_HOST", "compass-day-vitalyn.db-msk0.amvera.tech")
        clean_host = raw_host.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
        port = int(os.getenv("DB_PORT", "5432"))
        user = os.getenv("DB_USER", "compass-admin")
        password = os.getenv("DB_PASSWORD", "Land40Us")
        dbname = os.getenv("DB_NAME", "Compass-Day-DB")
        
        logging.info(f"Connecting to: {clean_host} via pg8000")
        
        # pg8000.native handles SSL negotiation elegantly
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
        # pg8000 returns list of lists.
        # Current DB columns: tg_id, name, birth_date, occupation
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

def log_daily_mailing(tg_id, content):
    conn = get_db_connection()
    if not conn:
        return
    try:
        # pg8000.native uses colon for parameters
        conn.run(
            "INSERT INTO daily_logs (tg_id, content, sent_at) VALUES (:tg_id, :content, NOW())",
            tg_id=tg_id, content=content
        )
    except Exception as e:
        logging.error(f"Error logging mailing: {e}")
    finally:
        conn.close()

def fetch_user_history(tg_id, days=3):
    conn = get_db_connection()
    if not conn:
        return ""
    try:
        # Note: INTERVAL parameterization can be tricky, using simple concatenation for the constant part
        rows = conn.run(
            "SELECT content FROM daily_logs WHERE tg_id = :tg_id AND sent_at > NOW() - INTERVAL '3 days' ORDER BY sent_at DESC",
            tg_id=tg_id
        )
        history = "\n---\n".join([r[0] for r in rows])
        return history
    except Exception as e:
        logging.error(f"Error fetching user history: {e}")
        return ""
    finally:
        conn.close()
