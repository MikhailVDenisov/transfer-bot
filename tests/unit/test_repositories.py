"""
Тесты для репозиториев
"""

import pytest

from database.repositories import (
    BusOwnerRepository,
    BusRepository,
    PassengerRepository,
    ReservationRepository,
    WaitingListRepository,
)
from tests.factories import (
    BusFactory,
    BusOwnerFactory,
    PassengerFactory,
    ReservationFactory,
    WaitingListRecordFactory,
)


class TestPassengerRepository:
    """Тесты для PassengerRepository"""

    def test_get_by_username_not_found(self):
        """Тест получения несуществующего пассажира"""
        passenger = PassengerRepository.get_by_username("nonexistent_user")
        assert passenger is None

    def test_create_passenger(self):
        """Тест создания пассажира"""
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )

        assert passenger is not None
        assert passenger.telegram_username == test_passenger.telegram_username
        assert passenger.chat_id == test_passenger.chat_id
        assert passenger.role == "user"

    def test_get_by_username_found(self):
        """Тест получения существующего пассажира"""
        # Создаем пассажира
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        created_passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )

        # Получаем его по username
        found_passenger = PassengerRepository.get_by_username(
            test_passenger.telegram_username
        )

        assert found_passenger is not None
        assert found_passenger.id == created_passenger.id
        assert found_passenger.telegram_username == test_passenger.telegram_username

    def test_update_chat_id(self):
        """Тест обновления chat_id"""
        # Создаем пассажира
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )

        # Обновляем chat_id
        PassengerRepository.update_chat_id(
            test_passenger.telegram_username, "987654321"
        )

        # Проверяем обновление
        updated_passenger = PassengerRepository.get_by_username(
            test_passenger.telegram_username
        )
        assert updated_passenger.chat_id == "987654321"

    def test_update_fio(self):
        """Тест обновления ФИО"""
        # Создаем пассажира
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )

        # Обновляем ФИО
        PassengerRepository.update_fio(
            test_passenger.telegram_username, "Иванов Иван Иванович"
        )

        # Проверяем обновление
        updated_passenger = PassengerRepository.get_by_username(
            test_passenger.telegram_username
        )
        assert updated_passenger.fio == "Иванов Иван Иванович"

    def test_get_all_passengers(self):
        """Тест получения всех пассажиров"""
        # Создаем несколько пассажиров
        from tests.factories import PassengerFactory

        p1 = PassengerFactory.build()
        p2 = PassengerFactory.build()
        p3 = PassengerFactory.build()
        PassengerRepository.create(p1.telegram_username, p1.chat_id)
        PassengerRepository.create(p2.telegram_username, p2.chat_id)
        PassengerRepository.create(p3.telegram_username, p3.chat_id)

        # Получаем всех пассажиров
        passengers = PassengerRepository.get_all()

        assert len(passengers) == 3
        usernames = [p.telegram_username for p in passengers]
        assert p1.telegram_username in usernames
        assert p2.telegram_username in usernames
        assert p3.telegram_username in usernames

    def test_get_by_bus(self):
        """Тест получения пассажиров по автобусу"""
        # Создаем несколько пассажиров
        from tests.factories import PassengerFactory

        p1 = PassengerFactory.build()
        p2 = PassengerFactory.build()
        p3 = PassengerFactory.build()
        p4 = PassengerFactory.build()
        PassengerRepository.create(p1.telegram_username, p1.chat_id)
        PassengerRepository.create(p2.telegram_username, p2.chat_id)
        PassengerRepository.create(p3.telegram_username, p3.chat_id)
        PassengerRepository.create(p4.telegram_username, p3.chat_id)

        passengers = PassengerRepository.get_all()
        assert len(passengers) == 4

        from database.connection import db_connection

        # Создаем автобус
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
        buses = BusRepository.get_all()
        bus = buses[0]

        # Создаем бронирование
        for passenger in passengers:
            if passenger.id == 1 or passenger.id == 4:
                ReservationRepository.create(passenger.id, bus.id, "Туда")
            elif passenger.id == 3:
                ReservationRepository.create(passenger.id, bus.id, "Сюда")
            else:
                ReservationRepository.create(passenger.id, 999, "Туда")

        reservations = ReservationRepository.get_all()
        assert len(reservations) == 4

        # Проверяем пассажиров по автобусу и направлению
        passengers_by_bus = PassengerRepository.get_by_bus(bus.id)

        assert len(passengers_by_bus) == 3
        usernames = [p.telegram_username for p in passengers]
        assert p1.telegram_username in usernames
        assert p4.telegram_username in usernames


class TestBusRepository:
    """Тесты для BusRepository"""

    def test_get_all_buses_empty(self):
        """Тест получения пустого списка автобусов"""
        buses = BusRepository.get_all()
        assert buses == []

    def test_get_by_id_not_found(self):
        """Тест получения несуществующего автобуса"""
        bus = BusRepository.get_by_id(999)
        assert bus is None

    def test_get_active_buses_empty(self):
        """Тест получения пустого списка активных автобусов"""
        buses = BusRepository.get_active_buses()
        assert buses == []

    def test_get_by_direction_empty(self):
        """Тест получения автобусов по несуществующему направлению"""
        buses = BusRepository.get_by_direction("Несуществующее направление")
        assert buses == []

    def test_create_and_get_bus(self):
        """Тест создания и получения автобуса"""
        # Создаем автобус через SQL (так как у нас нет метода create)
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

        # Получаем автобус
        buses = BusRepository.get_all()
        assert len(buses) == 1

        bus = buses[0]
        assert bus.number == "БУС-001"
        assert bus.departure_place == "Москва"
        assert bus.destination == "Переславль-Залесский"
        assert bus.capacity == 30
        assert bus.direction == "Туда"
        assert bus.is_active is True

    def test_get_by_chief(self):
        """Тест получения автобуса по шефу"""

        from tests.factories import PassengerFactory

        p1 = PassengerFactory.build()
        p2 = PassengerFactory.build()
        PassengerRepository.create(p1.telegram_username, p1.chat_id)
        PassengerRepository.create(p2.telegram_username, p2.chat_id)

        passengers = PassengerRepository.get_all()
        assert len(passengers) == 2

        from database.connection import db_connection

        # Создаем автобус
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

        db_connection.execute_query(
            "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "БУС-001",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "10:00",
                30,
                "Сюда",
                True,
            ),
        )

        db_connection.execute_query(
            "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "БУС-002",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "10:00",
                30,
                "Tуда",
                True,
            ),
        )
        buses = BusRepository.get_all()
        bus1 = buses[0]
        bus2 = buses[1]
        bus3 = buses[2]

        chief1 = passengers[0]
        chief2 = passengers[1]

        # Создаем владельцев автобуса
        db_connection.execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)",
            (bus1.id, chief1.id),
        )

        db_connection.execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)",
            (bus2.id, chief1.id),
        )

        db_connection.execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)",
            (bus3.id, chief2.id),
        )

        owners = BusOwnerRepository.get_all()

        assert len(owners) == 3

        buses_by_chief1 = BusRepository.get_by_chief(chief1.id)

        assert len(buses_by_chief1) == 2

        buses_by_chief2 = BusRepository.get_by_chief(chief2.id)

        assert len(buses_by_chief2) == 1

        assert buses_by_chief1[0].number == "БУС-001"
        assert buses_by_chief1[1].number == "БУС-001"

        assert buses_by_chief2[0].number == "БУС-002"


class TestReservationRepository:
    """Тесты для ReservationRepository"""

    def test_get_all_reservations_empty(self):
        """Тест получения пустого списка бронирований"""
        reservations = ReservationRepository.get_all()
        assert reservations == []

    def test_get_by_bus_empty(self):
        """Тест получения бронирований для несуществующего автобуса"""
        reservations = ReservationRepository.get_by_bus(999)
        assert reservations == []

    def test_get_by_passenger_empty(self):
        """Тест получения бронирований для несуществующего пассажира"""
        reservations = ReservationRepository.get_by_passenger(999)
        assert reservations == []

    def test_create_reservation(self):
        """Тест создания бронирования"""
        # Создаем пассажира и автобус
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )
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
        buses = BusRepository.get_all()
        bus = buses[0]

        # Создаем бронирование
        ReservationRepository.create(passenger.id, bus.id, "Туда")

        # Проверяем создание
        reservations = ReservationRepository.get_all()
        assert len(reservations) == 1

        reservation = reservations[0]
        assert reservation.passenger_id == passenger.id
        assert reservation.bus_id == bus.id
        assert reservation.direction == "Туда"

    def test_delete_by_id(self):
        """Тест удаления бронирования"""
        # Создаем пассажира, автобус и бронирование
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )
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
        buses = BusRepository.get_all()
        bus = buses[0]

        ReservationRepository.create(passenger.id, bus.id, "Туда")
        reservations = ReservationRepository.get_all()
        reservation_id = reservations[0].id

        # Удаляем бронирование
        ReservationRepository.delete_by_id(reservation_id)

        # Проверяем удаление
        reservations_after = ReservationRepository.get_all()
        assert len(reservations_after) == 0


class TestWaitingListRepository:
    """Тесты для WaitingListRepository"""

    def test_get_all_waiting_records_empty(self):
        """Тест получения пустого списка записей листа ожидания"""
        records = WaitingListRepository.get_all()
        assert records == []

    def test_create_waiting_record(self):
        """Тест создания записи листа ожидания"""
        # Создаем пассажира и автобус
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )
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
        buses = BusRepository.get_all()
        bus = buses[0]

        # Создаем запись листа ожидания
        WaitingListRepository.create(passenger.id, bus.id)

        # Проверяем создание
        records = WaitingListRepository.get_all()
        assert len(records) == 1

        record = records[0]
        assert record.passenger_id == passenger.id
        assert record.bus_id == bus.id
        assert record.status == "Waiting"
        assert record.notification_sent == "No"

    def test_update_notification(self):
        """Тест обновления статуса уведомления"""
        # Создаем запись листа ожидания
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )
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
        buses = BusRepository.get_all()
        bus = buses[0]

        WaitingListRepository.create(passenger.id, bus.id)
        records = WaitingListRepository.get_all()
        record_id = records[0].id

        # Обновляем статус уведомления
        WaitingListRepository.update_notification(record_id, "Yes")

        # Проверяем обновление
        updated_records = WaitingListRepository.get_all()
        assert updated_records[0].notification_sent == "Yes"

    def test_get_waiting_records(self):
        """Тест получения записей в статусе ожидания"""
        # Создаем несколько записей с разными статусами
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )
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
        buses = BusRepository.get_all()
        bus = buses[0]

        # Создаем запись в статусе ожидания
        WaitingListRepository.create(passenger.id, bus.id)

        # Создаем запись в другом статусе
        db_connection.execute_query(
            "INSERT INTO WaitingList (PassengerID, BusID, RequestTime, Status, NotificationSent) VALUES (?, ?, ?, ?, ?)",
            (passenger.id, bus.id, "2024-01-15 10:00:00", "Confirmed", "Yes"),
        )

        # Получаем только записи в статусе ожидания
        waiting_records = WaitingListRepository.get_waiting_records()
        assert len(waiting_records) == 1
        assert waiting_records[0].status == "Waiting"


class TestBusOwnerRepository:
    """Тесты для BusOwnerRepository"""

    def test_get_all_bus_owners_empty(self):
        """Тест получения пустого списка владельцев автобусов"""
        owners = BusOwnerRepository.get_all()
        assert owners == []

    def test_get_by_bus_empty(self):
        """Тест получения владельцев для несуществующего автобуса"""
        owners = BusOwnerRepository.get_by_bus(999)
        assert owners == []

    def test_create_and_get_bus_owner(self):
        """Тест создания и получения владельца автобуса"""
        # Создаем пассажира и автобус
        from tests.factories import PassengerFactory

        test_passenger = PassengerFactory.build()
        passenger = PassengerRepository.create(
            test_passenger.telegram_username, test_passenger.chat_id
        )
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
        buses = BusRepository.get_all()
        bus = buses[0]

        # Создаем владельца автобуса
        db_connection.execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)",
            (bus.id, passenger.id),
        )

        # Проверяем создание
        owners = BusOwnerRepository.get_all()
        assert len(owners) == 1

        owner = owners[0]
        assert owner.bus_id == bus.id
        assert owner.chief_id == passenger.id
