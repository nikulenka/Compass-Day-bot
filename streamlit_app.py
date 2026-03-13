# streamlit_app.py
import streamlit as st
import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables for local development
load_dotenv()

from database import fetch_active_users, log_daily_mailing, get_db_connection
from ai_service import generate_daily_content
from telegram_service import send_telegram_message, get_bot_status
import datetime

st.set_page_config(page_title="Compass-Day Dashboard", page_icon="🌟")

# --- UI Sidebar for Configuration ---
st.sidebar.title("⚙️ Настройки AI")

ai_provider = st.sidebar.selectbox(
    "Выберите провайдера",
    ["Gemini", "OpenRouter"],
    index=0
)

# Suggested models
default_models = {
    "Gemini": "gemini-2.0-flash",
    "OpenRouter": "google/gemini-2.0-flash-001"
}

ai_model = st.sidebar.text_input(
    "Модель",
    value=os.getenv("AI_MODEL_NAME") or default_models[ai_provider]
)

# Persistent API Key from secrets/env or manual input
default_key = os.getenv("GEMINI_API_KEY") if ai_provider == "Gemini" else os.getenv("OPENROUTER_API_KEY")
ai_key = st.sidebar.text_input(
    f"API Key ({ai_provider})",
    value=default_key or "",
    type="password"
)

st.sidebar.divider()
st.sidebar.write("ℹ️ Настройки применяются для текущей сессии рассылки.")

st.title("🌟 Compass-Day Daily Loop")
st.write("Управление ежедневной рассылкой экспертных прогнозов.")

# --- Logging setup ---
log_container = st.empty()
class StreamlitLogHandler(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.logs = []

    def emit(self, record):
        msg = self.format(record)
        self.logs.append(msg)
        recent_logs = self.logs[-15:]
        self.widget.code("\n".join(recent_logs))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Clear existing handlers to prevent duplicates on rerun
for h in logger.handlers[:]:
    logger.removeHandler(h)
handler = StreamlitLogHandler(log_container)
logger.addHandler(handler)

async def run_daily_loop():
    """Core logic to process all users."""
    if not ai_key:
        st.error(f"❌ Пожалуйста, введите API Key для {ai_provider} в боковой панели!")
        return

    st.info(f"Запуск рассылки через {ai_provider} ({ai_model})...")
    users = fetch_active_users()
    st.write(f"Найдено активных пользователей: {len(users)}")

    progress_bar = st.progress(0)
    
    for i, user in enumerate(users):
        tg_id = user['tg_id']
        st.write(f"🔄 Обработка: {user['name']} ({tg_id})")
        
        try:
            result = await generate_daily_content(
                user, 
                provider=ai_provider, 
                api_key=ai_key, 
                model_name=ai_model
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
                    st.success(f"✅ Отправлено: {user['name']}")
                else:
                    st.error(f"❌ Ошибка отправки: {user['name']}")
            else:
                st.error(f"❌ Ошибка генерации ИИ для {user['name']}")
        except Exception as e:
            st.error(f"⚠️ Ошибка в процессе для {user['name']}: {e}")
            logging.exception(e)
        
        progress_bar.progress((i + 1) / len(users))

    st.balloons()
    st.success("Рассылка полностью завершена!")

# --- UI Controls ---
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Запустить рассылку сейчас"):
        asyncio.run(run_daily_loop())

with col2:
    st.write("**Статус системы:**")
    
    # DB Check
    try:
        db_conn = get_db_connection()
        if db_conn:
            st.success("✅ База данных подключена")
            db_conn.close()
        else:
            st.error("❌ База: Ошибка")
    except Exception as e:
        st.error(f"❌ База: {str(e)}")

    # AI Config Check
    if ai_key:
        st.success(f"✅ {ai_provider} API готов")
    else:
        st.warning(f"⚠️ {ai_provider}: Введите ключ")

    # Telegram Check
    try:
        tg_ok, tg_msg = asyncio.run(get_bot_status())
        if tg_ok:
            st.success(f"✅ Бот: {tg_msg}")
        else:
            st.error(f"❌ Бот: {tg_msg}")
    except:
        st.error("❌ Бот: Ошибка")

st.divider()
st.subheader("📋 Последние логи")
