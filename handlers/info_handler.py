"""
Обработчик для информационных сообщений
"""

import logging

from telegram import InputMediaPhoto, Update
from telegram.ext import ContextTypes

from config.settings import (
    FAQ_TEXT,
    HOW_TO_GET_THERE_INFO,
    ROUTE_TO_HOTEL_IMAGE_URL,
    ROUTE_TO_HOTEL_INFO,
)
from handlers.base_handler import BaseHandler
from utils.keyboards import create_back_keyboard

logger = logging.getLogger(__name__)


class InfoHandler(BaseHandler):
    """Обработчик для информационных сообщений"""

    async def show_how_to_get_there(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Показывает информацию о том, как добраться"""
        try:
            query = update.callback_query
            await query.answer()

            keyboard = create_back_keyboard()
            await query.edit_message_text(
                HOW_TO_GET_THERE_INFO, reply_markup=keyboard, parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Ошибка в show_how_to_get_there: {str(e)}")
            await self.send_error_message(update, "Ошибка при получении информации")

    async def show_faq(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает FAQ"""
        try:
            query = update.callback_query
            await query.answer()

            keyboard = create_back_keyboard()
            await query.edit_message_text(
                FAQ_TEXT, parse_mode="Markdown", reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Ошибка в show_faq: {str(e)}")
            await self.send_error_message(update, "Ошибка при получении FAQ")

    async def show_route_to_hotel(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Показывает маршрут до отеля"""
        try:
            query = update.callback_query
            await query.answer()

            keyboard = create_back_keyboard()

            await query.edit_message_media(
                media=InputMediaPhoto(
                    media=ROUTE_TO_HOTEL_IMAGE_URL,
                    caption=ROUTE_TO_HOTEL_INFO,
                    parse_mode="Markdown",
                ),
                reply_markup=keyboard,
            )

        except Exception as e:
            logger.error(f"Ошибка в show_route_to_hotel: {str(e)}")
            await self.send_error_message(update, "Ошибка при получении маршрута")
