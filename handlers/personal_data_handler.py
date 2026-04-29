import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config.settings import MESSAGES
from handlers.base_handler import BaseHandler
from services.booking_service import BookingService
from utils.keyboards import (
    create_back_keyboard,
    create_citizenship_keyboard,
    create_personal_data_confirm_keyboard,
    create_personal_data_view_keyboard,
    create_phone_request_keyboard,
    create_reply_keyboard_remove,
)
from utils.messages import (
    format_personal_data_confirmation_message,
    format_personal_data_view_message,
)
from utils.validators import (
    normalize_citizenship,
    validate_birth_date,
    validate_citizenship,
    validate_name_part,
    validate_passport_number,
    validate_phone,
)

logger = logging.getLogger(__name__)
INVISIBLE_MESSAGE = "\u2063"

(
    PERSONAL_LAST_NAME,
    PERSONAL_FIRST_NAME,
    PERSONAL_PATRONYMIC,
    PERSONAL_PHONE,
    PERSONAL_BIRTH_DATE,
    PERSONAL_PASSPORT,
    PERSONAL_CITIZENSHIP,
    PERSONAL_CONFIRM,
) = range(8)


class PersonalDataHandler(BaseHandler):
    """Обработчик ввода персональных данных"""

    def __init__(self):
        super().__init__()
        self.booking_service = BookingService()

    async def show_personal_data(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Показывает текущие персональные данные и кнопки действий"""
        try:
            query = update.callback_query
            await query.answer()

            passenger = await self.get_or_create_passenger(update)
            if not passenger:
                return ConversationHandler.END

            if not passenger.has_confirmed_personal_data():
                return await self._start_flow(update, context, passenger, False)

            await query.edit_message_text(
                format_personal_data_view_message(passenger),
                reply_markup=create_personal_data_view_keyboard(),
            )
            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Ошибка в show_personal_data: {str(e)}")
            await self.send_error_message(
                update, "Ошибка при получении персональных данных"
            )
            return ConversationHandler.END

    async def start_flow(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Запускает ввод персональных данных"""
        return await self._start_flow(update, context)

    async def _start_flow(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        passenger=None,
        answer_callback: bool = True,
    ) -> int:
        """Внутренний запуск ввода персональных данных"""
        try:
            query = update.callback_query
            if answer_callback:
                await query.answer()

            passenger = passenger or await self.get_or_create_passenger(update)
            if not passenger:
                return ConversationHandler.END

            if self.booking_service.has_active_bookings(passenger):
                await query.edit_message_text(
                    MESSAGES["personal_data_locked"],
                    reply_markup=create_back_keyboard(),
                )
                return ConversationHandler.END

            context.user_data["personal_data"] = self._build_initial_personal_data(
                passenger
            )
            context.user_data["personal_data_return_to_booking"] = (
                query.data == "personal_data_from_booking"
            )
            await query.edit_message_text(
                self._format_prompt(
                    MESSAGES["personal_data_intro"],
                    MESSAGES["personal_data_last_name"],
                    context.user_data["personal_data"].get("last_name"),
                )
            )
            return PERSONAL_LAST_NAME

        except Exception as e:
            logger.error(f"Ошибка в _start_flow: {str(e)}")
            await self.send_error_message(
                update, "Ошибка при запуске ввода персональных данных"
            )
            return ConversationHandler.END

    async def handle_last_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обрабатывает ввод фамилии"""
        value = update.message.text.strip()
        is_valid, error_message = validate_name_part(value, "Фамилия")
        if not is_valid:
            await update.message.reply_text(f"❌ {error_message}")
            return PERSONAL_LAST_NAME

        context.user_data.setdefault("personal_data", {})["last_name"] = value
        await update.message.reply_text(
            self._format_prompt(
                None,
                MESSAGES["personal_data_first_name"],
                context.user_data["personal_data"].get("first_name"),
            )
        )
        return PERSONAL_FIRST_NAME

    async def handle_first_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обрабатывает ввод имени"""
        value = update.message.text.strip()
        is_valid, error_message = validate_name_part(value, "Имя")
        if not is_valid:
            await update.message.reply_text(f"❌ {error_message}")
            return PERSONAL_FIRST_NAME

        context.user_data.setdefault("personal_data", {})["first_name"] = value
        await update.message.reply_text(
            self._format_prompt(
                None,
                MESSAGES["personal_data_patronymic"],
                context.user_data["personal_data"].get("patronymic"),
            )
        )
        return PERSONAL_PATRONYMIC

    async def handle_patronymic(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обрабатывает ввод отчества"""
        raw_value = update.message.text.strip()
        value = "" if raw_value == "-" else raw_value

        is_valid, error_message = validate_name_part(value, "Отчество", optional=True)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_message}")
            return PERSONAL_PATRONYMIC

        context.user_data.setdefault("personal_data", {})["patronymic"] = value
        await update.message.reply_text(
            self._format_prompt(
                None,
                MESSAGES["personal_data_phone"],
                context.user_data["personal_data"].get("phone"),
            ),
            reply_markup=create_phone_request_keyboard(),
        )
        return PERSONAL_PHONE

    async def handle_phone(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обрабатывает ввод телефона"""
        contact = getattr(update.message, "contact", None)
        if contact and getattr(contact, "phone_number", None):
            value = contact.phone_number.strip()
        else:
            value = (update.message.text or "").strip()

        is_valid, error_message = validate_phone(value)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_message}")
            return PERSONAL_PHONE

        context.user_data.setdefault("personal_data", {})["phone"] = value
        await update.message.reply_text(
            self._format_prompt(
                None,
                MESSAGES["personal_data_birth_date"],
                context.user_data["personal_data"].get("birth_date"),
            ),
            reply_markup=create_reply_keyboard_remove(),
        )
        return PERSONAL_BIRTH_DATE

    async def handle_birth_date(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обрабатывает ввод даты рождения"""
        value = update.message.text.strip()
        is_valid, error_message = validate_birth_date(value)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_message}")
            return PERSONAL_BIRTH_DATE

        context.user_data.setdefault("personal_data", {})["birth_date"] = value
        await update.message.reply_text(
            self._format_prompt(
                None,
                MESSAGES["personal_data_passport"],
                context.user_data["personal_data"].get("passport_number"),
            )
        )
        return PERSONAL_PASSPORT

    async def handle_passport(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Обрабатывает ввод серии и номера паспорта"""
        value = update.message.text.strip()
        is_valid, error_message = validate_passport_number(value)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_message}")
            return PERSONAL_PASSPORT

        context.user_data.setdefault("personal_data", {})["passport_number"] = value
        await update.message.reply_text(
            self._format_prompt(
                None,
                MESSAGES["personal_data_citizenship"],
                context.user_data["personal_data"].get("citizenship"),
            ),
            reply_markup=create_citizenship_keyboard(),
        )
        return PERSONAL_CITIZENSHIP

    async def handle_citizenship(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Сохраняет гражданство во временные данные и показывает подтверждение"""
        try:
            raw_value = update.message.text.strip()
            is_valid, error_message = validate_citizenship(raw_value)
            if not is_valid:
                await update.message.reply_text(f"❌ {error_message}")
                return PERSONAL_CITIZENSHIP

            personal_data = context.user_data.setdefault("personal_data", {})
            personal_data["citizenship"] = normalize_citizenship(raw_value)

            await update.message.reply_text(
                format_personal_data_confirmation_message(personal_data),
                reply_markup=create_reply_keyboard_remove(),
            )
            await update.message.reply_text(
                MESSAGES["personal_data_confirm"],
                reply_markup=create_personal_data_confirm_keyboard(),
            )
            return PERSONAL_CONFIRM

        except Exception as e:
            logger.error(f"Ошибка в handle_citizenship: {str(e)}")
            self._reset_personal_data_state(context)
            await self._remove_reply_keyboard(update)
            await update.message.reply_text(
                "❌ Произошла ошибка при сохранении персональных данных.",
                reply_markup=create_back_keyboard(),
            )
            return ConversationHandler.END

    async def confirm_personal_data(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Сохраняет персональные данные после явного подтверждения"""
        try:
            query = update.callback_query
            await query.answer()

            chat_id, username = await self.get_user_info(update)
            if not username:
                await self._remove_reply_keyboard(update)
                await query.edit_message_text("❌ Username не найден")
                return ConversationHandler.END

            personal_data = context.user_data.get("personal_data")
            if not personal_data:
                await self._remove_reply_keyboard(update)
                await query.edit_message_text(
                    "❌ Данные для подтверждения не найдены.",
                    reply_markup=create_back_keyboard(),
                )
                return ConversationHandler.END

            passenger, _ = self.passenger_service.get_or_create_passenger(
                username, chat_id
            )
            if self.booking_service.has_active_bookings(passenger):
                self._reset_personal_data_state(context)
                await self._remove_reply_keyboard(update)
                await query.edit_message_text(
                    MESSAGES["personal_data_locked"],
                    reply_markup=create_back_keyboard(),
                )
                return ConversationHandler.END

            success, error_message = self.passenger_service.update_personal_data(
                username, personal_data
            )
            return_to_booking = context.user_data.pop(
                "personal_data_return_to_booking", False
            )
            context.user_data.pop("personal_data", None)

            if not success:
                # await self._remove_reply_keyboard(update)
                await query.edit_message_text(
                    f"❌ {error_message}", reply_markup=create_back_keyboard()
                )
                return ConversationHandler.END

            # await self._remove_reply_keyboard(update)
            if return_to_booking:
                from handlers.booking_handler import BookingHandler

                booking_handler = BookingHandler()
                context.user_data["skip_callback_answer"] = True
                await booking_handler.show_directions(update, context)
            else:
                await query.edit_message_text(
                    MESSAGES["personal_data_saved"], reply_markup=create_back_keyboard()
                )
            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Ошибка в confirm_personal_data: {str(e)}")
            self._reset_personal_data_state(context)
            if update.callback_query:
                await self._remove_reply_keyboard(update)
                await update.callback_query.edit_message_text(
                    "❌ Произошла ошибка при сохранении персональных данных.",
                    reply_markup=create_back_keyboard(),
                )
            return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отменяет ввод персональных данных"""
        self._reset_personal_data_state(context)
        await self._remove_reply_keyboard(update)
        await update.message.reply_text(
            "Ввод персональных данных отменен.",
            reply_markup=create_back_keyboard(),
        )
        return ConversationHandler.END

    async def back_to_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Завершает ввод персональных данных по кнопке Назад"""
        self._reset_personal_data_state(context)

        if update.callback_query:
            await update.callback_query.answer()
            await self._remove_reply_keyboard(update)

        from handlers.start_handler import StartHandler

        start_handler = StartHandler()
        await start_handler.handle(update, context)
        return ConversationHandler.END

    async def restart_to_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Сбрасывает ввод персональных данных по команде /start"""
        self._reset_personal_data_state(context)
        await self._remove_reply_keyboard(update)

        from handlers.start_handler import StartHandler

        start_handler = StartHandler()
        await start_handler.handle(update, context)
        return ConversationHandler.END

    async def handoff_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Завершает диалог персональных данных и передает callback дальше"""
        self._reset_personal_data_state(context)

        if update.callback_query:
            await self._remove_reply_keyboard(update)

        from handlers.callback_handler import CallbackHandler

        callback_handler = CallbackHandler()
        await callback_handler.handle_callback(update, context)
        return ConversationHandler.END

    async def _remove_reply_keyboard(self, update: Update) -> None:
        """Снимает reply-клавиатуру при выходе из сценария"""
        target_message = None

        if update.message:
            target_message = update.message
        elif update.callback_query and update.callback_query.message:
            target_message = update.callback_query.message

        if target_message:
            await target_message.reply_text(
                INVISIBLE_MESSAGE,
                reply_markup=create_reply_keyboard_remove(),
            )

    def _reset_personal_data_state(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Очищает временное состояние формы персональных данных"""
        context.user_data.pop("personal_data", None)
        context.user_data.pop("personal_data_return_to_booking", None)
        context.user_data.pop("skip_callback_answer", None)

    def _build_initial_personal_data(self, passenger) -> dict:
        """Собирает начальные данные формы из профиля пассажира"""
        return {
            "last_name": passenger.last_name or "",
            "first_name": passenger.first_name or "",
            "patronymic": passenger.patronymic or "",
            "phone": passenger.phone or "",
            "birth_date": passenger.birth_date or "",
            "passport_number": passenger.passport_number or "",
            "citizenship": passenger.citizenship or "РФ",
        }

    def _format_prompt(
        self, intro: str | None, prompt: str, current_value: str | None
    ) -> str:
        """Формирует подсказку шага с текущим значением"""
        parts = []
        if intro:
            parts.append(intro)
        parts.append(prompt)
        if current_value:
            parts.append(f"Текущее значение: {current_value}")
        return "\n\n".join(parts)
