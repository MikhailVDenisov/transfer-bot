"""
Интеграционные тесты для полного процесса бронирования
"""

import pytest

from database.repositories import (
    BusRepository,
    PassengerRepository,
    ReservationRepository,
    WaitingListRepository,
)
from services.booking_service import BookingService
from services.bus_service import BusService
from services.passenger_service import PassengerService
from services.waiting_list_service import WaitingListService
from tests.factories import BusFactory, PassengerFactory


@pytest.mark.integration
class TestBookingFlow:
    """Интеграционные тесты для процесса бронирования"""

    def test_complete_booking_flow(self, temp_db):
        """Тест полного процесса бронирования"""
        # Создаем сервисы
        passenger_service = PassengerService()
        bus_service = BusService()
        booking_service = BookingService()

        # 1. Создаем пассажира
        passenger, created = passenger_service.get_or_create_passenger(
            "test_user", "123456789"
        )
        assert created is True
        assert passenger.telegram_username == "test_user"

        # 2. Создаем автобус
        from database.connection import db_connection

        db_connection.execute_query(
            "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "БУС-001",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "10:00",
                30,
                "Туда",
                True,
            ),
        )

        buses = bus_service.get_all_buses()
        assert len(buses) == 1
        bus = buses[0]

        # 3. Проверяем доступность автобуса
        availability = bus_service.get_bus_availability_info(bus)
        assert availability["capacity"] == 30
        assert availability["booked"] == 0
        assert availability["free"] == 30
        assert availability["is_available"] is True

        # 4. Создаем бронирование
        can_book, error_msg = booking_service.can_book_bus(passenger, bus)
        assert can_book is True
        assert error_msg == ""

        success = booking_service.create_booking(passenger, bus)
        assert success is True

        # 5. Проверяем, что бронирование создано
        reservations = booking_service.get_user_bookings(passenger)
        assert len(reservations) == 1
        assert reservations[0].passenger_id == passenger.id
        assert reservations[0].bus_id == bus.id

        # 6. Проверяем обновленную доступность автобуса
        availability_after = bus_service.get_bus_availability_info(bus)
        assert availability_after["booked"] == 1
        assert availability_after["free"] == 29

        # 7. Отменяем бронирование
        success = booking_service.cancel_booking(reservations[0].id, passenger)
        assert success is True

        # 8. Проверяем, что бронирование отменено
        reservations_after = booking_service.get_user_bookings(passenger)
        assert len(reservations_after) == 0

        # 9. Проверяем восстановленную доступность автобуса
        availability_final = bus_service.get_bus_availability_info(bus)
        assert availability_final["booked"] == 0
        assert availability_final["free"] == 30

    def test_waiting_list_flow(self, temp_db):
        """Тест процесса работы с листом ожидания"""
        # Создаем сервисы
        passenger_service = PassengerService()
        bus_service = BusService()
        waiting_service = WaitingListService()

        # 1. Создаем пассажира
        passenger, created = passenger_service.get_or_create_passenger(
            "test_user", "123456789"
        )
        assert created is True

        # 2. Создаем автобус с малой вместимостью
        from database.connection import db_connection

        db_connection.execute_query(
            "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "БУС-002",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "12:00",
                1,
                "Обратно",
                True,
            ),
        )

        buses = bus_service.get_all_buses()
        bus = buses[0]

        # 3. Заполняем автобус
        db_connection.execute_query(
            "INSERT INTO Reservations (PassengerID, BusID, ReservationDate, Direction) VALUES (?, ?, ?, ?)",
            (999, bus.id, "2024-01-15 10:00:00", bus.direction),
        )

        # 4. Добавляем пассажира в лист ожидания
        success = waiting_service.add_to_waiting_list(passenger, bus)
        assert success is True

        # 5. Проверяем, что запись в листе ожидания создана
        waiting_records = waiting_service.get_waiting_records_for_bus(bus.id)
        assert len(waiting_records) == 1
        assert waiting_records[0].passenger_id == passenger.id
        assert waiting_records[0].bus_id == bus.id
        assert waiting_records[0].status == "Waiting"

        # 6. Освобождаем место (удаляем бронирование)
        db_connection.execute_query(
            "DELETE FROM Reservations WHERE BusID = ?", (bus.id,)
        )

        # 7. Подтверждаем бронирование из листа ожидания
        success = waiting_service.confirm_waiting_booking(passenger, bus)
        assert success is True

        # 8. Проверяем, что бронирование создано
        reservations = ReservationRepository.get_by_passenger(passenger.id)
        assert len(reservations) == 1
        assert reservations[0].passenger_id == passenger.id
        assert reservations[0].bus_id == bus.id

        # 9. Проверяем, что статус в листе ожидания обновлен
        updated_records = WaitingListRepository.get_all()
        assert len(updated_records) == 1
        assert updated_records[0].status == "Confirmed"

    def test_multiple_passengers_booking(self, temp_db):
        """Тест бронирования несколькими пассажирами"""
        # Создаем сервисы
        passenger_service = PassengerService()
        bus_service = BusService()
        booking_service = BookingService()

        # 1. Создаем автобус
        from database.connection import db_connection

        db_connection.execute_query(
            "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "БУС-003",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "14:00",
                3,
                "Туда",
                True,
            ),
        )

        buses = bus_service.get_all_buses()
        bus = buses[0]

        # 2. Создаем трех пассажиров
        passengers = []
        for i in range(3):
            passenger, created = passenger_service.get_or_create_passenger(
                f"user{i}", f"12345678{i}"
            )
            assert created is True
            passengers.append(passenger)

        # 3. Бронируем места для всех пассажиров
        for passenger in passengers:
            success = booking_service.create_booking(passenger, bus)
            assert success is True

        # 4. Проверяем, что все бронирования созданы
        all_reservations = ReservationRepository.get_all()
        assert len(all_reservations) == 3

        # 5. Проверяем доступность автобуса
        availability = bus_service.get_bus_availability_info(bus)
        assert availability["booked"] == 3
        assert availability["free"] == 0
        assert availability["is_available"] is False

        # 6. Пытаемся забронировать еще одно место (должно не получиться)
        passenger4, created = passenger_service.get_or_create_passenger(
            "user4", "123456784"
        )
        can_book, error_msg = booking_service.can_book_bus(passenger4, bus)
        assert can_book is False
        assert "заняты" in error_msg

        # 7. Добавляем четвертого пассажира в лист ожидания
        waiting_service = WaitingListService()
        success = waiting_service.add_to_waiting_list(passenger4, bus)
        assert success is True

        # 8. Проверяем лист ожидания
        waiting_records = waiting_service.get_waiting_records_for_bus(bus.id)
        assert len(waiting_records) == 1
        assert waiting_records[0].passenger_id == passenger4.id

    def test_direction_filtering(self, temp_db):
        """Тест фильтрации автобусов по направлениям"""
        # Создаем сервисы
        bus_service = BusService()

        # 1. Создаем автобусы с разными направлениями
        from database.connection import db_connection

        buses_data = [
            (
                "БУС-001",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "10:00",
                30,
                "Туда",
                True,
            ),
            (
                "БУС-002",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "12:00",
                25,
                "Обратно",
                True,
            ),
            (
                "БУС-003",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "14:00",
                20,
                "Туда",
                True,
            ),
        ]

        for bus_data in buses_data:
            db_connection.execute_query(
                "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                bus_data,
            )

        # 2. Получаем все автобусы
        all_buses = bus_service.get_all_buses()
        assert len(all_buses) == 3

        # 3. Получаем автобусы по направлению "Туда"
        buses_tuda = bus_service.get_buses_for_direction("Туда")
        assert len(buses_tuda) == 2
        assert all(bus.direction == "Туда" for bus in buses_tuda)

        # 4. Получаем автобусы по направлению "Обратно"
        buses_obratno = bus_service.get_buses_for_direction("Обратно")
        assert len(buses_obratno) == 1
        assert buses_obratno[0].direction == "Обратно"

        # 5. Получаем доступные направления
        directions = bus_service.get_available_directions()
        assert len(directions) == 2
        assert "Туда" in directions
        assert "Обратно" in directions

    def test_passenger_fio_management(self, temp_db):
        """Тест управления ФИО пассажиров"""
        # Создаем сервис
        passenger_service = PassengerService()

        # 1. Создаем пассажира без ФИО
        passenger, created = passenger_service.get_or_create_passenger(
            "test_user", "123456789"
        )
        assert created is True
        assert passenger.fio is None

        # 2. Проверяем, что ФИО не заполнено
        has_fio, passenger_check = passenger_service.check_user_fio("test_user")
        assert has_fio is False
        assert passenger_check.fio is None

        # 3. Обновляем ФИО
        success = passenger_service.update_fio("test_user", "Иванов Иван Иванович")
        assert success is True

        # 4. Проверяем, что ФИО обновлено
        has_fio_after, passenger_after = passenger_service.check_user_fio("test_user")
        assert has_fio_after is True
        assert passenger_after.fio == "Иванов Иван Иванович"

        # 5. Пытаемся обновить на невалидное ФИО
        success_invalid = passenger_service.update_fio("test_user", "Ив")
        assert success_invalid is False

        # 6. Проверяем, что ФИО не изменилось
        has_fio_final, passenger_final = passenger_service.check_user_fio("test_user")
        assert has_fio_final is True
        assert passenger_final.fio == "Иванов Иван Иванович"
