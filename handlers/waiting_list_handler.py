"""
Обработчик для работы с листом ожидания
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import MESSAGES
from handlers.base_handler import BaseHandler
from services.booking_service import BookingService
from services.bus_service import BusService
from services.waiting_list_service import WaitingListService
from utils.keyboards import create_back_keyboard, create_waiting_list_keyboard

logger = logging.getLogger(__name__)


class WaitingListHandler(BaseHandler):
    """Обработчик для работы с листом ожидания"""

    def __init__(self):
        super().__init__()
        self.booking_service = BookingService()
        self.bus_service = BusService()
        self.waiting_service = WaitingListService()

    async def show_waiting_list_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Показывает меню листа ожидания"""
        try:
            query = update.callback_query
            await query.answer()

            # Получаем пассажира
            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            # Получаем все автобусы
            buses = self.bus_service.get_all_buses()

            if not buses:
                await query.edit_message_text(
                    "Нет автобусов для очереди.", reply_markup=create_back_keyboard()
                )
                return

            # Создаем клавиатуру
            keyboard = create_waiting_list_keyboard(buses)

            await query.edit_message_text(
                "Выберите автобус для постановки в очередь:", reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Ошибка в show_waiting_list_menu: {str(e)}")
            await self.send_error_message(update, "Ошибка при получении автобусов")

    async def add_to_waiting_list(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, bus_id: int
    ):
        """Добавляет пользователя в лист ожидания"""
        try:
            query = update.callback_query
            await query.answer()

            # Получаем пассажира
            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            # Получаем автобус
            bus = self.bus_service.get_bus_by_id(bus_id)
            if not bus:
                await query.edit_message_text(
                    "Автобус не найден.", reply_markup=create_back_keyboard()
                )
                return

            # Добавляем в лист ожидания
            success = self.booking_service.add_to_waiting_list(passenger, bus)

            if success:
                await query.edit_message_text(
                    MESSAGES["waiting_list_added"], reply_markup=create_back_keyboard()
                )
            else:
                await query.edit_message_text(
                    MESSAGES["already_in_waiting"], reply_markup=create_back_keyboard()
                )

        except Exception as e:
            logger.error(f"Ошибка в add_to_waiting_list: {str(e)}")
            await self.send_error_message(
                update, "Ошибка при добавлении в лист ожидания"
            )

    async def confirm_waiting_booking(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Подтверждает бронирование из листа ожидания"""
        try:
            # Получаем пассажира
            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            # Получаем все автобусы для проверки
            buses = self.bus_service.get_all_buses()

            # Ищем автобус, на который можно подтвердить бронь
            for bus in buses:
                success = self.waiting_service.confirm_waiting_booking(passenger, bus)
                if success:
                    await update.message.reply_text("Бронь подтверждена. Удачи!")
                    return

            await update.message.reply_text("Нет ожидающих для подтверждения.")

        except Exception as e:
            logger.error(f"Ошибка в confirm_waiting_booking: {str(e)}")
            await self.send_error_message(update, "Ошибка при подтверждении брони")
