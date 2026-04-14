import logging
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.base_handler import BaseHandler
from services.broadcast_service import BroadcastService
from services.bus_service import BusService
from utils.const import (
    BROADCAST_CHIEF_CANCEL,
    BROADCAST_CHIEF_SELECT_BUS,
    BROADCAST_CHIEF_SEND,
)
from utils.keyboards import (
    create_back_keyboard,
    create_cancel_broadcast_chief_keyboard,
    create_chief_buses_keyboard,
)

logger = logging.getLogger(__name__)


class BroadcastChiefHandler(BaseHandler):
    """Обработчик рассылки от шефа"""

    def __init__(self):
        super().__init__()
        self.bus_service = BusService()
        self.broadcast_service = BroadcastService()

    async def broadcast_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        try:
            passenger = await self.get_or_create_passenger(update)

            # Проверяем права
            if not passenger or not passenger.is_chief():
                await self._broadcast_error(update, context, "Доступ запрещен")
                return

            query = update.callback_query
            await query.answer()

            buses = self.bus_service.get_buses_by_chief(passenger.id)

            if len(buses) < 1:
                await self._broadcast_error(
                    update, context, "На вас не назначено ни одного автобуса"
                )
                return

            keyboard = create_chief_buses_keyboard(buses)
            await query.edit_message_text("Выберите автобус:", reply_markup=keyboard)

        except Exception:
            logger.exception("Ошибка в broadcast_command")
            await self._broadcast_error(update, context, "Ошибка запуска рассылки")

    async def prepare_broadcast(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        try:
            passenger = await self.get_or_create_passenger(update)

            query = update.callback_query
            await query.answer()

            # Проверяем права
            if not passenger or not passenger.is_chief():
                await self._broadcast_error(update, context, "Доступ запрещен")
                return

            bus_id = self._parse_bus_id(query.data)
            if bus_id is None:
                await self._broadcast_error(
                    update, context, "Некорректный выбор автобуса"
                )
                return

            chief_buses = self.bus_service.get_buses_by_chief(passenger.id)
            if not any(b.id == bus_id for b in chief_buses):
                await self._broadcast_error(
                    update, context, "Этот автобус вам не назначен"
                )
                return

            context.user_data["bus_id"] = bus_id

            # Устанавливаем признак, что пользователь в режиме рассылки
            context.user_data["broadcast_mode"] = True

            # Обнуляем сообщение для рассылки
            context.user_data["broadcast_message"] = None

            await query.edit_message_text(
                "Отправь сообщение для пассажиров\n"
                "Это может быть текст, фото, видео, документ и т.д.\n"
                "После этого я покажу предпросмотр и кнопки подтверждения",
                reply_markup=create_cancel_broadcast_chief_keyboard(),
            )

        except Exception:
            logger.exception("Ошибка в prepare_broadcast")
            await self._broadcast_error(update, context, "Ошибка подготовки рассылки")

    async def handle_chief_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        try:
            if not context.user_data.get("broadcast_mode"):
                return

            if not update.message:
                await self._broadcast_error(
                    update, context, "Ошибка предпросмотра сообщения"
                )
                return

            passenger = await self.get_or_create_passenger(update)

            # Проверяем права
            if not passenger or not passenger.is_chief():
                await self._broadcast_error(update, context, "Доступ запрещен")
                return

            message = update.message

            # Сохраняем оригинальное сообщение админа:
            context.user_data["broadcast_message"] = {
                "chat_id": update.effective_chat.id,
                "message_id": message.message_id,
            }

            send_cb = f"{BROADCAST_CHIEF_SEND}_{message.message_id}"
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Отправить", callback_data=send_cb),
                        InlineKeyboardButton(
                            "❌ Отмена", callback_data=BROADCAST_CHIEF_CANCEL
                        ),
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
        except Exception:
            logger.exception("Ошибка в handle_chief_message")
            await self._broadcast_error(update, context, "Ошибка создания сообщения")

    async def broadcast_send(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        try:
            passenger = await self.get_or_create_passenger(update)

            query = update.callback_query
            await query.answer()

            # Проверяем права
            if not passenger or not passenger.is_chief():
                await self._broadcast_error(update, context, "Доступ запрещен")
                return

            if not context.user_data.get("broadcast_mode"):
                logger.warning(
                    "broadcast_send: режим рассылки выключен, keys=%s",
                    list(context.user_data.keys()),
                )
                await self._broadcast_error(update, context, "Ошибка рассылки")
                return

            # Получаем message_id для отправки
            message_id_from_callback_data = self._parse_message_id_from_callback_data(
                query.data
            )

            if message_id_from_callback_data is not None:
                source_chat_id = update.effective_chat.id
                source_message_id = message_id_from_callback_data
            else:
                send_prefix = f"{BROADCAST_CHIEF_SEND}_"
                if query.data and query.data.startswith(send_prefix):
                    await self._broadcast_error(
                        update, context, "Устарела или повреждена кнопка отправки"
                    )
                    return

                payload = context.user_data.get("broadcast_message")
                if not payload:
                    await self._broadcast_error(
                        update, context, "Не найдено сообщение для рассылки"
                    )
                    return

                source_chat_id = payload["chat_id"]
                source_message_id = payload["message_id"]

            # Получаем bus_id для отправки
            bus_id = context.user_data.get("bus_id")

            # Получаем пассажиров для рассылки
            passengers_for_broadcast = (
                self.broadcast_service.get_passengers_for_broadcast(
                    bus_id, passenger.id
                )
            )

            if passengers_for_broadcast is None:
                await self._broadcast_error(
                    update, context, "Ошибка получения пассажиров для рассылки"
                )
                return

            if len(passengers_for_broadcast) == 0:
                await self._broadcast_error(
                    update, context, "Не найдено пассажиров для рассылки"
                )
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
            context.user_data.pop("bus_id", None)

            await query.message.reply_text(
                f"Рассылка завершена.\n"
                f"Успешно: {stats.sent}\n"
                f"Ошибок: {stats.failed}\n"
                f"Заблокировали бота: {stats.forbidden}\n",
                reply_markup=create_back_keyboard(),
            )

        except Exception:
            logger.exception("Ошибка в broadcast_send")
            await self._broadcast_error(update, context, "Ошибка рассылки")

    async def broadcast_cancel(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        passenger = await self.get_or_create_passenger(update)

        query = update.callback_query
        await query.answer()

        # Проверяем права
        if not passenger or not passenger.is_chief():
            await self._broadcast_error(update, context, "Доступ запрещен")
            return

        context.user_data.pop("broadcast_mode", False)
        context.user_data.pop("broadcast_message", None)
        context.user_data.pop("bus_id", None)

        query = update.callback_query

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Рассылка отменена.")

    async def _broadcast_error(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, error_message: str
    ) -> None:
        await self.send_error_message(update, error_message)

        context.user_data.pop("broadcast_mode", False)
        context.user_data.pop("broadcast_message", None)
        context.user_data.pop("bus_id", None)

    @staticmethod
    def _parse_bus_id(callback_data: Optional[str]) -> Optional[int]:
        """Извлекает id автобуса из callback_data кнопки выбора автобуса для рассылки шефа."""
        if not callback_data or not callback_data.startswith(
            BROADCAST_CHIEF_SELECT_BUS
        ):
            return None
        suffix = callback_data[len(BROADCAST_CHIEF_SELECT_BUS) :]
        if not suffix or not suffix.isdigit():
            return None
        bus_id = int(suffix)
        if bus_id < 1:
            return None
        return bus_id

    @staticmethod
    def _parse_message_id_from_callback_data(
        callback_data: Optional[str],
    ) -> Optional[int]:
        """Извлекает message_id исходного сообщения из callback_data кнопки «Отправить»."""
        if not callback_data:
            return None
        if callback_data == BROADCAST_CHIEF_SEND:
            return None
        prefix = f"{BROADCAST_CHIEF_SEND}_"
        if not callback_data.startswith(prefix):
            return None
        suffix = callback_data[len(prefix) :]
        if not suffix or not suffix.isdigit():
            return None
        message_id = int(suffix)
        if message_id < 1:
            return None
        return message_id
