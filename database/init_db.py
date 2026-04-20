"""
Инициализация базы данных
"""

import logging

from config.settings import DB_PATH
from database.connection import db_connection

logger = logging.getLogger(__name__)


def ensure_column_exists(table_name: str, column_name: str, column_definition: str):
    """Добавляет колонку в таблицу, если она отсутствует"""
    columns = db_connection.execute_query(
        f"PRAGMA table_info({table_name})", fetch_all=True
    )
    existing_columns = {column[1] for column in columns}

    if column_name not in existing_columns:
        db_connection.execute_query(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def init_database():
    """Инициализирует базу данных и создает таблицы"""
    try:
        # Создание таблицы Passengers
        db_connection.execute_query("""
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

        ensure_column_exists("Passengers", "PassportNumber", "TEXT")
        ensure_column_exists("Passengers", "Citizenship", "TEXT")
        ensure_column_exists("Passengers", "LastName", "TEXT")
        ensure_column_exists("Passengers", "FirstName", "TEXT")
        ensure_column_exists("Passengers", "Patronymic", "TEXT")
        ensure_column_exists("Passengers", "BirthDate", "TEXT")
        ensure_column_exists(
            "Passengers", "PersonalDataConfirmed", "BOOLEAN DEFAULT FALSE"
        )

        # Создание таблицы Buses
        db_connection.execute_query("""
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
        db_connection.execute_query("""
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
        db_connection.execute_query("""
        CREATE TABLE IF NOT EXISTS WaitingList (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            PassengerID INTEGER,
            BusID INTEGER,
            RequestTime TEXT,
            Status TEXT DEFAULT 'Waiting',
            NotificationSent TEXT DEFAULT 'No',
            FOREIGN KEY (PassengerID) REFERENCES Passengers (ID),
            FOREIGN KEY (BusID) REFERENCES Buses (ID)
        )
        """)

        # Создание таблицы BusOwners
        db_connection.execute_query("""
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
            db_connection.execute_query(stmt)

        logger.info("База данных успешно инициализирована")

    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        raise
