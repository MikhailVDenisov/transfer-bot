# Transfer Bot 🚌

Telegram бот для управления трансферами на корпоративные мероприятия

## 📋 Описание

Transfer Bot - это современный Telegram бот, разработанный для автоматизации процесса бронирования трансферов на корпоративные мероприятия. Бот позволяет сотрудникам легко бронировать места в автобусах, управлять своими бронированиями и получать уведомления о доступных местах.

## ✨ Основные возможности

- 🎫 **Бронирование мест** - Простое бронирование места в автобусе
- 📋 **Управление бронированиями** - Просмотр и отмена существующих бронирований  
- ⏳ **Лист ожидания** - Автоматическое уведомление при освобождении мест
- 📊 **Экспорт данных** - Экспорт списков пассажиров в Excel (для администраторов)
- 🔍 **Фильтрация по направлениям** - Поиск автобусов по нужному направлению
- 👥 **Управление пользователями** - Система ролей (пользователь/администратор)

## 🛠️ Makefile

Проект включает удобный Makefile с командами для разработки:

```bash
make help        # Показать все доступные команды
make dev-setup   # Полная настройка среды разработки
make test        # Запустить тесты
make db-backup   # Создать резервную копию базы данных
make test-fast   # Быстрые тесты без покрытия
make format      # Отформатировать код
make clean       # Очистить временные файлы
```

## 🏗️ Архитектура

Проект построен с использованием современных принципов разработки:

- **Модульная архитектура** - Разделение на слои (handlers, services, repositories)
- **Dependency Injection** - Слабая связанность компонентов
- **Repository Pattern** - Абстракция работы с данными
- **Service Layer** - Бизнес-логика отделена от обработчиков
- **Factory Pattern** - Для создания тестовых данных

## 📁 Структура проекта

```
transfer-bot/
├── app.py                 # Главный файл приложения
├── config/                # Конфигурация
│   └── settings.py
├── database/              # Слой данных
│   ├── connection.py      # Подключение к БД
│   ├── init_db.py         # Инициализация БД
│   └── repositories.py    # Репозитории
├── handlers/              # Обработчики Telegram
│   ├── base_handler.py
│   ├── booking_handler.py
│   ├── callback_handler.py
│   └── ...
├── models/                # Модели данных
│   └── entities.py
├── services/              # Бизнес-логика
│   ├── booking_service.py
│   ├── bus_service.py
│   └── ...
├── utils/                 # Утилиты
│   ├── keyboards.py
│   ├── messages.py
│   └── validators.py
├── tests/                 # Тесты
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── pyproject.toml         # Конфигурация проекта
```

## 🚀 Установка и запуск

### Требования

- Python 3.9+
- SQLite3
- Telegram Bot Token

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-org/transfer-bot.git
cd transfer-bot
```

2. Создайте виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate     # Windows
```

3. Установите зависимости:
```bash
# Через Makefile (рекомендуется)
make install

# Или прямая команда
pip install -e .
```

4. Создайте файл `.env` с настройками:
```env
TELEGRAM_TOKEN=your_bot_token_here
ADMIN_USERNAMES=admin1,admin2
DB_PATH=transfer_bot.db
WAITING_LIST_CHECK_INTERVAL=300
```

5. Инициализируйте базу данных:
```bash
# Через Makefile (рекомендуется)
make db-init

# Или прямая команда
python -c "from database.init_db import init_database; init_database()"
```

6. При необходимости создайте резервную копию базы данных:
```bash
# Через Makefile
make db-backup

# Или прямой запуск shell-скрипта
./scripts/backup_transfer_bot_db.sh

# С кастомными параметрами
DB_PATH=transfer_bot.db BACKUP_DIR=backups/sqlite KEEP_DAYS=7 ./scripts/backup_transfer_bot_db.sh
```

7. Запустите бота:
```bash
# Через Makefile (рекомендуется)
make run

# Или прямая команда
python app.py
```

### Быстрая настройка для разработки

```bash
# Полная настройка среды разработки одной командой
make dev-setup
```

## 🧪 Тестирование

Проект имеет comprehensive test suite с покрытием 67%.

### Makefile команды (рекомендуется)

```bash
# Все тесты
make test

# Быстрые тесты (без покрытия)
make test-fast

# Только unit тесты
make test-unit

# Только integration тесты  
make test-integration

# С покрытием кода
make test-cov

# С HTML отчетом
make test-html
```

### Прямые pytest команды

```bash
# Все тесты
pytest

# Только unit тесты
pytest -m unit

# Только integration тесты  
pytest -m integration

# С покрытием кода
pytest --cov

# С HTML отчетом
pytest --cov --cov-report=html
```

### Установка тестовых зависимостей

```bash
# Через Makefile (рекомендуется)
make install-test

# Прямая команда
pip install -e ".[test]"
```

## 🛠️ Разработка

### Makefile команды для разработки

```bash
# Полная настройка среды разработки
make dev-setup

# Установка dev зависимостей
make install-dev

# Форматирование кода
make format

# Проверка форматирования
make check-format

# Проверка импортов
make check-imports

# Линтинг
make lint

# Проверка типов
make check-types

# Все проверки сразу
make check-all

# Быстрая проверка для разработки
make dev

# Очистка временных файлов
make clean

# Полная очистка
make clean-all

# Информация о проекте
make info

# Помощь по командам
make help
```

### Прямые команды

```bash
# Установка dev зависимостей
pip install -e ".[dev]"

# Форматирование кода
black .
isort .

# Статический анализ
flake8 .
mypy .
```

## 📊 Покрытие кода

Текущее покрытие тестами: **67%**

- **Repositories**: 100% ✅
- **Models**: 100% ✅  
- **Utils**: 95%+ ✅
- **Services**: 35-93% 🔄
- **Handlers**: 41-95% 🔄

## 🤝 Участие в разработке

1. Форкните проект
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Сделайте commit (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🐛 Сообщения об ошибках

Если вы нашли ошибку, пожалуйста, создайте [issue](https://github.com/your-org/transfer-bot/issues) с подробным описанием.

## 📞 Поддержка

Если у вас есть вопросы, свяжитесь с нами:

- Email: bazinga.mail@yandex.ru
- Telegram: @maximovd

---

Made with ❤️ by Transfer Bot Team
