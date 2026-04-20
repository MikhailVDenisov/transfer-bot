"""
Сервис для работы с листом ожидания
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from config.settings import NOTIFICATION_TIMEOUT_HOURS
from database.repositories import (
    BusRepository,
    PassengerRepository,
    ReservationRepository,
    WaitingListRepository,
)
from models.entities import Bus, Passenger, WaitingListRecord

logger = logging.getLogger(__name__)


class WaitingListService:
    """Сервис для работы с листом ожидания"""

    def __init__(self):
        self.waiting_repository = WaitingListRepository()
        self.reservation_repository = ReservationRepository()
        self.bus_repository = BusRepository()
        self.passenger_repository = PassengerRepository()

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

    def get_waiting_records_for_bus(self, bus_id: int) -> List[WaitingListRecord]:
        """Получает записи листа ожидания для автобуса"""
        all_records = self.waiting_repository.get_waiting_records()
        return [record for record in all_records if record.bus_id == bus_id]

    def process_waiting_list(self, application) -> None:
        """
        Обрабатывает лист ожидания и отправляет уведомления
        """
        try:
            # Получаем все необходимые данные
            buses = self.bus_repository.get_all()
            reservations = self.reservation_repository.get_all()
            waiting_records = self.waiting_repository.get_waiting_records()
            passengers = self.passenger_repository.get_all()

            # Подготавливаем данные о вместимости автобусов
            bus_capacity = {}
            for bus in buses:
                if bus.is_active:
                    bus_capacity[bus.id] = bus.capacity

            # Подсчитываем количество броней для каждого автобуса
            bus_reserved_counts = {}
            for bus in buses:
                bus_reserved_counts[bus.id] = len(
                    [r for r in reservations if r.bus_id == bus.id]
                )

            # Текущее время для проверки таймаута уведомлений
            current_time = datetime.now()

            # Группируем ожидающих по автобусам
            bus_waiting_groups = {}
            for wait in waiting_records:
                if (
                    wait.is_waiting()
                    and not wait.is_notification_sent()
                    and wait.request_time
                ):

                    try:
                        bus_id = wait.bus_id
                        if bus_id not in bus_waiting_groups:
                            bus_waiting_groups[bus_id] = []

                        request_time = datetime.strptime(
                            wait.request_time, "%Y-%m-%d %H:%M:%S"
                        )
                        bus_waiting_groups[bus_id].append((request_time, wait))
                    except (ValueError, TypeError):
                        continue

            # Для каждого автобуса с ожидающими и свободными местами
            for bus_id, waiting_list in bus_waiting_groups.items():
                # Пропускаем если автобус не существует или нет свободных мест
                if bus_id not in bus_capacity:
                    continue

                free_places = bus_capacity[bus_id] - bus_reserved_counts.get(bus_id, 0)
                if free_places <= 0:
                    continue

                # Берем самого раннего в очереди
                if waiting_list:
                    waiting_list.sort(key=lambda x: x[0])
                    _, wait = waiting_list[0]

                    # Проверяем таймаут уведомления
                    if self._should_reset_notification(wait, current_time):
                        self.waiting_repository.update_notification(wait.id, "No")
                        continue

                    # Отправляем уведомление
                    self._send_waiting_notification(
                        application, wait, passengers, buses
                    )

        except Exception as e:
            logger.exception("Ошибка в process_waiting_list")

    def _should_reset_notification(
        self, wait: WaitingListRecord, current_time: datetime
    ) -> bool:
        """Проверяет, нужно ли сбросить статус уведомления"""
        if not wait.request_time or not wait.is_notification_sent():
            return False

        try:
            request_time = datetime.strptime(wait.request_time, "%Y-%m-%d %H:%M:%S")
            time_diff = current_time - request_time
            return time_diff.total_seconds() > (NOTIFICATION_TIMEOUT_HOURS * 3600)
        except (ValueError, TypeError):
            return False

    def _send_waiting_notification(
        self,
        application,
        wait: WaitingListRecord,
        passengers: List[Passenger],
        buses: List[Bus],
    ):
        """Отправляет уведомление о свободном месте"""
        try:
            # Находим пассажира и автобус
            passenger = next((p for p in passengers if p.id == wait.passenger_id), None)
            bus = next((b for b in buses if b.id == wait.bus_id), None)

            if passenger and bus and passenger.chat_id:
                # Создаем клавиатуру для подтверждения
                from utils.keyboards import create_confirm_booking_keyboard

                keyboard = create_confirm_booking_keyboard(bus.id)

                # Формируем сообщение
                from utils.messages import format_waiting_notification_message

                message = format_waiting_notification_message(bus)

                # Отправляем уведомление (синхронно, так как это вызывается из async контекста)
                import asyncio

                asyncio.create_task(
                    self._send_notification_async(
                        application, passenger.chat_id, message, keyboard
                    )
                )

                # Обновляем статус уведомления
                self.waiting_repository.update_notification(wait.id, "Yes")

                logger.info(
                    f"Уведомление отправлено пассажиру {passenger.id} для автобуса {bus.id}"
                )

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {str(e)}")

    async def _send_notification_async(
        self, application, chat_id: str, message: str, keyboard
    ):
        """Асинхронно отправляет уведомление"""
        try:
            await application.bot.send_message(
                chat_id=chat_id, text=message, reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления в чат {chat_id}: {str(e)}")

    def confirm_waiting_booking(self, passenger: Passenger, bus: Bus) -> bool:
        """
        Подтверждает бронирование из листа ожидания

        Returns:
            bool: Успешность операции
        """
        try:
            # Проверяем, есть ли свободные места
            reservations = self.reservation_repository.get_by_bus(bus.id)
            if len(reservations) >= bus.capacity:
                return False

            # Создаем бронирование
            self.reservation_repository.create(passenger.id, bus.id, bus.direction)

            # Обновляем статус в листе ожидания
            waiting_records = self.waiting_repository.get_by_passenger_and_bus(
                passenger.id, bus.id
            )

            for record in waiting_records:
                if record.is_waiting():
                    self.waiting_repository.update_status(record.id, "Confirmed")
                    self.waiting_repository.update_notification(record.id, "Yes")

            return True
        except Exception as e:
            logger.error(f"Ошибка при подтверждении брони из листа ожидания: {str(e)}")
            return False
