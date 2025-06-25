# Transfer Bot for ProductCamp

Телеграм-бот для организации трансферов на мероприятие ProductCamp. Позволяет участникам бронировать места в автобусах, просматривать свои брони и получать информацию о маршрутах.

## Функционал

- 📌 Запись на автобусы по направлениям
- 👀 Просмотр текущих броней пользователя
- ❌ Отмена бронирования
- 📊 Админ-панель с выгрузкой данных (для организаторов)
- 📅 Лист ожидания с уведомлениями о свободных местах
- ℹ️ Информация о маршрутах и способах добраться

## Технологии

- Python 3.10+
- python-telegram-bot 20.x
- Google Sheets API (gspread)
- oauth2client
- python-dotenv

## Установка и настройка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/productcamp-transfer-bot.git
cd productcamp-transfer-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте окружение:
   - Создайте файл `.env` в корне проекта
   - Заполните его по примеру `.env.example`:
```
TELEGRAM_TOKEN=ваш_токен_бота
GOOGLE_OAUTH_TOKEN=id_google_таблицы
GOOGLE_CREDENTIALS_JSON={"type": "service_account", ...}
```

4. Настройте Google Sheets:
   - Создайте таблицу с листами: `Passengers`, `Buses`, `Reservations`, `WaitingList`, `BusOwners`
   - Предоставьте доступ для service account из credentials

## Структура проекта (TOBE)

```
productcamp-transfer-bot/
├── app.py                 # Точка входа
├── bot.py                 # Основной класс бота
├── config.py              # Конфигурация
├── requirements.txt       # Зависимости
├── .env.example           # Шаблон .env файла
├── database/              # Работа с данными
│   ├── gsheets_client.py  # Клиент Google Sheets
│   └── repositories/      # Репозитории для таблиц
├── handlers/              # Обработчики команд
├── services/              # Бизнес-логика
├── models/                # Модели данных
└── utils/                 # Вспомогательные утилиты
```

## Запуск

1. В режиме разработки:
```bash
python app.py
```

2. В production (с использованием systemd или supervisor):
```ini
[program:transfer_bot]
command=python /path/to/app.py
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
environment=PYTHONPATH="/path/to/project"
```

## Администрирование

Для назначения прав администратора:
1. Добавьте пользователя в лист `Passengers`
2. В столбце `Role` укажите `admin`

Администраторы получают доступ к:
- Кнопке "Выгрузить данные" в главном меню
- Полному Excel-отчету по бронированиям

## Особенности реализации

1. **Лист ожидания**:
   - Автоматическая проверка каждые 10 минут
   - Уведомления при освобождении мест
   - Очередь по времени подачи заявки

2. **Интеграция с Google Sheets**:
   - Все данные хранятся в облачной таблице
   - Реализованы репозитории для каждой сущности
   - Авторизация через Service Account

3. **Логика бронирования**:
   - Проверка доступности мест
   - Защита от дублирования броней
   - Поддержка разных направлений

## Разработка

Для добавления новой функциональности:

1. Создайте обработчик в `handlers/`
2. Реализуйте бизнес-логику в `services/`
3. Добавьте необходимые методы в репозитории
4. Зарегистрируйте обработчик в `bot.py`

Пример добавления команды:
```python
# handlers/new_feature.py
from telegram import Update
from telegram.ext import ContextTypes

async def handle_new_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("New feature works!")

# bot.py
from handlers.new_feature import handle_new_feature

def setup_handlers(application):
    application.add_handler(CommandHandler("new", handle_new_feature))
```

## Лицензия

MIT License
