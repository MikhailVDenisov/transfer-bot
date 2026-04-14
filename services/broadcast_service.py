import asyncio
import logging
import sqlite3
from typing import List, NamedTuple

from telegram import Bot
from telegram.error import BadRequest, Forbidden

from database.repositories import PassengerRepository
from models.entities import Passenger

logger = logging.getLogger(__name__)


class BroadcastStats(NamedTuple):
    """Итоги рассылки: успешно, прочие ошибки, пользователь заблокировал бота."""

    sent: int
    failed: int
    forbidden: int


class BroadcastService:
    """Сервис рассылки"""

    def __init__(self):
        self.passenger_repository = PassengerRepository()

    def get_passengers_for_broadcast(
        self, bus_id: int, chief_id: int
    ) -> List[Passenger] | None:
        try:
            passengers = self.passenger_repository.get_by_bus(bus_id)
            result = list(filter(lambda p: p.id != chief_id, passengers))

            return result

        except sqlite3.Error:
            logger.error(
                "Ошибка БД при получении списка пассажиров для рассылки",
                exc_info=True,
            )
            return None

    async def send_broadcast(
        self, bot: Bot, passengers: List[Passenger], source_chat_id, source_message_id
    ) -> BroadcastStats:

        sent_count = 0
        failed_count = 0
        forbidden_count = 0

        for passenger in list(passengers):
            try:
                await bot.copy_message(
                    chat_id=passenger.chat_id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                )
                sent_count += 1

                # Небольшая пауза помогает не упереться в rate limits
                await asyncio.sleep(0.05)

            except Forbidden:
                forbidden_count += 1

            except BadRequest:
                failed_count += 1

            except Exception:
                failed_count += 1

        return BroadcastStats(sent_count, failed_count, forbidden_count)
