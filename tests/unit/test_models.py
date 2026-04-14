"""
Тесты для моделей данных
"""

import pytest

from models.entities import Bus, BusOwner, Passenger, Reservation, WaitingListRecord
from tests.factories import (
    BusFactory,
    BusOwnerFactory,
    PassengerFactory,
    ReservationFactory,
    WaitingListRecordFactory,
)


class TestPassenger:
    """Тесты для модели Passenger"""

    def test_passenger_creation(self):
        """Тест создания пассажира"""
        passenger = PassengerFactory.build()

        assert passenger.telegram_username is not None
        assert passenger.role == "user"
        assert passenger.fio is not None

    def test_passenger_from_tuple(self):
        """Тест создания пассажира из кортежа"""
        data = (
            1,
            "test_user",
            "123456789",
            "Иванов Иван Иванович",
            "+7900123456",
            "Комментарий",
            "user",
        )
        passenger = Passenger.from_tuple(data)

        assert passenger.id == 1
        assert passenger.telegram_username == "test_user"
        assert passenger.chat_id == "123456789"
        assert passenger.fio == "Иванов Иван Иванович"
        assert passenger.phone == "+7900123456"
        assert passenger.comment == "Комментарий"
        assert passenger.role == "user"

    def test_passenger_is_admin(self):
        """Тест проверки администратора"""
        admin = PassengerFactory.build(role="admin")
        chief = PassengerFactory.build(role="chief")
        user = PassengerFactory.build(role="user")

        assert admin.is_admin() is True
        assert chief.is_admin() is False
        assert user.is_admin() is False

    def test_passenger_is_chief(self):
        """Тест проверки администратора"""
        admin = PassengerFactory.build(role="admin")
        chief = PassengerFactory.build(role="chief")
        user = PassengerFactory.build(role="user")

        assert admin.is_chief() is False
        assert chief.is_chief() is True
        assert user.is_chief() is False

    def test_passenger_has_fio(self):
        """Тест проверки наличия ФИО"""
        passenger_with_fio = PassengerFactory.build(fio="Иванов Иван Иванович")
        passenger_without_fio = PassengerFactory.build(fio="")
        passenger_with_none_fio = PassengerFactory.build(fio=None)

        assert passenger_with_fio.has_fio() is True
        assert passenger_without_fio.has_fio() is False
        assert passenger_with_none_fio.has_fio() is False


class TestBus:
    """Тесты для модели Bus"""

    def test_bus_creation(self):
        """Тест создания автобуса"""
        bus = BusFactory.build()

        assert bus.number is not None
        assert bus.departure_place is not None
        assert bus.destination is not None
        assert bus.capacity > 0
        assert bus.is_active is True

    def test_bus_from_tuple(self):
        """Тест создания автобуса из кортежа"""
        data = (
            1,
            "БУС-001",
            "Москва",
            "Переславль-Залесский",
            "2024-01-15",
            "10:00",
            30,
            "Туда",
            True,
        )
        bus = Bus.from_tuple(data)

        assert bus.id == 1
        assert bus.number == "БУС-001"
        assert bus.departure_place == "Москва"
        assert bus.destination == "Переславль-Залесский"
        assert bus.departure_date == "2024-01-15"
        assert bus.departure_time == "10:00"
        assert bus.capacity == 30
        assert bus.direction == "Туда"
        assert bus.is_active is True

    def test_bus_get_route(self):
        """Тест получения маршрута"""
        bus = BusFactory.build(
            departure_place="Москва", destination="Переславль-Залесский"
        )

        assert bus.get_route() == "Москва-Переславль-Залесский"

    def test_bus_get_departure_info(self):
        """Тест получения информации о времени отправления"""
        bus = BusFactory.build(departure_date="2024-01-15", departure_time="10:00")

        assert bus.get_departure_info() == "2024-01-15 10:00"


class TestReservation:
    """Тесты для модели Reservation"""

    def test_reservation_creation(self):
        """Тест создания бронирования"""
        reservation = ReservationFactory.build()

        assert reservation.passenger_id is not None
        assert reservation.bus_id is not None
        assert reservation.direction is not None
        assert reservation.reservation_date is not None

    def test_reservation_from_tuple(self):
        """Тест создания бронирования из кортежа"""
        data = (1, 1, 1, "2024-01-15 10:00:00", "Туда")
        reservation = Reservation.from_tuple(data)

        assert reservation.id == 1
        assert reservation.passenger_id == 1
        assert reservation.bus_id == 1
        assert reservation.reservation_date == "2024-01-15 10:00:00"
        assert reservation.direction == "Туда"


class TestWaitingListRecord:
    """Тесты для модели WaitingListRecord"""

    def test_waiting_list_record_creation(self):
        """Тест создания записи листа ожидания"""
        record = WaitingListRecordFactory.build()

        assert record.passenger_id is not None
        assert record.bus_id is not None
        assert record.status == "Waiting"
        assert record.notification_sent == "No"

    def test_waiting_list_record_from_tuple(self):
        """Тест создания записи из кортежа"""
        data = (1, 1, 1, "2024-01-15 10:00:00", "Waiting", "No")
        record = WaitingListRecord.from_tuple(data)

        assert record.id == 1
        assert record.passenger_id == 1
        assert record.bus_id == 1
        assert record.request_time == "2024-01-15 10:00:00"
        assert record.status == "Waiting"
        assert record.notification_sent == "No"

    def test_waiting_list_record_is_waiting(self):
        """Тест проверки статуса ожидания"""
        waiting_record = WaitingListRecordFactory.build(status="Waiting")
        confirmed_record = WaitingListRecordFactory.build(status="Confirmed")

        assert waiting_record.is_waiting() is True
        assert confirmed_record.is_waiting() is False

    def test_waiting_list_record_is_confirmed(self):
        """Тест проверки статуса подтверждения"""
        waiting_record = WaitingListRecordFactory.build(status="Waiting")
        confirmed_record = WaitingListRecordFactory.build(status="Confirmed")

        assert waiting_record.is_confirmed() is False
        assert confirmed_record.is_confirmed() is True

    def test_waiting_list_record_notification_sent(self):
        """Тест проверки отправки уведомления"""
        sent_record = WaitingListRecordFactory.build(notification_sent="Yes")
        not_sent_record = WaitingListRecordFactory.build(notification_sent="No")

        assert sent_record.is_notification_sent() is True
        assert not_sent_record.is_notification_sent() is False


class TestBusOwner:
    """Тесты для модели BusOwner"""

    def test_bus_owner_creation(self):
        """Тест создания владельца автобуса"""
        owner = BusOwnerFactory.build()

        assert owner.bus_id is not None
        assert owner.chief_id is not None

    def test_bus_owner_from_tuple(self):
        """Тест создания владельца из кортежа"""
        data = (1, 1, 1)
        owner = BusOwner.from_tuple(data)

        assert owner.id == 1
        assert owner.bus_id == 1
        assert owner.chief_id == 1
