"""
Обработчик для экспорта данных
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import MESSAGES
from handlers.base_handler import BaseHandler
from services.bus_service import BusService
from services.export_service import ExportService
from utils.keyboards import (
    create_back_keyboard,
    create_personal_data_export_buses_keyboard,
)

logger = logging.getLogger(__name__)


class ExportHandler(BaseHandler):
    """Обработчик для экспорта данных"""

    def __init__(self):
        super().__init__()
        self.export_service = ExportService()
        self.bus_service = BusService()

    async def show_personal_data_export_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Показывает меню выбора автобусов для выгрузки персональных данных"""
        try:
            query = update.callback_query
            passenger = await self.get_or_create_passenger(update)
            if not passenger or not passenger.is_admin():
                await query.answer("⚠️ Доступ запрещен", show_alert=True)
                return

            buses = self.bus_service.get_all_buses()
            if not buses:
                await query.answer()
                await query.edit_message_text(
                    "Нет автобусов для выгрузки.",
                    reply_markup=create_back_keyboard(),
                )
                return

            context.user_data["personal_data_export_bus_ids"] = []
            await query.answer()
            await query.edit_message_text(
                "Выберите автобусы для выгрузки персональных данных:",
                reply_markup=create_personal_data_export_buses_keyboard(buses, []),
            )

        except Exception as e:
            logger.error(f"Ошибка при открытии меню выгрузки персональных данных: {e}")
            await self.send_error_message(
                update, "Ошибка при открытии меню выгрузки персональных данных"
            )

    async def toggle_personal_data_export_bus(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Переключает выбранный автобус в списке выгрузки"""
        try:
            query = update.callback_query
            passenger = await self.get_or_create_passenger(update)
            if not passenger or not passenger.is_admin():
                await query.answer("⚠️ Доступ запрещен", show_alert=True)
                return

            bus_id = int(query.data.split("_")[-1])
            selected_bus_ids = set(
                context.user_data.get("personal_data_export_bus_ids", [])
            )

            if bus_id in selected_bus_ids:
                selected_bus_ids.remove(bus_id)
            else:
                selected_bus_ids.add(bus_id)

            buses = self.bus_service.get_all_buses()
            context.user_data["personal_data_export_bus_ids"] = sorted(selected_bus_ids)

            await query.answer("Выбор обновлен")
            await query.edit_message_text(
                "Выберите автобусы для выгрузки персональных данных:",
                reply_markup=create_personal_data_export_buses_keyboard(
                    buses, context.user_data["personal_data_export_bus_ids"]
                ),
            )

        except Exception as e:
            logger.error(f"Ошибка при выборе автобуса для выгрузки: {e}")
            await self.send_error_message(update, "Ошибка при выборе автобуса")

    async def export_personal_data(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Выгружает персональные данные по выбранным автобусам"""
        try:
            query = update.callback_query
            passenger = await self.get_or_create_passenger(update)
            if not passenger or not passenger.is_admin():
                await query.answer("⚠️ Доступ запрещен", show_alert=True)
                return

            selected_bus_ids = context.user_data.get("personal_data_export_bus_ids", [])
            if not selected_bus_ids:
                await query.answer("Выберите хотя бы один автобус", show_alert=True)
                return

            await query.answer()
            msg = await query.edit_message_text(
                "🔄 Подготовка выгрузки персональных данных..."
            )

            temp_file = await self.export_service.export_personal_data_to_excel(
                selected_bus_ids
            )

            await msg.edit_text("📤 Отправляем файл...")

            with open(temp_file, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename="personal_data_export.xlsx",
                    caption="✅ Выгрузка персональных данных пассажиров",
                )

            await msg.delete()
            context.user_data.pop("personal_data_export_bus_ids", None)
            self.export_service.cleanup_temp_file(temp_file)

        except Exception as e:
            logger.error(f"Ошибка при выгрузке персональных данных: {e}")
            error_msg = f"❌ Ошибка при выгрузке: {str(e)}"

            if update.callback_query:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)

    async def export_buses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Экспортирует данные об автобусах"""
        try:
            # Проверяем права доступа
            user = update.effective_user
            if not user:
                if update.callback_query:
                    await update.callback_query.answer(
                        "⚠️ Доступ запрещен", show_alert=True
                    )
                return

            # Получаем пассажира и проверяем права
            passenger = await self.get_or_create_passenger(update)
            if not passenger or not passenger.is_admin():
                if update.callback_query:
                    await update.callback_query.answer(
                        "⚠️ Доступ запрещен", show_alert=True
                    )
                return

            # Уведомление о начале процесса
            if update.callback_query:
                await update.callback_query.answer()
                msg = await update.callback_query.edit_message_text(
                    "🔄 Подготовка отчета..."
                )
            else:
                msg = await update.message.reply_text("🔄 Подготовка отчета...")

            # Генерируем Excel файл
            temp_file = await self.export_service.export_buses_to_excel()

            await msg.edit_text("📤 Отправляем файл...")

            # Отправляем файл
            with open(temp_file, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=f"bus_report_{context.bot_data.get('timestamp', 'unknown')}.xlsx",
                    caption="✅ Отчет по автобусам",
                )

            await msg.delete()

            # Удаляем временный файл
            self.export_service.cleanup_temp_file(temp_file)

        except Exception as e:
            logger.error(f"Ошибка при экспорте данных: {str(e)}")
            error_msg = f"❌ Ошибка при выгрузке: {str(e)}"

            if update.callback_query:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
