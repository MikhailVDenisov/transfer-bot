"""
Фикстуры для работы с базой данных
"""

import os
import sqlite3
import tempfile

import pytest

from database.connection import DatabaseConnection
from database.init_db import init_database


@pytest.fixture
def temp_db():
    """Создает временную базу данных для тестов"""
    # Создаем временный файл базы данных
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    # Сохраняем оригинальный путь к БД
    original_db_path = os.getenv("DB_PATH")

    # Устанавливаем временный путь
    os.environ["DB_PATH"] = temp_file.name

    try:
        # Инициализируем базу данных
        init_database()
        yield temp_file.name
    finally:
        # Восстанавливаем оригинальный путь
        if original_db_path:
            os.environ["DB_PATH"] = original_db_path
        else:
            os.environ.pop("DB_PATH", None)

        # Удаляем временный файл
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@pytest.fixture
def db_connection(temp_db):
    """Создает подключение к тестовой базе данных"""
    return DatabaseConnection()


@pytest.fixture
def sample_passenger():
    """Создает тестового пассажира"""
    from tests.factories import PassengerFactory

    return PassengerFactory.build(
        id=1,
        telegram_username="test_user",
        chat_id="123456789",
        fio="Иванов Иван Иванович",
        role="user",
    )


@pytest.fixture
def sample_admin():
    """Создает тестового администратора"""
    from tests.factories import PassengerFactory

    return PassengerFactory.build(
        id=2,
        telegram_username="admin_user",
        chat_id="987654321",
        fio="Петров Петр Петрович",
        role="admin",
    )


@pytest.fixture
def sample_bus():
    """Создает тестовый автобус"""
    from tests.factories import BusFactory

    return BusFactory.build(
        id=1,
        number="БУС-001",
        departure_place="Москва",
        destination="Переславль-Залесский",
        departure_date="2024-01-15",
        departure_time="10:00",
        capacity=30,
        direction="Туда",
        is_active=True,
    )


@pytest.fixture
def sample_reservation(sample_passenger, sample_bus):
    """Создает тестовое бронирование"""
    from tests.factories import ReservationFactory

    return ReservationFactory.build(
        id=1,
        passenger_id=sample_passenger.id,
        bus_id=sample_bus.id,
        direction=sample_bus.direction,
    )


@pytest.fixture
def sample_waiting_record(sample_passenger, sample_bus):
    """Создает тестовую запись листа ожидания"""
    from tests.factories import WaitingListRecordFactory

    return WaitingListRecordFactory.build(
        id=1,
        passenger_id=sample_passenger.id,
        bus_id=sample_bus.id,
        status="Waiting",
        notification_sent="No",
    )
