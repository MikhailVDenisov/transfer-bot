# Руководство для разработчиков

## 🚀 Быстрый старт

```bash
# Клонируйте репозиторий
git clone https://github.com/your-org/transfer-bot.git
cd transfer-bot

# Создайте виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или .venv\Scripts\activate  # Windows

# Полная настройка среды разработки
make dev-setup
```

## 🛠️ Основные команды

### Разработка
```bash
make dev        # Форматирование + быстрые тесты
make format     # Форматирование кода
make test-fast  # Быстрые тесты без покрытия
make clean      # Очистка временных файлов
```

### Тестирование
```bash
make test           # Все тесты
make test-cov       # Тесты с покрытием
make test-html      # HTML отчет покрытия
make test-unit      # Только unit тесты
make test-integration # Только integration тесты
```

### Проверка качества
```bash
make check-all      # Все проверки
make lint          # Линтинг
make check-format  # Проверка форматирования
make check-types   # Проверка типов
```

### Помощь
```bash
make help          # Все доступные команды
make info          # Информация о проекте
```

## 📋 Процесс разработки

1. **Перед началом работы:**
   ```bash
   make dev-setup
   ```

2. **Во время разработки:**
   ```bash
   make dev  # После изменений
   ```

3. **Перед коммитом:**
   ```bash
   make check-all  # Все проверки
   ```

## 🧪 Тестирование

- **Все тесты должны проходить** перед коммитом
- **Покрытие кода** должно оставаться на уровне 67%+
- **Unit тесты** для бизнес-логики
- **Integration тесты** для полных сценариев

## 📝 Стиль кода

- **Black** для форматирования
- **isort** для сортировки импортов
- **Flake8** для линтинга
- **MyPy** для проверки типов

## 🔄 Workflow

1. Создайте feature branch
2. Внесите изменения
3. Запустите `make dev`
4. Запустите `make check-all`
5. Создайте Pull Request

## 🐛 Отладка

```bash
# Запуск конкретного теста
pytest tests/unit/test_models.py::TestPassenger::test_passenger_creation -v

# Запуск с отладочным выводом
pytest tests/unit/test_models.py -s -vv

# Остановка на первой ошибке
pytest -x
```

## 📊 Покрытие кода

```bash
make test-html
# Откройте htmlcov/index.html в браузере
```

## ❓ Помощь

Если возникли вопросы:

1. `make help` - список всех команд
2. `make info` - информация о проекте  
3. Создайте issue в репозитории
4. Обратитесь к команде разработки
