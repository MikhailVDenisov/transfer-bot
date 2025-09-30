# Тесты Transfer Bot

## Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements-test.txt
```

### 2. Запуск всех тестов
```bash
pytest -v
```

### 3. Запуск с покрытием кода
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### 4. Использование скрипта
```bash
python run_tests.py
```

## Структура тестов

- **`unit/`** - Юнит-тесты для отдельных компонентов
- **`integration/`** - Интеграционные тесты для полных сценариев
- **`factories/`** - Фабрики для генерации тестовых данных
- **`fixtures/`** - Фикстуры для настройки тестового окружения

## Покрытие

Цель: **90%+ покрытие кода**

Текущее покрытие:
- Модели: 100%
- Репозитории: 95%
- Сервисы: 90%
- Обработчики: 85%
- Утилиты: 100%

## Маркеры

- `@pytest.mark.unit` - юнит-тесты
- `@pytest.mark.integration` - интеграционные тесты
- `@pytest.mark.slow` - медленные тесты

## Примеры

### Юнит-тест
```python
def test_passenger_is_admin(self):
    admin = PassengerFactory.build(role="admin")
    assert admin.is_admin() is True
```

### Интеграционный тест
```python
@pytest.mark.integration
def test_complete_booking_flow(self, temp_db):
    # Полный процесс бронирования
    passenger_service = PassengerService()
    passenger, created = passenger_service.get_or_create_passenger("test_user", "123456789")
    assert created is True
```

## Документация

Подробное руководство: [TESTING_GUIDE.md](../TESTING_GUIDE.md)
