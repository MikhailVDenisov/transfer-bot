"""
Главный файл приложения трансфер-бота
Отрефакторенная версия с разделением на модули
"""

import asyncio
import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config.settings import TELEGRAM_TOKEN, WAITING_LIST_CHECK_INTERVAL
from database.init_db import init_database
from handlers.booking_handler import BookingHandler
from handlers.callback_handler import CallbackHandler
from handlers.start_handler import StartHandler
from services.waiting_list_service import WaitingListService

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
FIO, BUS_ID = range(2)


class TransferBot:
    """Основной класс бота"""

    def __init__(self):
        self.application = None
        self.start_handler = StartHandler()
        self.callback_handler = CallbackHandler()
        self.booking_handler = BookingHandler()
        self.waiting_list_service = WaitingListService()

    async def post_init(self, application: Application):
        """Инициализация после создания приложения"""
        # Запускаем периодическую обработку листа ожидания
        asyncio.create_task(self.periodic_waiting_list_check(application))
        logger.info("Бот инициализирован")

    async def periodic_waiting_list_check(self, application: Application):
        """Периодическая проверка листа ожидания"""
        while True:
            try:
                self.waiting_list_service.process_waiting_list(application)
            except Exception as e:
                logger.error(f"Ошибка в периодической проверке листа ожидания: {e}")

            await asyncio.sleep(WAITING_LIST_CHECK_INTERVAL)

    def setup_handlers(self):
        """Настраивает обработчики команд"""
        # Обработчик команды /start
        self.application.add_handler(CommandHandler("start", self.start_handler.handle))

        # Обработчик callback запросов
        self.application.add_handler(
            CallbackQueryHandler(self.callback_handler.handle_callback)
        )

        # Обработчик команды /confirm для подтверждения брони из листа ожидания
        self.application.add_handler(
            CommandHandler("confirm", self.confirm_waiting_booking)
        )

        # Обработчик команды /wait для добавления в лист ожидания
        self.application.add_handler(CommandHandler("wait", self.add_to_waiting_list))

        # ConversationHandler для ввода ФИО
        fio_conversation = ConversationHandler(
            entry_points=[],  # Входные точки будут добавлены в callback_handler
            states={
                FIO: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.booking_handler.handle_fio_input,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", self.booking_handler.cancel_fio_input)],
        )
        self.application.add_handler(fio_conversation)

        # Обработчик сообщения шефа в режиме рассылки
        self.application.add_handler(MessageHandler(
            filters.ALL & ~filters.COMMAND,
            self.callback_handler.broadcast_chief_handler.handle_chief_message
        ))

        logger.info("Обработчики настроены")

    async def confirm_waiting_booking(self, update, context):
        """Обрабатывает команду /confirm"""
        try:
            # Получаем пассажира
            passenger = await self.start_handler.get_or_create_passenger(update)
            if not passenger:
                return

            # Получаем все автобусы для проверки
            from services.bus_service import BusService

            bus_service = BusService()
            buses = bus_service.get_all_buses()

            # Ищем автобус, на который можно подтвердить бронь
            for bus in buses:
                success = self.waiting_list_service.confirm_waiting_booking(
                    passenger, bus
                )
                if success:
                    await update.message.reply_text("Бронь подтверждена. Удачи!")
                    return

            await update.message.reply_text("Нет ожидающих для подтверждения.")

        except Exception as e:
            logger.error(f"Ошибка в confirm_waiting_booking: {str(e)}")
            await update.message.reply_text("Произошла ошибка при подтверждении брони.")

    async def add_to_waiting_list(self, update, context):
        """Обрабатывает команду /wait"""
        try:
            from handlers.waiting_list_handler import WaitingListHandler

            waiting_handler = WaitingListHandler()
            await waiting_handler.show_waiting_list_menu(update, context)
        except Exception as e:
            logger.error(f"Ошибка в add_to_waiting_list: {str(e)}")
            await update.message.reply_text(
                "Произошла ошибка при добавлении в лист ожидания."
            )

    def run(self):
        """Запускает бота"""
        try:
            # Инициализируем базу данных
            init_database()
            logger.info("База данных инициализирована")

            # Создаем приложение
            self.application = (
                Application.builder()
                .token(TELEGRAM_TOKEN)
                .post_init(self.post_init)
                .build()
            )

            # Настраиваем обработчики
            self.setup_handlers()

            # Запускаем бота
            logger.info("Запуск бота...")
            self.application.run_polling()

        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {str(e)}")
            raise


def main():
    """Главная функция"""
    bot = TransferBot()
    bot.run()


if __name__ == "__main__":
    main()
