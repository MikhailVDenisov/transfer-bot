"""
Конфигурация pytest
"""

import asyncio
import os
import sqlite3
import sys
import tempfile

import pytest

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всех тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def in_memory_db():
    """Создает in-memory базу данных для тестов"""
    # Создаем in-memory подключение
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Создание таблицы Passengers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Passengers (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Telegram_username TEXT UNIQUE,
        ChatID TEXT,
        FIO TEXT,
        Phone TEXT,
        Comment TEXT,
        Role TEXT DEFAULT 'user',
        PassportNumber TEXT,
        Citizenship TEXT,
        LastName TEXT,
        FirstName TEXT,
        Patronymic TEXT,
        BirthDate TEXT,
        PersonalDataConfirmed BOOLEAN DEFAULT FALSE
    )
    """)

    # Создание таблицы Buses
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Buses (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Number TEXT,
        Departure_Place TEXT,
        Destination TEXT,
        DepartureDate TEXT,
        DepartureTime TEXT,
        Capacity INTEGER,
        Direction TEXT,
        is_active BOOLEAN DEFAULT TRUE
    )
    """)

    # Создание таблицы Reservations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Reservations (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        PassengerID INTEGER,
        BusID INTEGER,
        ReservationDate TEXT,
        Direction TEXT,
        FOREIGN KEY (PassengerID) REFERENCES Passengers (ID),
        FOREIGN KEY (BusID) REFERENCES Buses (ID)
    )
    """)

    # Создание таблицы WaitingList
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS WaitingList (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        PassengerID INTEGER,
        BusID INTEGER,
        RequestTime TEXT,
        Status TEXT DEFAULT 'Waiting',
        NotificationSent TEXT DEFAULT 'No',
        NotificationSentAt TEXT,
        FOREIGN KEY (PassengerID) REFERENCES Passengers (ID),
        FOREIGN KEY (BusID) REFERENCES Buses (ID)
    )
    """)

    # Создание таблицы BusOwners
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS BusOwners (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        BusID INTEGER,
        ChiefID INTEGER,
        FOREIGN KEY (BusID) REFERENCES Buses (ID),
        FOREIGN KEY (ChiefID) REFERENCES Passengers (ID)
    )
    """)
    for stmt in (
        "CREATE INDEX IF NOT EXISTS idx_buses_direction_is_active ON Buses (Direction, is_active)",
        "CREATE INDEX IF NOT EXISTS idx_reservations_busid ON Reservations (BusID)",
        "CREATE INDEX IF NOT EXISTS idx_reservations_passengerid ON Reservations (PassengerID)",
        "CREATE INDEX IF NOT EXISTS idx_waitinglist_status ON WaitingList (Status)",
        "CREATE INDEX IF NOT EXISTS idx_waitinglist_passenger_bus_status ON WaitingList (PassengerID, BusID, Status)",
        "CREATE INDEX IF NOT EXISTS idx_busowners_busid ON BusOwners (BusID)",
        "CREATE INDEX IF NOT EXISTS idx_busowners_chiefid ON BusOwners (ChiefID)",
    ):
        cursor.execute(stmt)

    conn.commit()

    yield conn

    conn.close()


@pytest.fixture
def temp_db():
    """Создает временную in-memory базу данных для каждого теста"""
    return ":memory:"


@pytest.fixture
def db_connection(in_memory_db):
    """Создает подключение к тестовой базе данных"""

    # Создаем подключение к тестовой базе данных для тестов
    class TestDatabaseConnection:
        def __init__(self, connection):
            self.connection = connection
            self.db_path = ":memory:"

        def get_connection(self):
            return self.connection

        def execute_query(self, query, params=(), fetch_one=False, fetch_all=False):
            cursor = self.connection.cursor()
            try:
                cursor.execute(query, params)
                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                self.connection.commit()
                return result
            except Exception as e:
                self.connection.rollback()
                raise e

    return TestDatabaseConnection(in_memory_db)


@pytest.fixture(autouse=True, scope="function")
def setup_test_environment(in_memory_db):
    """Настройка тестового окружения - автоматически применяется ко всем тестам"""
    # Сохраняем оригинальный экземпляр db_connection
    import database.connection
    from database.connection import DatabaseConnection

    original_db_connection = database.connection.db_connection

    # Создаем новый экземпляр с in-memory базой данных
    class TestDatabaseConnection(DatabaseConnection):
        def __init__(self, connection):
            self.connection = connection
            self.db_path = ":memory:"

        def get_connection(self):
            return self.connection

        def execute_query(self, query, params=(), fetch_one=False, fetch_all=False):
            cursor = self.connection.cursor()
            try:
                cursor.execute(query, params)
                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                self.connection.commit()
                return result
            except Exception as e:
                self.connection.rollback()
                raise e

        def execute_many(self, query, params_list):
            cursor = self.connection.cursor()
            try:
                cursor.executemany(query, params_list)
                self.connection.commit()
            except Exception as e:
                self.connection.rollback()
                raise e

    # Заменяем глобальное подключение на in-memory
    test_db_connection = TestDatabaseConnection(in_memory_db)
    database.connection.db_connection = test_db_connection

    # Также заменяем в модулях репозиториев
    import database.repositories

    database.repositories.db_connection = test_db_connection

    yield test_db_connection

    # Восстанавливаем оригинальный экземпляр
    database.connection.db_connection = original_db_connection
    database.repositories.db_connection = original_db_connection


@pytest.fixture
def mock_telegram_update():
    """Создает мок Telegram Update"""
    from unittest.mock import Mock

    from telegram import CallbackQuery, Chat, Message, Update, User

    update = Mock(spec=Update)
    update.message = Mock(spec=Message)
    update.message.chat_id = 123456789
    update.message.from_user = Mock(spec=User)
    update.message.from_user.username = "test_user"
    update.message.from_user.id = 123456789
    update.message.reply_text = Mock()
    update.message.reply_text.return_value = Mock()

    update.callback_query = Mock(spec=CallbackQuery)
    update.callback_query.answer = Mock()
    update.callback_query.edit_message_text = Mock()
    update.callback_query.from_user = update.message.from_user
    update.callback_query.message = update.message

    update.effective_user = update.message.from_user
    update.effective_chat = Mock(spec=Chat)
    update.effective_chat.id = 123456789

    return update


@pytest.fixture
def mock_telegram_context():
    """Создает мок Telegram Context"""
    from unittest.mock import Mock

    context = Mock()
    context.user_data = {}
    context.bot_data = {}
    context.bot = Mock()
    context.bot.send_message = Mock()
    context.bot.send_document = Mock()

    return context


@pytest.fixture
def mock_context(mock_telegram_context):
    """Алиас для mock_telegram_context для совместимости"""
    return mock_telegram_context


@pytest.fixture
def mock_callback_query():
    """Создает мок CallbackQuery"""
    from unittest.mock import Mock

    from telegram import CallbackQuery

    callback_query = Mock(spec=CallbackQuery)
    callback_query.answer = Mock()
    callback_query.edit_message_text = Mock()
    callback_query.from_user = Mock()
    callback_query.from_user.id = 123456789
    callback_query.from_user.username = "test_user"
    callback_query.message = Mock()
    callback_query.message.chat_id = 123456789
    callback_query.data = "test_callback"

    return callback_query


@pytest.fixture
def mock_update_with_callback(mock_callback_query):
    """Создает мок Update с CallbackQuery"""
    from unittest.mock import Mock

    from telegram import Update

    update = Mock(spec=Update)
    update.callback_query = mock_callback_query
    update.effective_user = mock_callback_query.from_user
    update.effective_chat = Mock()
    update.effective_chat.id = 123456789
    update.message = None  # Нет сообщения для callback query

    return update


@pytest.fixture
def handler():
    """Создает экземпляр StartHandler для тестов"""
    from handlers.start_handler import StartHandler

    return StartHandler()


@pytest.fixture
def booking_handler():
    """Создает экземпляр BookingHandler для тестов"""
    from handlers.booking_handler import BookingHandler

    return BookingHandler()


@pytest.fixture
def view_booking_handler():
    """Создает экземпляр ViewBookingHandler для тестов"""
    from handlers.view_booking_handler import ViewBookingHandler

    return ViewBookingHandler()


@pytest.fixture
def waiting_list_handler():
    """Создает экземпляр WaitingListHandler для тестов"""
    from handlers.waiting_list_handler import WaitingListHandler

    return WaitingListHandler()


@pytest.fixture
def info_handler():
    """Создает экземпляр InfoHandler для тестов"""
    from handlers.info_handler import InfoHandler

    return InfoHandler()


@pytest.fixture
def export_handler():
    """Создает экземпляр ExportHandler для тестов"""
    from handlers.export_handler import ExportHandler

    return ExportHandler()


@pytest.fixture
def callback_handler():
    """Создает экземпляр CallbackHandler для тестов"""
    from handlers.callback_handler import CallbackHandler

    return CallbackHandler()


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


@pytest.fixture
def sample_data():
    """Создает образцы тестовых данных"""
    from tests.factories import (
        BusFactory,
        BusOwnerFactory,
        PassengerFactory,
        ReservationFactory,
        WaitingListRecordFactory,
    )

    return {
        "passenger": PassengerFactory.build(
            id=1,
            telegram_username="test_user",
            chat_id="123456789",
            fio="Иванов Иван Иванович",
            role="user",
        ),
        "admin": PassengerFactory.build(
            id=2,
            telegram_username="admin_user",
            chat_id="987654321",
            fio="Петров Петр Петрович",
            role="admin",
        ),
        "bus": BusFactory.build(
            id=1,
            number="БУС-001",
            departure_place="Москва",
            destination="Переславль-Залесский",
            departure_date="2024-01-15",
            departure_time="10:00",
            capacity=30,
            direction="Туда",
            is_active=True,
        ),
        "reservation": ReservationFactory.build(
            id=1, passenger_id=1, bus_id=1, direction="Туда"
        ),
        "waiting_record": WaitingListRecordFactory.build(
            id=1, passenger_id=1, bus_id=1, status="Waiting", notification_sent="No"
        ),
    }


# Маркеры для категоризации тестов
pytest_plugins = []


def pytest_configure(config):
    """Конфигурация pytest"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
