# streamlit_app.py
import streamlit as st
import asyncio
import logging
import os
import json
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database import fetch_active_users, log_daily_mailing, get_db_connection, fetch_recent_logs
from ai_service import generate_daily_content
from telegram_service import send_telegram_message, get_bot_status
import datetime

st.set_page_config(page_title="Compass-Day Control Panel", page_icon="🧭", layout="wide")

# --- Constants & Config ---
CONFIG_FILE = "config_ui.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "provider": os.getenv("AI_PROVIDER", "Gemini"),
        "model": os.getenv("AI_MODEL_NAME", "gemini-2.0-flash")
    }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

# Initialize Session State
if 'config' not in st.session_state:
    st.session_state.config = load_config()

# --- Custom Styling ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #4A90E2; color: white; }
    .status-ok { color: #28a745; font-weight: bold; }
    .status-err { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar Management ---
st.sidebar.title("🧭 Compass-Day")
page = st.sidebar.radio("Навигация", ["📊 Дашборд", "📜 История рассылок", "⚙️ Настройки AI"])

# --- Logging setup for Streamlit (Global) ---
if 'logs' not in st.session_state:
    st.session_state.logs = []

class StreamlitLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        st.session_state.logs.append(msg)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
for h in logger.handlers[:]: logger.removeHandler(h)
logger.addHandler(StreamlitLogHandler())

# ==========================================
# PAGE: SETTINGS
# ==========================================
if page == "⚙️ Настройки AI":
    st.title("⚙️ Настройки AI")
    st.write("Эти настройки сохраняются локально и используются для рассылки.")
    
    col1, col2 = st.columns(2)
    with col1:
        new_provider = st.selectbox(
            "Провайдер", ["Gemini", "OpenRouter"], 
            index=0 if st.session_state.config['provider'] == "Gemini" else 1
        )
        new_model = st.text_input("Название модели", value=st.session_state.config['model'])
    
    with col2:
        st.info("💡 OpenRouter позволяет использовать Claude 3, GPT-4 и другие модели.")
        st.warning("⚠️ Убедитесь, что соответствующие ключи (GEMINI_API_KEY / OPENROUTER_API_KEY) прописаны в .env или в Secrets GitHub.")

    if st.button("💾 Сохранить конфигурацию"):
        st.session_state.config['provider'] = new_provider
        st.session_state.config['model'] = new_model
        save_config(st.session_state.config)
        st.success("Конфигурация сохранена!")

# ==========================================
# PAGE: HISTORY
# ==========================================
elif page == "📜 История рассылок":
    st.title("📜 История последних рассылок")
    logs_data = fetch_recent_logs(50)
    
    if logs_data:
        df = pd.DataFrame(logs_data)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("Детали последнего сообщения")
        last = logs_data[0]
        st.write(f"**Пользователь:** {last['name']} | **Дата:** {last['date']}")
        
        c1, c2, c3 = st.columns(3)
        with c1: st.info(f"🧠 **Психолог:**\n\n{last['psych']}")
        with c2: st.success(f"👗 **Стилист:**\n\n{last['stylist']}")
        with c3: st.warning(f"🍏 **Нутрициолог:**\n\n{last['nutr']}")
    else:
        st.info("История пока пуста.")

# ==========================================
# PAGE: DASHBOARD
# ==========================================
else:
    st.title("📊 Панель управления")
    
    # 1. System Health
    st.subheader("📡 Статус систем")
    c1, c2, c3 = st.columns(3)
    
    # DB Status
    try:
        conn = get_db_connection()
        if conn:
            c1.metric("База данных", "Online", delta="OK")
            conn.close()
        else: c1.metric("База данных", "Offline", delta_color="inverse")
    except: c1.metric("База данных", "Error")

    # TG Status
    try:
        tg_ok, tg_name = asyncio.run(get_bot_status())
        if tg_ok: c2.metric("Telegram Бот", "Online", delta=tg_name)
        else: c2.metric("Telegram Бот", "Offline")
    except: c2.metric("Telegram Бот", "Error")

    # AI Status
    ai_p = st.session_state.config['provider']
    api_key = os.getenv("GEMINI_API_KEY") if ai_p == "Gemini" else os.getenv("OPENROUTER_API_KEY")
    if api_key: c3.metric(f"AI ({ai_p})", "Ready", delta=st.session_state.config['model'])
    else: c3.metric(f"AI ({ai_p})", "Missing Key", delta_color="inverse")

    st.divider()

    # 2. Main Action
    col_exec, col_logs = st.columns([1, 2])
    
    with col_exec:
        st.subheader("🚀 Ручной запуск")
        st.write(f"Будет использован провайдер **{ai_p}**.")
        
        async def run_mailing_task():
            users = fetch_active_users()
            st.write(f"Пользователей в базе: {len(users)}")
            pb = st.progress(0)
            
            for i, user in enumerate(users):
                st.write(f"Обработка {user['name']}...")
                res = await generate_daily_content(
                    user, provider=ai_p, api_key=api_key, model_name=st.session_state.config['model']
                )
                if res and res.get('html'):
                    ok = await send_telegram_message(user['tg_id'], res['html'])
                    if ok:
                        log_daily_mailing(user['tg_id'], res['psych'], res['stylist'], res['nutr'], res['color'])
                        st.success(f"✅ Готово: {user['name']}")
                    else: st.error(f"❌ Ошибка Telegram: {user['name']}")
                else: st.error(f"❌ Ошибка AI: {user['name']}")
                pb.progress((i+1)/len(users))
            st.balloons()
            st.success("Всё отправлено!")

        if st.button("🔥 ЗАПУСТИТЬ РАССЫЛКУ СЕЙЧАС"):
            if not api_key: st.error("Нет ключа API!")
            else: asyncio.run(run_mailing_task())

    with col_logs:
        st.subheader("📋 Системный лог (текущий)")
        log_text = "\n".join(st.session_state.get('logs', [])[-15:])
        st.code(log_text if log_text else "Логи отсутствуют...")
