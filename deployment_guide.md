# Инструкция по деплою на Streamlit.io

### 1. Подготовка и GitHub
Проект уже настроен для работы со Streamlit. Убедитесь, что все последние изменения отправлены в GitHub:
```bash
git add .
git commit -m "Migrate to Streamlit"
git push origin main
```

### 2. Деплой на Streamlit Cloud
1. Зайдите на [share.streamlit.io](https://share.streamlit.io).
2. Авторизуйтесь через GitHub.
3. Нажмите **"New app"**.
4. Выберите ваш репозиторий: `nikulenka/Compass-Day-bot`.
5. Main file path: `streamlit_app.py`.
6. Нажмите **"Deploy!"**.

### 3. Настройка Секретов (Secrets)
В консоли Streamlit после деплоя (или во время):
1. Нажмите **Settings** -> **Secrets**.
2. Вставьте все переменные в формате TOML (скопируйте блок ниже полностью):

```toml
# Вставьте сюда ваши данные из файла .env в формате:
DB_HOST = "..."
DB_PORT = "..."
DB_USER = "..."
DB_PASSWORD = "..."
DB_NAME = "..."
GEMINI_API_KEY = "..."
TELEGRAM_BOT_TOKEN = "..."
```

### 4. Автоматизация (Cron через GitHub Actions)
Чтобы рассылка уходила каждый день в 21:15 автоматически:
1. Зайдите в ваш репозиторий на GitHub.
2. Перейдите в **Settings** -> **Secrets and variables** -> **Actions**.
3. Нажмите **New repository secret** и добавьте следующие ключи (возьмите их из вашего `.env` файла):
   - `DB_HOST`
   - `DB_PORT`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`
   - `GEMINI_API_KEY` (или `OPENROUTER_API_KEY`)
   - `TELEGRAM_BOT_TOKEN`
   - `AI_PROVIDER` (необязательно, по умолчанию `Gemini`)
   - `AI_MODEL_NAME` (необязательно)

Теперь GitHub будет сам запускать файл `cron_daily.py` по расписанию. Состояние запуска можно отслеживать во вкладке **Actions**.

### 5. Ручной запуск
* **Через Streamlit:** Нажмите кнопку **"🚀 Запустить рассылку сейчас"** в интерфейсе приложения.
* **Через GitHub:** Зайдите в **Actions** -> **Daily Automated Mailing** -> **Run workflow**.

---
*Проект настроен для полностью автономной работы.* 🦾🚀🤖
