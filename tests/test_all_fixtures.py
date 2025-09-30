"""
Тест для проверки всех фикстур
"""

import pytest


def test_temp_db_fixture(temp_db):
    """Тест фикстуры temp_db"""
    assert temp_db is not None
    assert isinstance(temp_db, str)
    assert temp_db == ":memory:"  # Используем in-memory базу данных для тестов
    print(f"✅ temp_db: {temp_db}")


def test_db_connection_fixture(db_connection):
    """Тест фикстуры db_connection"""
    assert db_connection is not None
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
        assert table in tables
    print(f"✅ db_connection: {len(tables)} таблиц")


def test_mock_telegram_update_fixture(mock_telegram_update):
    """Тест фикстуры mock_telegram_update"""
    assert mock_telegram_update is not None
    assert mock_telegram_update.message is not None
    assert mock_telegram_update.message.chat_id == 123456789
    print(f"✅ mock_telegram_update: chat_id={mock_telegram_update.message.chat_id}")


def test_mock_telegram_context_fixture(mock_telegram_context):
    """Тест фикстуры mock_telegram_context"""
    assert mock_telegram_context is not None
    assert mock_telegram_context.bot is not None
    assert mock_telegram_context.bot.send_message is not None
    print("✅ mock_telegram_context: bot доступен")


def test_mock_context_fixture(mock_context):
    """Тест фикстуры mock_context"""
    assert mock_context is not None
    assert mock_context.bot is not None
    print("✅ mock_context: доступен")


def test_mock_callback_query_fixture(mock_callback_query):
    """Тест фикстуры mock_callback_query"""
    assert mock_callback_query is not None
    assert mock_callback_query.answer is not None
    assert mock_callback_query.edit_message_text is not None
    assert mock_callback_query.data == "test_callback"
    print(f"✅ mock_callback_query: data={mock_callback_query.data}")


def test_mock_update_with_callback_fixture(mock_update_with_callback):
    """Тест фикстуры mock_update_with_callback"""
    assert mock_update_with_callback is not None
    assert mock_update_with_callback.callback_query is not None
    assert mock_update_with_callback.effective_user is not None
    print("✅ mock_update_with_callback: callback_query доступен")


def test_handler_fixture(handler):
    """Тест фикстуры handler"""
    assert handler is not None
    assert hasattr(handler, "handle")
    print(f"✅ handler: {type(handler).__name__}")


def test_booking_handler_fixture(booking_handler):
    """Тест фикстуры booking_handler"""
    assert booking_handler is not None
    assert hasattr(booking_handler, "show_directions")
    print(f"✅ booking_handler: {type(booking_handler).__name__}")


def test_view_booking_handler_fixture(view_booking_handler):
    """Тест фикстуры view_booking_handler"""
    assert view_booking_handler is not None
    assert hasattr(view_booking_handler, "view_bookings")
    print(f"✅ view_booking_handler: {type(view_booking_handler).__name__}")


def test_waiting_list_handler_fixture(waiting_list_handler):
    """Тест фикстуры waiting_list_handler"""
    assert waiting_list_handler is not None
    assert hasattr(waiting_list_handler, "show_waiting_list_menu")
    print(f"✅ waiting_list_handler: {type(waiting_list_handler).__name__}")


def test_info_handler_fixture(info_handler):
    """Тест фикстуры info_handler"""
    assert info_handler is not None
    assert hasattr(info_handler, "show_how_to_get_there")
    print(f"✅ info_handler: {type(info_handler).__name__}")


def test_export_handler_fixture(export_handler):
    """Тест фикстуры export_handler"""
    assert export_handler is not None
    assert hasattr(export_handler, "export_buses")
    print(f"✅ export_handler: {type(export_handler).__name__}")


def test_callback_handler_fixture(callback_handler):
    """Тест фикстуры callback_handler"""
    assert callback_handler is not None
    assert hasattr(callback_handler, "handle_callback")
    print(f"✅ callback_handler: {type(callback_handler).__name__}")


def test_sample_passenger_fixture(sample_passenger):
    """Тест фикстуры sample_passenger"""
    assert sample_passenger is not None
    assert sample_passenger.telegram_username == "test_user"
    assert sample_passenger.fio == "Иванов Иван Иванович"
    print(f"✅ sample_passenger: {sample_passenger.telegram_username}")


def test_sample_bus_fixture(sample_bus):
    """Тест фикстуры sample_bus"""
    assert sample_bus is not None
    assert sample_bus.number == "БУС-001"
    assert sample_bus.departure_place == "Москва"
    print(f"✅ sample_bus: {sample_bus.number}")


def test_sample_data_fixture(sample_data):
    """Тест фикстуры sample_data"""
    assert sample_data is not None
    assert "passenger" in sample_data
    assert "admin" in sample_data
    assert "bus" in sample_data
    print(f"✅ sample_data: {len(sample_data)} элементов")


def test_all_fixtures_integration(
    temp_db,
    db_connection,
    mock_telegram_update,
    mock_context,
    mock_update_with_callback,
    handler,
    sample_passenger,
    sample_bus,
):
    """Интеграционный тест всех фикстур"""
    # Проверяем, что все фикстуры работают вместе
    assert temp_db is not None
    assert db_connection is not None
    assert mock_telegram_update is not None
    assert mock_context is not None
    assert mock_update_with_callback is not None
    assert handler is not None
    assert sample_passenger is not None
    assert sample_bus is not None

    # Проверяем, что можем выполнить базовые операции
    conn = db_connection.get_connection()
    cursor = conn.cursor()

    # Вставляем тестовые данные
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

    assert passenger_count == 1
    assert bus_count == 1

    print(
        f"✅ Интеграционный тест: {passenger_count} пассажиров, {bus_count} автобусов"
    )
