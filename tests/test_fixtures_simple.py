"""
Простой тест для проверки фикстур
"""

import pytest


def test_temp_db_fixture(temp_db):
    """Тест фикстуры temp_db"""
    assert temp_db is not None
    assert isinstance(temp_db, str)
    assert temp_db == ":memory:"  # Используем in-memory базу данных для тестов
    print(f"✅ temp_db фикстура работает: {temp_db}")


def test_db_connection_fixture(db_connection):
    """Тест фикстуры db_connection"""
    assert db_connection is not None

    # Проверяем, что можем выполнить запрос
    result = db_connection.execute_query(
        "SELECT name FROM sqlite_master WHERE type='table'", fetch_all=True
    )
    tables = [row[0] for row in result]

    expected_tables = [
        "Passengers",
        "Buses",
        "Reservations",
        "WaitingList",
        "BusOwners",
    ]
    for table in expected_tables:
        assert table in tables, f"Таблица {table} не найдена"

    print(f"✅ db_connection фикстура работает, таблицы: {tables}")


def test_sample_passenger_fixture(sample_passenger):
    """Тест фикстуры sample_passenger"""
    assert sample_passenger is not None
    assert sample_passenger.telegram_username == "test_user"
    assert sample_passenger.fio == "Иванов Иван Иванович"
    assert sample_passenger.role == "user"
    print(
        f"✅ sample_passenger фикстура работает: {sample_passenger.telegram_username}"
    )


def test_sample_bus_fixture(sample_bus):
    """Тест фикстуры sample_bus"""
    assert sample_bus is not None
    assert sample_bus.number == "БУС-001"
    assert sample_bus.departure_place == "Москва"
    assert sample_bus.destination == "Переславль-Залесский"
    print(f"✅ sample_bus фикстура работает: {sample_bus.number}")


def test_sample_reservation_fixture(sample_reservation):
    """Тест фикстуры sample_reservation"""
    assert sample_reservation is not None
    assert sample_reservation.passenger_id == 1
    assert sample_reservation.bus_id == 1
    assert sample_reservation.direction == "Туда"
    print(
        f"✅ sample_reservation фикстура работает: пассажир {sample_reservation.passenger_id}, автобус {sample_reservation.bus_id}"
    )


def test_sample_waiting_record_fixture(sample_waiting_record):
    """Тест фикстуры sample_waiting_record"""
    assert sample_waiting_record is not None
    assert sample_waiting_record.passenger_id == 1
    assert sample_waiting_record.bus_id == 1
    assert sample_waiting_record.status == "Waiting"
    print(
        f"✅ sample_waiting_record фикстура работает: пассажир {sample_waiting_record.passenger_id}, автобус {sample_waiting_record.bus_id}"
    )


def test_sample_data_fixture(sample_data):
    """Тест фикстуры sample_data"""
    assert sample_data is not None
    assert "passenger" in sample_data
    assert "admin" in sample_data
    assert "bus" in sample_data
    assert "reservation" in sample_data
    assert "waiting_record" in sample_data

    print(f"✅ sample_data фикстура работает, содержит {len(sample_data)} элементов")


def test_fixtures_integration(temp_db, db_connection, sample_passenger, sample_bus):
    """Интеграционный тест всех фикстур"""
    # Проверяем, что можем вставить данные в базу
    conn = db_connection.get_connection()
    cursor = conn.cursor()

    # Вставляем пассажира
    cursor.execute(
        """
        INSERT INTO Passengers (Telegram_username, ChatID, FIO, Phone, Comment, Role)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            sample_passenger.telegram_username,
            sample_passenger.chat_id,
            sample_passenger.fio,
            sample_passenger.phone,
            sample_passenger.comment,
            sample_passenger.role,
        ),
    )

    # Вставляем автобус
    cursor.execute(
        """
        INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            sample_bus.number,
            sample_bus.departure_place,
            sample_bus.destination,
            sample_bus.departure_date,
            sample_bus.departure_time,
            sample_bus.capacity,
            sample_bus.direction,
            sample_bus.is_active,
        ),
    )

    conn.commit()

    # Проверяем, что данные вставлены
    cursor.execute("SELECT COUNT(*) FROM Passengers")
    passenger_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Buses")
    bus_count = cursor.fetchone()[0]

    conn.close()

    assert passenger_count == 1, f"Ожидался 1 пассажир, получено {passenger_count}"
    assert bus_count == 1, f"Ожидался 1 автобус, получено {bus_count}"

    print(
        f"✅ Интеграционный тест прошел: {passenger_count} пассажиров, {bus_count} автобусов"
    )
