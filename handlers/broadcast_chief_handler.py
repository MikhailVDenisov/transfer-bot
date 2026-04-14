import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from handlers.base_handler import BaseHandler
from handlers.start_handler import StartHandler
from services.export_service import ExportService
from services.bus_service import BusService
from services.broadcast_service import BroadcastService

from utils.const import (
    BROADCAST_CHIEF_SEND,
    BROADCAST_CHIEF_CANCEL
)
from utils.keyboards import (
    create_chief_buses_keyboard,
    cancel_broadcast_chief_keyboard, create_back_keyboard,
)

logger = logging.getLogger(__name__)



class BroadcastChiefHandler(BaseHandler):
    """Обработчик рассылки от шефа"""

    def __init__(self):
        super().__init__()
        self.export_service = ExportService()
        self.bus_service = BusService()
        self.broadcast_service = BroadcastService()
        self.start_handler = StartHandler()


    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            passenger = await self.get_or_create_passenger(update)

            # Проверяем права
            if not passenger or not passenger.is_chief():
                await self.broadcast_error(update, context, "Доступ запрещен")
                return

            query = update.callback_query
            await query.answer()

            buses = self.bus_service.get_buses_by_chief(passenger.id)

            if len(buses) < 1:
                await self.broadcast_error(update, context, "На вас не назначено ни одного автобуса")
                return

            keyboard = create_chief_buses_keyboard(buses)
            await query.edit_message_text(
                "Выберите автобус:", reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Ошибка в broadcast_command: {str(e)}")
            await self.broadcast_error(update, context, "Ошибка запуска рассылки")


    async def prepare_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            passenger = await self.get_or_create_passenger(update)

            # Проверяем права
            if not passenger or not passenger.is_chief():
                await self.broadcast_error(update, context, "Доступ запрещен")
                return

            query = update.callback_query
            await query.answer()

            # Получаем bus_id
            data = query.data
            context.user_data["bus_id"] =  int(data.split("_", 4)[4])

            #Устанавливаем признак, что пользователь в режиме рассылки
            context.user_data["broadcast_mode"] = True

            # Обнуляем сообщение для рассылки
            context.user_data["broadcast_message"] = None

            await query.edit_message_text(
                "Отправь сообщение для пассажиров\n"
                "Это может быть текст, фото, видео, документ и т.д.\n"
                "После этого я покажу предпросмотр и кнопки подтверждения",
                reply_markup=cancel_broadcast_chief_keyboard(),
            )

        except Exception as e:
            logger.error(f"Ошибка в prepare_broadcast: {str(e)}")
            await self.broadcast_error(update, context, "Ошибка подготовки рассылки")


    async def handle_chief_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            passenger = await self.get_or_create_passenger(update)

            # Проверяем права
            if not passenger or not passenger.is_chief():
                await self.broadcast_error(update, context, "Доступ запрещен")
                return

            if not context.user_data.get("broadcast_mode"):
                logger.warning(f"handle_chief_message broadcast_mode: {context.user_data.get("broadcast_mode")}")
                await self.broadcast_error(update, context, "Ошибка при создании сообщения")
                return

            message = update.message

            # Сохраняем оригинальное сообщение админа:
            context.user_data["broadcast_message"] = {
                "chat_id": update.effective_chat.id,
                "message_id": message.message_id,
            }

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Отправить", callback_data=BROADCAST_CHIEF_SEND),
                        InlineKeyboardButton("❌ Отмена", callback_data=BROADCAST_CHIEF_CANCEL),
                    ]
                ]
            )

            await update.message.reply_text("Предпросмотр сообщения:")

            # Показываем что будет отправлено пассажирам
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=update.effective_chat.id,
                message_id=message.message_id,
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.error(f"Ошибка в handle_chief_message: {str(e)}")
            await self.send_error_message(update, "Ошибка создания сообщения")


    async def broadcast_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            passenger = await self.get_or_create_passenger(update)

            # Проверяем права
            if not passenger or not passenger.is_chief():
                await self.broadcast_error(update, context, "Доступ запрещен")
                return

            if not context.user_data.get("broadcast_mode"):
                logger.warning(f"broadcast_send broadcast_mode: {context.user_data.get("broadcast_mode")}")
                await self.broadcast_error(update, context,"Ошибка рассылки")
                return

            query = update.callback_query
            await query.answer()

            # Получаем сообщение для рассылки
            payload = context.user_data.get("broadcast_message")

            if not payload:
                await self.broadcast_error(update, context,"Не найдено сообщение для рассылки")
                return

            source_chat_id = payload["chat_id"]
            source_message_id = payload["message_id"]

            bus_id = context.user_data.get("bus_id")

            # Получаем пассажиров для рассылки
            passengers_for_broadcast = self.broadcast_service.get_passengers_for_broadcast(bus_id, passenger.id)

            if not passengers_for_broadcast or len(passengers_for_broadcast) == 0:
                await self.broadcast_error(update, context,"Не найдено пассажиров для рассылки")
                return

            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("Начинаю рассылку...")

            # Запускаем рассылку
            stats = await self.broadcast_service.send_broadcast(
                context.bot,
                passengers_for_broadcast,
                source_chat_id,
                source_message_id,
            )

            context.user_data["broadcast_mode"] = False
            context.user_data.pop("broadcast_message", None)
            context.user_data.pop("chat_id", None)

            await query.message.reply_text(
                f"Рассылка завершена.\n"
                f"Успешно: {stats.sent}\n"
                f"Ошибок: {stats.failed}\n"
                f"Заблокировали бота: {stats.forbidden}\n"
            )
        except Exception as e:
            logger.error(f"Ошибка в broadcast_send: {str(e)}")
            await self.send_error_message(update, "Ошибка рассылки")


    async def broadcast_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        passenger = await self.get_or_create_passenger(update)
        # Проверяем права
        if not passenger or not passenger.is_chief():
            await self.broadcast_error(update, context,"Доступ запрещен")
            return

        query = update.callback_query
        await query.answer()

        context.user_data.pop("broadcast_mode", False)
        context.user_data.pop("broadcast_message",None)
        context.user_data.pop("bus_id", None)


    async def broadcast_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, error_message: str) -> None:
        await self.send_error_message(update, error_message)

        context.user_data.pop("broadcast_mode", False)
        context.user_data.pop("broadcast_message", None)
        context.user_data.pop("bus_id", None)