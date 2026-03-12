# streamlit_app.py
import streamlit as st
import asyncio
import logging
from database import fetch_active_users, log_daily_mailing, get_db_connection
from ai_service import generate_daily_content
from telegram_service import send_telegram_message
import datetime
import os

st.set_page_config(page_title="Compass-Day Dashboard", page_icon="🌟")

st.title("🌟 Compass-Day Daily Loop")
st.write("Управление ежедневной рассылкой экспертных прогнозов.")

# Logging setup for Streamlit
log_container = st.empty()
class StreamlitLogHandler(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.logs = []

    def emit(self, record):
        msg = self.format(record)
        self.logs.append(msg)
        self.widget.code("\n".join(self.logs[-15:]))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = StreamlitLogHandler(log_container)
logger.addHandler(handler)

async def run_daily_loop():
    """Core logic to process all users."""
    st.info("Запуск процесса рассылки...")
    users = fetch_active_users()
    st.write(f"Найдено активных пользователей: {len(users)}")

    progress_bar = st.progress(0)
    
    for i, user in enumerate(users):
        tg_id = user['tg_id']
        st.write(f"🔄 Обработка: {user['name']} ({tg_id})")
        
        try:
            content = await generate_daily_content(user)
            if content:
                success = await send_telegram_message(tg_id, content)
                if success:
                    log_daily_mailing(tg_id, content)
                    st.success(f"✅ Отправлено: {user['name']}")
                else:
                    st.error(f"❌ Ошибка отправки: {user['name']}")
            else:
                st.error(f"❌ Ошибка генерации контента для {user['name']}")
        except Exception as e:
            st.error(f"⚠️ Ошибка для {user['name']}: {e}")
        
        progress_bar.progress((i + 1) / len(users))

    st.balloons()
    st.success("Рассылка завершена!")

# UI Components
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Запустить рассылку сейчас"):
        asyncio.run(run_daily_loop())

with col2:
    st.write("**Статус системы:**")
    
    # DB Check
    db_conn = get_db_connection()
    if db_conn:
        st.write("✅ База данных подключена")
        db_conn.close()
    else:
        st.write("❌ Ошибка подключения к базе")

    # Gemini Check
    if os.getenv("GEMINI_API_KEY"):
        st.write("✅ Gemini API ключ найден")
    else:
        st.write("❌ Gemini API ключ не настроен")

st.divider()
st.subheader("📋 Последние логи")
# Logs are displayed in the log_container defined above
