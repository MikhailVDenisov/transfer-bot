"""
Обработчики для работы с бронированиями
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import MESSAGES
from handlers.base_handler import BaseHandler
from services.booking_service import BookingService
from services.bus_service import BusService
from utils.keyboards import (
    create_back_keyboard,
    create_buses_keyboard,
    create_directions_keyboard,
    create_personal_data_prompt_keyboard,
)
from utils.messages import (
    format_available_seats_summary,
    format_booking_success_message,
    format_buses_list_message,
)

logger = logging.getLogger(__name__)


class BookingHandler(BaseHandler):
    """Обработчик для работы с бронированиями"""

    def __init__(self):
        super().__init__()
        self.bus_service = BusService()
        self.booking_service = BookingService()

    @staticmethod
    def _get_manual_reserved_counts_for_passenger(buses, passenger) -> dict:
        """Возвращает ручные резервации по автобусам с учетом текущего пассажира."""
        from database.repositories import ManualReservationRepository

        manual_repo = ManualReservationRepository()
        bus_ids = [bus.id for bus in buses if bus.id is not None]
        manual_reserved_by_bus = manual_repo.get_unbooked_counts_by_bus(bus_ids)

        username = passenger.telegram_username
        if not username:
            return manual_reserved_by_bus

        for bus in buses:
            if bus.id is None:
                continue
            if manual_repo.has_unbooked_by_username_and_bus(username, bus.id):
                current_count = manual_reserved_by_bus.get(bus.id, 0)
                manual_reserved_by_bus[bus.id] = max(0, current_count - 1)

        return manual_reserved_by_bus

    def _build_personal_data_required_message(self) -> str:
        """Собирает сообщение о необходимости заполнить персональные данные со сводкой мест."""
        active_buses = self.bus_service.get_active_buses()
        available_seats_by_bus = {}
        for bus in active_buses:
            if bus.id is None:
                continue
            availability = self.bus_service.get_bus_availability_info(bus)
            available_seats_by_bus[bus.id] = availability["free"]

        seats_summary = format_available_seats_summary(
            active_buses, available_seats_by_bus
        )
        return f"{seats_summary}\n\n{MESSAGES['personal_data_required']}"

    async def show_directions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает доступные направления"""
        try:
            query = update.callback_query
            if query and not context.user_data.pop("skip_callback_answer", False):
                await query.answer()

            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            if not passenger.has_confirmed_personal_data():
                await query.edit_message_text(
                    self._build_personal_data_required_message(),
                    reply_markup=create_personal_data_prompt_keyboard(
                        "personal_data_from_booking"
                    ),
                )
                return

            directions = self.bus_service.get_available_directions()

            if not directions:
                await query.edit_message_text(
                    MESSAGES["no_available_directions"],
                    reply_markup=create_back_keyboard(),
                )
                return

            keyboard = create_directions_keyboard(directions)
            await query.edit_message_text(
                "Выберите направление:", reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Ошибка в show_directions: {str(e)}")
            await self.send_error_message(update, "Ошибка при получении направлений")

    async def show_buses_for_direction(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, direction: str
    ):
        """Показывает автобусы для выбранного направления"""
        try:
            query = update.callback_query
            await query.answer()

            # Получаем пассажира
            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            # Получаем автобусы для направления
            buses = self.bus_service.get_buses_for_direction(direction)

            if not buses:
                await query.edit_message_text(
                    MESSAGES["no_available_buses"].format(direction=direction),
                    reply_markup=create_back_keyboard(),
                )
                return

            # Проверяем, есть ли уже бронь на это направление
            user_bookings = self.booking_service.get_user_bookings(passenger)
            existing_res = [r for r in user_bookings if r.direction == direction]

            if existing_res:
                await query.edit_message_text(
                    MESSAGES["already_registered"], reply_markup=create_back_keyboard()
                )
                return

            # Получаем все бронирования для подсчета свободных мест
            from database.repositories import ReservationRepository

            reservation_repo = ReservationRepository()
            all_reservations = reservation_repo.get_all()
            manual_reserved_by_bus = self._get_manual_reserved_counts_for_passenger(
                buses, passenger
            )

            # Формируем сообщение
            message = format_buses_list_message(
                buses,
                all_reservations,
                direction,
                manual_reserved_by_bus=manual_reserved_by_bus,
            )

            # Создаем клавиатуру
            keyboard = create_buses_keyboard(
                buses, all_reservations, manual_reserved_by_bus=manual_reserved_by_bus
            )

            await query.edit_message_text(message, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Ошибка в show_buses_for_direction: {str(e)}")
            await self.send_error_message(update, "Ошибка при получении автобусов")

    async def confirm_booking(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, bus_id: int
    ):
        """Подтверждает бронирование"""
        try:
            query = update.callback_query
            await query.answer()

            # Получаем пассажира
            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            if not passenger.has_confirmed_personal_data():
                await query.edit_message_text(
                    self._build_personal_data_required_message(),
                    reply_markup=create_personal_data_prompt_keyboard(
                        "personal_data_from_booking"
                    ),
                )
                return

            # Получаем автобус
            bus = self.bus_service.get_bus_by_id(bus_id)
            if not bus:
                await query.edit_message_text(
                    "Автобус не найден.", reply_markup=create_back_keyboard()
                )
                return

            # Проверяем, может ли пассажир забронировать автобус
            can_book, error_msg = self.booking_service.can_book_bus(passenger, bus)

            if not can_book:
                await query.edit_message_text(
                    error_msg, reply_markup=create_back_keyboard()
                )
                return

            # Создаем бронирование
            success = self.booking_service.create_booking(passenger, bus)

            if success:
                message = format_booking_success_message(bus)
                await query.edit_message_text(
                    message, reply_markup=create_back_keyboard()
                )
            else:
                await query.edit_message_text(
                    "Ошибка при создании бронирования.",
                    reply_markup=create_back_keyboard(),
                )

        except Exception as e:
            logger.error(f"Ошибка в confirm_booking: {str(e)}")
            await self.send_error_message(
                update, "Ошибка при подтверждении бронирования"
            )
