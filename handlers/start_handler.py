"""
Обработчик команды /start
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import MESSAGES
from handlers.base_handler import BaseHandler
from utils.keyboards import create_main_menu_keyboard

logger = logging.getLogger(__name__)


class StartHandler(BaseHandler):
    """Обработчик команды /start"""

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает команду /start"""
        try:
            # Получаем или создаем пассажира
            passenger = await self.get_or_create_passenger(update)

            if not passenger:
                return

            # Проверяем, является ли пользователь администратором
            is_admin = passenger.is_admin()

            # Проверяем, является ли пользователь шефом
            is_chief = passenger.is_chief()

            # Создаем клавиатуру
            keyboard = create_main_menu_keyboard(is_admin, is_chief)

            # Отправляем приветственное сообщение
            if update.message:
                await update.message.reply_text(
                    MESSAGES["welcome"], reply_markup=keyboard
                )
            else:
                await update.callback_query.message.reply_text(
                    MESSAGES["welcome"], reply_markup=keyboard
                )

        except Exception as e:
            logger.error(f"Ошибка в StartHandler: {str(e)}")
            await self.send_error_message(update, "Произошла ошибка при запуске бота")
