"""
Обработчик для экспорта данных
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import MESSAGES
from handlers.base_handler import BaseHandler
from services.export_service import ExportService
from utils.keyboards import create_back_keyboard

logger = logging.getLogger(__name__)


class ExportHandler(BaseHandler):
    """Обработчик для экспорта данных"""

    def __init__(self):
        super().__init__()
        self.export_service = ExportService()

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
