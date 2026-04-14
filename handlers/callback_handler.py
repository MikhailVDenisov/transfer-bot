"""
Обработчик callback запросов
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.booking_handler import BookingHandler
from handlers.export_handler import ExportHandler
from handlers.info_handler import InfoHandler
from handlers.start_handler import StartHandler
from handlers.view_booking_handler import ViewBookingHandler
from handlers.waiting_list_handler import WaitingListHandler
from handlers.broadcast_chief_handler import (
    BroadcastChiefHandler,
)
from utils.const import (
    BROADCAST_CHIEF_COMMAND,
    BROADCAST_CHIEF_SEND,
    BROADCAST_CHIEF_CANCEL, BROADCAST_CHIEF_SELECT_BUS
)

logger = logging.getLogger(__name__)


class CallbackHandler:
    """Обработчик callback запросов"""

    def __init__(self):
        self.start_handler = StartHandler()
        self.booking_handler = BookingHandler()
        self.view_booking_handler = ViewBookingHandler()
        self.waiting_list_handler = WaitingListHandler()
        self.info_handler = InfoHandler()
        self.export_handler = ExportHandler()
        self.broadcast_chief_handler = BroadcastChiefHandler()

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Обрабатывает callback запросы"""
        try:
            query = update.callback_query
            await query.answer()

            callback_data = query.data

            if callback_data == "book_bus":
                await self.booking_handler.show_directions(update, context)

            elif callback_data == "view_booking":
                await self.view_booking_handler.view_bookings(update, context)

            elif callback_data == "cancel_booking":
                await self.view_booking_handler.cancel_booking_menu(update, context)

            elif callback_data.startswith("select_direction_"):
                direction = callback_data.split("_", 2)[2]
                await self.booking_handler.show_buses_for_direction(
                    update, context, direction
                )

            elif callback_data.startswith("select_bus_"):
                bus_id = int(callback_data.split("_")[2])
                await self.booking_handler.confirm_booking(update, context, bus_id)

            elif callback_data.startswith("cancel_reservation_"):
                reservation_id = int(callback_data.split("_")[2])
                await self.view_booking_handler.cancel_booking(
                    update, context, reservation_id
                )

            elif callback_data == "how_to_get_there":
                await self.info_handler.show_how_to_get_there(update, context)

            elif callback_data == "route_to_hotel":
                await self.info_handler.show_route_to_hotel(update, context)

            elif callback_data == "join_waiting_list":
                await self.waiting_list_handler.show_waiting_list_menu(update, context)

            elif callback_data == "waiting_list_back":
                await self.start_handler.handle(update, context)

            elif callback_data.startswith("set_waiting_bus_"):
                bus_id = int(callback_data.split("_", 3)[3])
                await self.waiting_list_handler.add_to_waiting_list(
                    update, context, bus_id
                )

            elif callback_data == "render_faq":
                await self.info_handler.show_faq(update, context)

            elif callback_data == "export_buses":
                await self.export_handler.export_buses(update, context)

            elif callback_data == BROADCAST_CHIEF_COMMAND:
                await self.broadcast_chief_handler.broadcast_command(update,context)

            elif callback_data.startswith(BROADCAST_CHIEF_SELECT_BUS):
                await self.broadcast_chief_handler.prepare_broadcast(
                    update, context
                )

            elif callback_data == BROADCAST_CHIEF_SEND or callback_data.startswith(
                f"{BROADCAST_CHIEF_SEND}_"
            ):
                await self.broadcast_chief_handler.broadcast_send(update, context)

            elif callback_data == BROADCAST_CHIEF_CANCEL:
                await self.broadcast_chief_handler.broadcast_cancel(update, context)
                await self.start_handler.handle(update, context)

            elif callback_data == "back_to_menu":
                await self.start_handler.handle(update, context)

            else:
                logger.warning(f"Неизвестный callback: {callback_data}")
                await query.edit_message_text("Неизвестная команда.")

        except Exception as e:
            logger.error(f"Ошибка в CallbackHandler: {str(e)}")
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "Произошла ошибка при обработке запроса."
                )
