"""
Сервис для работы с бронированиями
"""

import logging
from typing import List, Optional, Tuple

from database.repositories import ReservationRepository, WaitingListRepository
from models.entities import Bus, Passenger, Reservation, WaitingListRecord

logger = logging.getLogger(__name__)


class BookingService:
    """Сервис для работы с бронированиями"""

    def __init__(self):
        self.reservation_repository = ReservationRepository()
        self.waiting_repository = WaitingListRepository()

    def can_book_bus(self, passenger: Passenger, bus: Bus) -> Tuple[bool, str]:
        """
        Проверяет, может ли пассажир забронировать автобус

        Returns:
            Tuple[bool, str]: (может_ли_забронировать, сообщение_об_ошибке)
        """
        # Проверяем, есть ли свободные места
        reservations = self.reservation_repository.get_by_bus(bus.id)
        if len(reservations) >= bus.capacity:
            return False, "Все места в автобусе уже заняты."

        # Проверяем, нет ли уже брони на это направление
        user_reservations = self.reservation_repository.get_by_passenger(passenger.id)
        existing_res = [
            r
            for r in user_reservations
            if r.bus_id == bus.id and r.direction == bus.direction
        ]

        if existing_res:
            return False, "Вы уже зарегистрированы на этот автобус и направление."

        return True, ""

    def create_booking(self, passenger: Passenger, bus: Bus) -> bool:
        """
        Создает бронирование

        Returns:
            bool: Успешность операции
        """
        try:
            can_book, error_msg = self.can_book_bus(passenger, bus)
            if not can_book:
                logger.warning(f"Не удалось создать бронирование: {error_msg}")
                return False

            self.reservation_repository.create(passenger.id, bus.id, bus.direction)
            self._sync_waiting_list_after_booking(passenger, bus)
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании бронирования: {str(e)}")
            return False

    def get_user_bookings(self, passenger: Passenger) -> List[Reservation]:
        """Получает бронирования пользователя"""
        return self.reservation_repository.get_by_passenger(passenger.id)

    def get_user_waiting_records(self, passenger: Passenger) -> List[WaitingListRecord]:
        """Получает активные записи пользователя в листе ожидания"""
        return self.waiting_repository.get_by_passenger(passenger.id)

    def has_active_bookings(self, passenger: Passenger) -> bool:
        """Проверяет, есть ли у пользователя активные бронирования"""
        return bool(self.get_user_bookings(passenger))

    def cancel_booking(self, reservation_id: int, passenger: Passenger) -> bool:
        """
        Отменяет бронирование

        Returns:
            bool: Успешность операции
        """
        try:
            # Проверяем, принадлежит ли бронирование пользователю
            reservation = self.reservation_repository.get_by_id_and_passenger(
                reservation_id, passenger.id
            )

            if not reservation:
                return False

            self.reservation_repository.delete_by_id(reservation_id)
            return True
        except Exception as e:
            logger.error(f"Ошибка при отмене бронирования: {str(e)}")
            return False

    def add_to_waiting_list(self, passenger: Passenger, bus: Bus) -> bool:
        """
        Добавляет пассажира в лист ожидания

        Returns:
            bool: Успешность операции
        """
        try:
            # Проверяем, не находится ли уже в очереди
            existing = self.waiting_repository.get_by_passenger_and_bus(
                passenger.id, bus.id
            )

            if existing:
                return False

            self.waiting_repository.create(passenger.id, bus.id)
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении в лист ожидания: {str(e)}")
            return False

    def _sync_waiting_list_after_booking(self, passenger: Passenger, bus: Bus) -> None:
        """Синхронизирует запись в листе ожидания после успешной брони."""
        waiting_records = self.waiting_repository.get_by_passenger_and_bus(
            passenger.id, bus.id
        )
        if not waiting_records:
            return

        if any(record.is_notification_sent() for record in waiting_records):
            for record in waiting_records:
                if record.is_waiting():
                    self.waiting_repository.update_status(record.id, "Confirmed")
                    self.waiting_repository.update_notification(record.id, "Yes")
            return

        self.waiting_repository.delete_by_passenger_and_bus(passenger.id, bus.id)
