"""
Обработчик для просмотра бронирований
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import MESSAGES
from handlers.base_handler import BaseHandler
from services.booking_service import BookingService
from services.bus_service import BusService
from utils.keyboards import create_back_keyboard, create_booking_cancel_keyboard
from utils.messages import format_user_bookings_message

logger = logging.getLogger(__name__)


class ViewBookingHandler(BaseHandler):
    """Обработчик для просмотра бронирований"""

    def __init__(self):
        super().__init__()
        self.booking_service = BookingService()
        self.bus_service = BusService()

    async def view_bookings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает бронирования пользователя"""
        try:
            query = update.callback_query
            await query.answer()

            # Получаем пассажира
            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            # Получаем бронирования пользователя
            reservations = self.booking_service.get_user_bookings(passenger)
            buses = self.bus_service.get_all_buses()

            # Формируем сообщение
            message = format_user_bookings_message(reservations, buses)

            # Создаем клавиатуру для отмены бронирований
            keyboard = create_back_keyboard()

            await query.edit_message_text(message, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Ошибка в view_bookings: {str(e)}")
            await self.send_error_message(update, "Ошибка при получении бронирований")

    async def cancel_booking_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Показывает меню отмены бронирований"""
        try:
            query = update.callback_query
            await query.answer()

            # Получаем пассажира
            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            # Получаем бронирования пользователя
            reservations = self.booking_service.get_user_bookings(passenger)
            buses = self.bus_service.get_all_buses()

            if not reservations:
                await query.edit_message_text(
                    MESSAGES["no_bookings_to_cancel"],
                    reply_markup=create_back_keyboard(),
                )
                return

            # Создаем клавиатуру для отмены бронирований
            keyboard = create_booking_cancel_keyboard(reservations, buses)

            await query.edit_message_text(
                "Выберите запись для отмены:", reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Ошибка в cancel_booking_menu: {str(e)}")
            await self.send_error_message(update, "Ошибка при получении бронирований")

    async def cancel_booking(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, reservation_id: int
    ):
        """Отменяет бронирование"""
        try:
            query = update.callback_query
            await query.answer()

            # Получаем пассажира
            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            # Отменяем бронирование
            success = self.booking_service.cancel_booking(reservation_id, passenger)

            if success:
                await query.edit_message_text(
                    MESSAGES["booking_cancelled"], reply_markup=create_back_keyboard()
                )
            else:
                await query.edit_message_text(
                    "Запись не найдена или вам не принадлежит.",
                    reply_markup=create_back_keyboard(),
                )

        except Exception as e:
            logger.error(f"Ошибка в cancel_booking: {str(e)}")
            await self.send_error_message(update, "Ошибка при отмене бронирования")
