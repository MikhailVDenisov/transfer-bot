"""
Базовый класс для обработчиков
"""

import logging
from abc import ABC

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import MESSAGES
from services.passenger_service import PassengerService
from utils.keyboards import create_back_keyboard

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Базовый класс для всех обработчиков"""

    def __init__(self):
        self.passenger_service = PassengerService()

    async def get_user_info(self, update: Update) -> tuple:
        """
        Получает информацию о пользователе из update

        Returns:
            tuple: (chat_id, username)
        """
        chat_id = None
        username = None

        if update.message:
            chat_id = update.message.chat_id
            username = update.message.from_user.username
        elif update.callback_query:
            chat_id = update.callback_query.message.chat_id
            username = update.callback_query.from_user.username

        return chat_id, username

    async def get_or_create_passenger(self, update: Update):
        """Получает или создает пассажира"""
        chat_id, username = await self.get_user_info(update)

        if not username:
            await self.send_error_message(update, "Username не найден")
            return None

        passenger, created = self.passenger_service.get_or_create_passenger(
            username, chat_id
        )
        return passenger

    async def send_error_message(self, update: Update, message: str):
        """Отправляет сообщение об ошибке"""
        keyboard = create_back_keyboard()

        if update.message:
            await update.message.reply_text(f"❌ {message}", reply_markup=keyboard)
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                f"❌ {message}", reply_markup=keyboard
            )

    async def send_success_message(self, update: Update, message: str):
        """Отправляет сообщение об успехе"""
        keyboard = create_back_keyboard()

        if update.message:
            await update.message.reply_text(f"✅ {message}", reply_markup=keyboard)
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                f"✅ {message}", reply_markup=keyboard
            )

    async def check_user_exists(self, update: Update) -> bool:
        """Проверяет, существует ли пользователь в системе"""
        passenger = await self.get_or_create_passenger(update)

        if not passenger:
            await self.send_error_message(update, MESSAGES["user_not_found"])
            return False

        return True
