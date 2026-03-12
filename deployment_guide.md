# Инструкция по деплою и подготовке к GitHub

### 1. Структура проекта
Теперь проект организован правильно для Firebase:
* `functions/` — папка с кодом функции Python.
* `firebase.json` — конфигурация Firebase.
* `.gitignore` — исключает секреты из GitHub.

### 2. Подготовка Firebase
1. Установите Firebase CLI: `npm install -g firebase-tools`.
2. Авторизуйтесь: `firebase login`.
3. Инициализируйте проект (уже сделано частично, но для связи с вашим Firebase ID): 
   `firebase use --add [имя-вашего-проекта]`

### 3. Настройка переменных окружения (Секреты)
**ВАЖНО:** Никогда не загружайте ключи в GitHub! 
Я создал файл `functions/.env` локально. Он добавлен в `.gitignore` и не попадет в репозиторий.

Для деплоя в Firebase используйте один из способов:
* **Способ А (.env):** Firebase автоматически подхватит `.env` файл при деплое, если он находится в папке `functions/`.
* **Способ Б (Google Cloud Secret Manager):** Рекомендуется для продакшена.

### 4. Деплой
Запустите команду из корня проекта:
```bash
firebase deploy --only functions
```

### 5. Загрузка на GitHub
1. Создайте новый репозиторий на GitHub.
2. Выполните команды в терминале:
```bash
git init
git add .
git commit -m "Initial commit: Compass-Day Daily Loop"
git branch -M main
git remote add origin https://github.com/ВАШ_ЛОГИН/ВАШ_РЕПО.git
git push -u origin main
```

### 6. Настройка Cloud Scheduler
Функция настроена на запуск в 21:15 UTC ежедневно.
 Проверить статус можно в Firebase Console -> Functions -> Scheduling.
