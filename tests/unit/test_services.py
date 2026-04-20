"""
Тесты для сервисов
"""

import sqlite3
from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram.error import BadRequest, Forbidden

from models.entities import Bus, Passenger, Reservation, WaitingListRecord
from services.booking_service import BookingService
from services.broadcast_service import BroadcastService, BroadcastStats
from services.bus_service import BusService
from services.export_service import ExportService
from services.passenger_service import PassengerService
from services.waiting_list_service import WaitingListService
from tests.factories import (
    BusFactory,
    PassengerFactory,
    ReservationFactory,
    WaitingListRecordFactory,
)


class TestPassengerService:
    """Тесты для PassengerService"""

    def test_get_or_create_passenger_existing(self):
        """Тест получения существующего пассажира"""
        service = PassengerService()
        mock_passenger = PassengerFactory.build()

        with patch.object(
            service.repository, "get_by_username", return_value=mock_passenger
        ):
            passenger, created = service.get_or_create_passenger(
                "test_user", "123456789"
            )

            assert passenger == mock_passenger
            assert created is False

    def test_get_or_create_passenger_new(self):
        """Тест создания нового пассажира"""
        service = PassengerService()
        mock_passenger = PassengerFactory.build()

        with (
            patch.object(service.repository, "get_by_username", return_value=None),
            patch.object(service.repository, "create", return_value=mock_passenger),
        ):

            passenger, created = service.get_or_create_passenger(
                "test_user", "123456789"
            )

            assert passenger == mock_passenger
            assert created is True

    def test_get_or_create_passenger_update_chat_id(self):
        """Тест обновления chat_id для существующего пассажира"""
        service = PassengerService()
        mock_passenger = PassengerFactory.build(chat_id=None)

        with (
            patch.object(
                service.repository, "get_by_username", return_value=mock_passenger
            ),
            patch.object(service.repository, "update_chat_id") as mock_update,
        ):

            passenger, created = service.get_or_create_passenger(
                "test_user", "123456789"
            )

            mock_update.assert_called_once_with("test_user", "123456789")
            assert created is False

    def test_update_personal_data_success(self):
        """Тест успешного сохранения персональных данных"""
        service = PassengerService()
        data = {
            "last_name": "Иванов",
            "first_name": "Иван",
            "patronymic": "Иванович",
            "phone": "+79001234567",
            "birth_date": "01.01.1990",
            "passport_number": "1234 567890",
            "citizenship": "РФ",
        }

        with patch.object(service.repository, "update_personal_data") as mock_update:
            result = service.update_personal_data("test_user", data)

            assert result == (True, "")
            mock_update.assert_called_once()

    def test_is_admin_true(self):
        """Тест проверки администратора"""
        service = PassengerService()
        mock_passenger = PassengerFactory.build(role="admin")

        with patch.object(
            service.repository, "get_by_username", return_value=mock_passenger
        ):
            result = service.is_admin("test_user")
            assert result is True

    def test_is_admin_false(self):
        """Тест проверки обычного пользователя"""
        service = PassengerService()
        mock_passenger = PassengerFactory.build(role="user")

        with patch.object(
            service.repository, "get_by_username", return_value=mock_passenger
        ):
            result = service.is_admin("test_user")
            assert result is False


class TestBusService:
    """Тесты для BusService"""

    def test_get_available_directions(self):
        """Тест получения доступных направлений"""
        service = BusService()
        mock_buses = [
            BusFactory.build(direction="Туда"),
            BusFactory.build(direction="Обратно"),
            BusFactory.build(direction="Туда"),  # Дубликат
        ]

        with patch.object(
            service.bus_repository, "get_active_buses", return_value=mock_buses
        ):
            directions = service.get_available_directions()

            assert len(directions) == 2
            assert "Туда" in directions
            assert "Обратно" in directions

    def test_get_buses_for_direction(self):
        """Тест получения автобусов по направлению"""
        service = BusService()
        mock_buses = [BusFactory.build(direction="Туда")]

        with patch.object(
            service.bus_repository, "get_by_direction", return_value=mock_buses
        ):
            buses = service.get_buses_for_direction("Туда")

            assert buses == mock_buses

    def test_get_bus_availability_info(self):
        """Тест получения информации о доступности мест"""
        service = BusService()
        mock_bus = BusFactory.build(capacity=30)
        mock_reservations = [ReservationFactory.build() for _ in range(5)]

        with patch.object(
            service.reservation_repository, "get_by_bus", return_value=mock_reservations
        ):
            info = service.get_bus_availability_info(mock_bus)

            assert info["capacity"] == 30
            assert info["booked"] == 5
            assert info["free"] == 25
            assert info["is_available"] is True

    def test_get_bus_availability_info_full(self):
        """Тест получения информации о полностью занятом автобусе"""
        service = BusService()
        mock_bus = BusFactory.build(capacity=30)
        mock_reservations = [ReservationFactory.build() for _ in range(30)]

        with patch.object(
            service.reservation_repository, "get_by_bus", return_value=mock_reservations
        ):
            info = service.get_bus_availability_info(mock_bus)

            assert info["capacity"] == 30
            assert info["booked"] == 30
            assert info["free"] == 0
            assert info["is_available"] is False


class TestBookingService:
    """Тесты для BookingService"""

    def test_can_book_bus_success(self):
        """Тест успешной проверки возможности бронирования"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build(capacity=30)
        mock_reservations = [ReservationFactory.build() for _ in range(5)]

        with (
            patch.object(
                service.reservation_repository,
                "get_by_bus",
                return_value=mock_reservations,
            ),
            patch.object(
                service.reservation_repository, "get_by_passenger", return_value=[]
            ),
        ):

            can_book, error_msg = service.can_book_bus(mock_passenger, mock_bus)

            assert can_book is True
            assert error_msg == ""

    def test_can_book_bus_full(self):
        """Тест проверки полностью занятого автобуса"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build(capacity=30)
        mock_reservations = [ReservationFactory.build() for _ in range(30)]

        with patch.object(
            service.reservation_repository, "get_by_bus", return_value=mock_reservations
        ):
            can_book, error_msg = service.can_book_bus(mock_passenger, mock_bus)

            assert can_book is False
            assert "заняты" in error_msg

    def test_can_book_bus_already_registered(self):
        """Тест проверки уже зарегистрированного пассажира"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build(direction="Туда")
        mock_existing_reservation = ReservationFactory.build(
            bus_id=mock_bus.id, direction="Туда"
        )

        with (
            patch.object(service.reservation_repository, "get_by_bus", return_value=[]),
            patch.object(
                service.reservation_repository,
                "get_by_passenger",
                return_value=[mock_existing_reservation],
            ),
        ):

            can_book, error_msg = service.can_book_bus(mock_passenger, mock_bus)

            assert can_book is False
            assert "зарегистрированы" in error_msg

    def test_create_booking_success(self):
        """Тест успешного создания бронирования"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build()

        with (
            patch.object(service, "can_book_bus", return_value=(True, "")),
            patch.object(service.reservation_repository, "create") as mock_create,
        ):

            result = service.create_booking(mock_passenger, mock_bus)

            assert result is True
            mock_create.assert_called_once_with(
                mock_passenger.id, mock_bus.id, mock_bus.direction
            )

    def test_create_booking_failed(self):
        """Тест неудачного создания бронирования"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build()

        with patch.object(
            service, "can_book_bus", return_value=(False, "Автобус занят")
        ):
            result = service.create_booking(mock_passenger, mock_bus)

            assert result is False

    def test_get_user_bookings(self):
        """Тест получения бронирований пользователя"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_reservations = [ReservationFactory.build() for _ in range(3)]

        with patch.object(
            service.reservation_repository,
            "get_by_passenger",
            return_value=mock_reservations,
        ):
            reservations = service.get_user_bookings(mock_passenger)

            assert reservations == mock_reservations

    def test_has_active_bookings(self):
        """Тест проверки активных бронирований"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_reservations = [ReservationFactory.build()]

        with patch.object(
            service.reservation_repository,
            "get_by_passenger",
            return_value=mock_reservations,
        ):
            assert service.has_active_bookings(mock_passenger) is True

    def test_cancel_booking_success(self):
        """Тест успешной отмены бронирования"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_reservation = ReservationFactory.build()

        with (
            patch.object(
                service.reservation_repository,
                "get_by_id_and_passenger",
                return_value=mock_reservation,
            ),
            patch.object(service.reservation_repository, "delete_by_id") as mock_delete,
        ):

            result = service.cancel_booking(1, mock_passenger)

            assert result is True
            mock_delete.assert_called_once_with(1)

    def test_cancel_booking_not_found(self):
        """Тест отмены несуществующего бронирования"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()

        with patch.object(
            service.reservation_repository, "get_by_id_and_passenger", return_value=None
        ):
            result = service.cancel_booking(999, mock_passenger)

            assert result is False

    def test_add_to_waiting_list_success(self):
        """Тест успешного добавления в лист ожидания"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build()

        with (
            patch.object(
                service.waiting_repository, "get_by_passenger_and_bus", return_value=[]
            ),
            patch.object(service.waiting_repository, "create") as mock_create,
        ):

            result = service.add_to_waiting_list(mock_passenger, mock_bus)

            assert result is True
            mock_create.assert_called_once_with(mock_passenger.id, mock_bus.id)

    def test_add_to_waiting_list_already_exists(self):
        """Тест добавления в лист ожидания уже существующей записи"""
        service = BookingService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build()
        mock_existing_record = WaitingListRecordFactory.build()

        with patch.object(
            service.waiting_repository,
            "get_by_passenger_and_bus",
            return_value=[mock_existing_record],
        ):
            result = service.add_to_waiting_list(mock_passenger, mock_bus)

            assert result is False


class TestWaitingListService:
    """Тесты для WaitingListService"""

    def test_add_to_waiting_list_success(self):
        """Тест успешного добавления в лист ожидания"""
        service = WaitingListService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build()

        with (
            patch.object(
                service.waiting_repository, "get_by_passenger_and_bus", return_value=[]
            ),
            patch.object(service.waiting_repository, "create") as mock_create,
        ):

            result = service.add_to_waiting_list(mock_passenger, mock_bus)

            assert result is True
            mock_create.assert_called_once_with(mock_passenger.id, mock_bus.id)

    def test_get_waiting_records_for_bus(self):
        """Тест получения записей листа ожидания для автобуса"""
        service = WaitingListService()
        mock_records = [WaitingListRecordFactory.build(bus_id=1) for _ in range(3)]

        with patch.object(
            service.waiting_repository, "get_waiting_records", return_value=mock_records
        ):
            records = service.get_waiting_records_for_bus(1)

            assert len(records) == 3
            assert all(record.bus_id == 1 for record in records)

    def test_confirm_waiting_booking_success(self):
        """Тест успешного подтверждения брони из листа ожидания"""
        service = WaitingListService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build(capacity=30)
        mock_reservations = [ReservationFactory.build() for _ in range(5)]
        mock_waiting_records = [WaitingListRecordFactory.build()]

        with (
            patch.object(
                service.reservation_repository,
                "get_by_bus",
                return_value=mock_reservations,
            ),
            patch.object(service.reservation_repository, "create") as mock_create,
            patch.object(
                service.waiting_repository,
                "get_by_passenger_and_bus",
                return_value=mock_waiting_records,
            ),
            patch.object(
                service.waiting_repository, "update_status"
            ) as mock_update_status,
            patch.object(
                service.waiting_repository, "update_notification"
            ) as mock_update_notification,
        ):

            result = service.confirm_waiting_booking(mock_passenger, mock_bus)

            assert result is True
            mock_create.assert_called_once_with(
                mock_passenger.id, mock_bus.id, mock_bus.direction
            )
            mock_update_status.assert_called_once()
            mock_update_notification.assert_called_once()

    def test_confirm_waiting_booking_bus_full(self):
        """Тест подтверждения брони для полностью занятого автобуса"""
        service = WaitingListService()
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build(capacity=30)
        mock_reservations = [ReservationFactory.build() for _ in range(30)]

        with patch.object(
            service.reservation_repository, "get_by_bus", return_value=mock_reservations
        ):
            result = service.confirm_waiting_booking(mock_passenger, mock_bus)

            assert result is False


class TestExportService:
    """Тесты для ExportService"""

    def test_export_service_initialization(self):
        """Тест инициализации сервиса экспорта"""
        service = ExportService()

        assert service.bus_repository is not None
        assert service.reservation_repository is not None
        assert service.passenger_repository is not None
        assert service.bus_owner_repository is not None

    @pytest.mark.asyncio
    async def test_export_buses_to_excel(self):
        """Тест экспорта данных в Excel"""
        service = ExportService()
        mock_buses = [BusFactory.build()]
        mock_reservations = [ReservationFactory.build()]
        mock_passengers = [PassengerFactory.build()]
        mock_bus_owners = []

        with (
            patch.object(service.bus_repository, "get_all", return_value=mock_buses),
            patch.object(
                service.reservation_repository,
                "get_all",
                return_value=mock_reservations,
            ),
            patch.object(
                service.passenger_repository, "get_all", return_value=mock_passengers
            ),
            patch.object(
                service.bus_owner_repository, "get_all", return_value=mock_bus_owners
            ),
            patch.object(service, "_generate_excel_file") as mock_generate,
        ):

            result = await service.export_buses_to_excel()

            assert result is not None
            mock_generate.assert_called_once()

    def test_cleanup_temp_file(self, tmp_path):
        """Тест очистки временного файла"""
        service = ExportService()
        temp_file = tmp_path / "test_file.xlsx"
        temp_file.write_text("test content")

        # Файл существует
        assert temp_file.exists()

        # Очищаем файл
        service.cleanup_temp_file(str(temp_file))

        # Файл удален
        assert not temp_file.exists()

    def test_cleanup_temp_file_not_exists(self):
        """Тест очистки несуществующего файла"""
        service = ExportService()

        # Не должно вызывать исключение
        service.cleanup_temp_file("nonexistent_file.xlsx")


class TestBroadcastService:
    """Тесты для BroadcastService"""

    def test_get_passengers_for_broadcast_excludes_chief(self):
        """Пассажир с id chief_id исключается из списка рассылки"""
        service = BroadcastService()
        chief_id = 10
        p1 = PassengerFactory.build(id=1, chat_id="111")
        chief = PassengerFactory.build(id=10, chat_id="222")
        p3 = PassengerFactory.build(id=3, chat_id="333")
        mock_passengers = [p1, chief, p3]

        with patch.object(
            service.passenger_repository, "get_by_bus", return_value=mock_passengers
        ):
            result = service.get_passengers_for_broadcast(5, chief_id)

        assert result == [p1, p3]

    def test_get_passengers_for_broadcast_repository_error_returns_none(self):
        """При ошибке SQLite возвращается None"""
        service = BroadcastService()

        with patch.object(
            service.passenger_repository,
            "get_by_bus",
            side_effect=sqlite3.OperationalError("database locked"),
        ):
            result = service.get_passengers_for_broadcast(1, 1)

        assert result is None

    @pytest.mark.asyncio
    async def test_send_broadcast_all_success(self):
        """Успешная рассылка всем получателям"""
        service = BroadcastService()
        passengers = [
            PassengerFactory.build(chat_id="100"),
            PassengerFactory.build(chat_id="200"),
        ]
        bot = Mock()
        bot.send_message = AsyncMock()
        bot.copy_message = AsyncMock()

        with patch("services.broadcast_service.asyncio.sleep", new_callable=AsyncMock):
            counts = await service.send_broadcast(bot, passengers, 100, 42, "preview")

        assert counts == BroadcastStats(2, 0, 0)
        assert bot.copy_message.await_count == 2

    @pytest.mark.asyncio
    async def test_send_broadcast_empty_list(self):
        """Пустой список пассажиров — нули в статистике"""
        service = BroadcastService()
        bot = Mock()
        bot.send_message = AsyncMock()
        bot.copy_message = AsyncMock()

        with patch("services.broadcast_service.asyncio.sleep", new_callable=AsyncMock):
            counts = await service.send_broadcast(bot, [], 100, 1, "preview")

        assert counts == BroadcastStats(0, 0, 0)
        bot.copy_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_broadcast_counts_forbidden_bad_request_and_generic(self):
        """Подсчёт успешных, Forbidden, BadRequest и прочих ошибок"""
        service = BroadcastService()
        passengers = [PassengerFactory.build() for _ in range(4)]
        bot = Mock()
        bot.send_message = AsyncMock()
        bot.copy_message = AsyncMock(
            side_effect=[
                None,
                Forbidden("blocked"),
                BadRequest("invalid"),
                ValueError("other"),
            ]
        )

        with patch("services.broadcast_service.asyncio.sleep", new_callable=AsyncMock):
            counts = await service.send_broadcast(bot, passengers, 100, 7, "preview")

        assert counts == BroadcastStats(1, 2, 1)
