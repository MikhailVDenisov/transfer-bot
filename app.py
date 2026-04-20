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
from handlers.personal_data_handler import (
    PERSONAL_BIRTH_DATE,
    PERSONAL_CITIZENSHIP,
    PERSONAL_CONFIRM,
    PERSONAL_FIRST_NAME,
    PERSONAL_LAST_NAME,
    PERSONAL_PASSPORT,
    PERSONAL_PATRONYMIC,
    PERSONAL_PHONE,
    PersonalDataHandler,
)
from handlers.start_handler import StartHandler
from services.waiting_list_service import WaitingListService

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Сообщения рассылки шефа обрабатываются после группы 0 (callbacks, ConversationHandler и т.д.)
BROADCAST_CHIEF_MESSAGE_GROUP = 1


class TransferBot:
    """Основной класс бота"""

    def __init__(self):
        self.application = None
        self.start_handler = StartHandler()
        self.callback_handler = CallbackHandler()
        self.booking_handler = BookingHandler()
        self.personal_data_handler = PersonalDataHandler()
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

        # ConversationHandler для ввода персональных данных
        personal_data_conversation = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    self.personal_data_handler.show_personal_data,
                    pattern="^personal_data$",
                ),
                CallbackQueryHandler(
                    self.personal_data_handler.start_flow,
                    pattern="^personal_data_from_booking$",
                ),
                CallbackQueryHandler(
                    self.personal_data_handler.start_flow,
                    pattern="^personal_data_edit$",
                ),
            ],
            states={
                PERSONAL_LAST_NAME: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.personal_data_handler.handle_last_name,
                    )
                ],
                PERSONAL_FIRST_NAME: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.personal_data_handler.handle_first_name,
                    )
                ],
                PERSONAL_PATRONYMIC: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.personal_data_handler.handle_patronymic,
                    )
                ],
                PERSONAL_PHONE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.personal_data_handler.handle_phone,
                    )
                ],
                PERSONAL_BIRTH_DATE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.personal_data_handler.handle_birth_date,
                    )
                ],
                PERSONAL_PASSPORT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.personal_data_handler.handle_passport,
                    )
                ],
                PERSONAL_CITIZENSHIP: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.personal_data_handler.handle_citizenship,
                    )
                ],
                PERSONAL_CONFIRM: [
                    CallbackQueryHandler(
                        self.personal_data_handler.confirm_personal_data,
                        pattern="^personal_data_confirm_save$",
                    )
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.personal_data_handler.cancel),
                CommandHandler("start", self.personal_data_handler.restart_to_menu),
                CallbackQueryHandler(
                    self.personal_data_handler.back_to_menu,
                    pattern="^back_to_menu$",
                ),
                CallbackQueryHandler(self.personal_data_handler.handoff_callback),
            ],
        )
        self.application.add_handler(personal_data_conversation)

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

        # Обработчик сообщения шефа в режиме рассылки (отдельная группа — после основных хендлеров)
        self.application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND,
                self.callback_handler.broadcast_chief_handler.handle_chief_message,
            ),
            group=BROADCAST_CHIEF_MESSAGE_GROUP,
        )

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
