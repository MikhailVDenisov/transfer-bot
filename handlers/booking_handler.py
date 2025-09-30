"""
Обработчики для работы с бронированиями
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config.settings import MESSAGES
from handlers.base_handler import BaseHandler
from services.booking_service import BookingService
from services.bus_service import BusService
from services.passenger_service import PassengerService
from utils.keyboards import (
    create_back_keyboard,
    create_buses_keyboard,
    create_directions_keyboard,
)
from utils.messages import format_booking_success_message, format_buses_list_message

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
FIO, BUS_ID = range(2)


class BookingHandler(BaseHandler):
    """Обработчик для работы с бронированиями"""

    def __init__(self):
        super().__init__()
        self.bus_service = BusService()
        self.booking_service = BookingService()
        self.passenger_service = PassengerService()

    async def show_directions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает доступные направления"""
        try:
            query = update.callback_query
            await query.answer()

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

            # Формируем сообщение
            message = format_buses_list_message(buses, all_reservations, direction)

            # Создаем клавиатуру
            keyboard = create_buses_keyboard(buses, all_reservations)

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

    async def request_fio(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, bus_id: int = None
    ):
        """Запрашивает ФИО у пользователя"""
        try:
            query = update.callback_query
            context.user_data["bus_id"] = bus_id

            if query:
                await query.answer()
                await query.edit_message_text(MESSAGES["fio_request"])
            else:
                await update.message.reply_text(MESSAGES["fio_request"])

            return FIO

        except Exception as e:
            logger.error(f"Ошибка в request_fio: {str(e)}")
            await self.send_error_message(update, "Ошибка при запросе ФИО")
            return ConversationHandler.END

    async def handle_fio_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Обрабатывает ввод ФИО пользователем"""
        try:
            fio = update.message.text.strip()

            # Валидируем ФИО
            from utils.validators import validate_fio

            is_valid, error_msg = validate_fio(fio)

            if not is_valid:
                await update.message.reply_text(f"❌ {error_msg}")
                return FIO

            # Сохраняем ФИО
            username = update.message.from_user.username
            success = self.passenger_service.update_fio(username, fio)

            if success:
                # Продолжаем процесс регистрации, если был выбран автобус
                bus_id = context.user_data.pop("bus_id", None)
                if bus_id:
                    await self.confirm_booking_from_fio(update, context, bus_id, fio)
                else:
                    await update.message.reply_text(
                        MESSAGES["fio_saved"].format(fio=fio)
                    )
                    # Возвращаемся в главное меню
                    from handlers.start_handler import StartHandler

                    start_handler = StartHandler()
                    await start_handler.handle(update, context)
            else:
                await update.message.reply_text(
                    "❌ Произошла ошибка при сохранении ФИО. Попробуйте позже."
                )

            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Ошибка в handle_fio_input: {str(e)}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке ФИО. Попробуйте позже."
            )
            return ConversationHandler.END

    async def confirm_booking_from_fio(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, bus_id: int, fio: str
    ):
        """Продолжает процесс подтверждения брони после ввода ФИО"""
        try:
            # Получаем пассажира
            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return

            # Получаем автобус
            bus = self.bus_service.get_bus_by_id(bus_id)
            if not bus:
                await update.message.reply_text("Автобус не найден.")
                return

            # Создаем бронирование
            success = self.booking_service.create_booking(passenger, bus)

            if success:
                message = format_booking_success_message(bus)
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("Ошибка при создании бронирования.")

        except Exception as e:
            logger.error(f"Ошибка в confirm_booking_from_fio: {str(e)}")
            await update.message.reply_text("Ошибка при создании бронирования.")

    async def cancel_fio_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Отменяет ввод ФИО"""
        await update.message.reply_text(
            "Ввод ФИО отменен. Вы можете попробовать снова через главное меню."
        )
        context.user_data.pop("bus_id", None)
        return ConversationHandler.END
