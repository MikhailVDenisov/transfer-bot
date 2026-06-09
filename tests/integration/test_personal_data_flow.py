"""
Интеграционные тесты для сценариев персональных данных
"""

from unittest.mock import AsyncMock, Mock

import pytest
from telegram import CallbackQuery, Message, Update, User
from telegram.ext import ConversationHandler

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
from services.passenger_service import PassengerService


def build_message_update(username: str, text: str = "") -> Update:
    """Создает Update с сообщением пользователя"""
    update = Mock(spec=Update)
    update.callback_query = None
    update.message = Mock(spec=Message)
    update.message.chat_id = 123456789
    update.message.text = text
    update.message.from_user = Mock(spec=User)
    update.message.from_user.username = username
    update.message.reply_text = AsyncMock()
    return update


def build_callback_update(username: str, callback_data: str) -> Update:
    """Создает Update с callback запросом"""
    update = Mock(spec=Update)
    update.message = None
    update.callback_query = Mock(spec=CallbackQuery)
    update.callback_query.data = callback_data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.from_user = Mock(spec=User)
    update.callback_query.from_user.username = username
    update.callback_query.message = Mock(spec=Message)
    update.callback_query.message.chat_id = 123456789
    update.callback_query.message.reply_text = AsyncMock()
    return update


@pytest.mark.integration
@pytest.mark.asyncio
class TestPersonalDataFlow:
    """Интеграционные тесты для ввода и просмотра персональных данных"""

    @pytest.fixture
    def context(self):
        context = Mock()
        context.user_data = {}
        return context

    async def test_confirmed_personal_data_saved_to_database(self, context):
        """Сохраняет персональные данные только после подтверждения"""
        username = "test_user"
        handler = PersonalDataHandler()
        passenger_service = PassengerService()
        passenger_service.get_or_create_passenger(username, "123456789")

        start_update = build_callback_update(username, "personal_data_edit")
        state = await handler.start_flow(start_update, context)
        assert state == PERSONAL_LAST_NAME

        steps = [
            ("Иванов", handler.handle_last_name, PERSONAL_FIRST_NAME),
            ("Иван", handler.handle_first_name, PERSONAL_PATRONYMIC),
            ("Иванович", handler.handle_patronymic, PERSONAL_PHONE),
            ("+79001234567", handler.handle_phone, PERSONAL_BIRTH_DATE),
            ("01.01.1990", handler.handle_birth_date, PERSONAL_PASSPORT),
            ("1234 567890", handler.handle_passport, PERSONAL_CITIZENSHIP),
            ("РФ", handler.handle_citizenship, PERSONAL_CONFIRM),
        ]

        for text, step_handler, expected_state in steps:
            message_update = build_message_update(username, text)
            state = await step_handler(message_update, context)
            assert state == expected_state

        before_confirm = passenger_service.repository.get_by_username(username)
        assert before_confirm.last_name is None
        assert before_confirm.personal_data_confirmed is False

        confirm_update = build_callback_update(username, "personal_data_confirm_save")
        state = await handler.confirm_personal_data(confirm_update, context)
        assert state == -1

        passenger = passenger_service.repository.get_by_username(username)
        assert passenger.last_name == "Иванов"
        assert passenger.first_name == "Иван"
        assert passenger.patronymic == "Иванович"
        assert passenger.phone == "+79001234567"
        assert passenger.birth_date == "01.01.1990"
        assert passenger.passport_number == "1234 567890"
        assert passenger.citizenship == "РФ"
        assert passenger.personal_data_confirmed is True

    async def test_edit_personal_data_on_confirmation_step(self, context):
        """Возвращает к вводу фамилии по кнопке редактирования на шаге подтверждения"""
        username = "edit_on_confirm_user"
        handler = PersonalDataHandler()
        passenger_service = PassengerService()
        passenger_service.get_or_create_passenger(username, "123456789")

        start_update = build_callback_update(username, "personal_data_edit")
        state = await handler.start_flow(start_update, context)
        assert state == PERSONAL_LAST_NAME

        steps = [
            ("Иванов", handler.handle_last_name, PERSONAL_FIRST_NAME),
            ("Иван", handler.handle_first_name, PERSONAL_PATRONYMIC),
            ("Иванович", handler.handle_patronymic, PERSONAL_PHONE),
            ("+79001234567", handler.handle_phone, PERSONAL_BIRTH_DATE),
            ("01.01.1990", handler.handle_birth_date, PERSONAL_PASSPORT),
            ("1234 567890", handler.handle_passport, PERSONAL_CITIZENSHIP),
            ("РФ", handler.handle_citizenship, PERSONAL_CONFIRM),
        ]

        for text, step_handler, expected_state in steps:
            message_update = build_message_update(username, text)
            state = await step_handler(message_update, context)
            assert state == expected_state

        edit_update = build_callback_update(username, "personal_data_confirm_edit")
        state = await handler.edit_personal_data_before_confirm(edit_update, context)

        assert state == PERSONAL_LAST_NAME
        edit_update.callback_query.edit_message_text.assert_called_once()
        prompt_text = edit_update.callback_query.edit_message_text.call_args.args[0]
        assert "Текущее значение: Иванов" in prompt_text
        assert context.user_data["personal_data"]["last_name"] == "Иванов"

        change_last_name_update = build_message_update(username, "Петров")
        state = await handler.handle_last_name(change_last_name_update, context)
        assert state == PERSONAL_FIRST_NAME
        assert context.user_data["personal_data"]["last_name"] == "Петров"

    async def test_show_personal_data_for_confirmed_passenger(self, context):
        """Показывает экран просмотра, если данные уже подтверждены"""
        username = "confirmed_user"
        handler = PersonalDataHandler()
        passenger_service = PassengerService()
        passenger_service.get_or_create_passenger(username, "123456789")
        passenger_service.update_personal_data(
            username,
            {
                "last_name": "Петров",
                "first_name": "Петр",
                "patronymic": "Петрович",
                "phone": "+79001234567",
                "birth_date": "02.02.1992",
                "passport_number": "4321 098765",
                "citizenship": "РФ",
            },
        )

        update = build_callback_update(username, "personal_data")
        state = await handler.show_personal_data(update, context)

        assert state == -1
        update.callback_query.edit_message_text.assert_called_once()
        message_text = update.callback_query.edit_message_text.call_args.args[0]
        assert "Ваши персональные данные" in message_text
        assert "Петров" in message_text

    async def test_show_personal_data_hides_edit_when_booking_exists(self, context):
        """При активной брони скрывает кнопку редактирования"""
        username = "confirmed_booked_user"
        handler = PersonalDataHandler()
        passenger_service = PassengerService()
        passenger, _ = passenger_service.get_or_create_passenger(username, "123456780")
        passenger_service.update_personal_data(
            username,
            {
                "last_name": "Орлов",
                "first_name": "Олег",
                "patronymic": "Олегович",
                "phone": "+79001230000",
                "birth_date": "05.05.1995",
                "passport_number": "5555 666777",
                "citizenship": "РФ",
            },
        )

        from database.connection import db_connection

        db_connection.execute_query(
            "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "БУС-011",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "11:00",
                30,
                "Туда",
                True,
            ),
        )
        bus_id = db_connection.execute_query(
            "SELECT ID FROM Buses WHERE Number = ?",
            ("БУС-011",),
            fetch_one=True,
        )[0]
        db_connection.execute_query(
            "INSERT INTO Reservations (PassengerID, BusID, ReservationDate, Direction) VALUES (?, ?, ?, ?)",
            (passenger.id, bus_id, "2024-01-10 09:00:00", "Туда"),
        )

        update = build_callback_update(username, "personal_data")
        await handler.show_personal_data(update, context)

        reply_markup = update.callback_query.edit_message_text.call_args.kwargs[
            "reply_markup"
        ]
        assert len(reply_markup.inline_keyboard) == 1
        assert reply_markup.inline_keyboard[0][0].text == "Назад"

    async def test_booking_flow_returns_to_directions_after_confirmation(self, context):
        """После ввода данных из бронирования возвращает пользователя к выбору направления"""
        username = "booking_user"
        handler = PersonalDataHandler()
        passenger_service = PassengerService()
        passenger_service.get_or_create_passenger(username, "123456789")

        from database.connection import db_connection

        db_connection.execute_query(
            "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "БУС-010",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "10:00",
                30,
                "Туда",
                True,
            ),
        )

        start_update = build_callback_update(username, "personal_data_from_booking")
        state = await handler.start_flow(start_update, context)
        assert state == PERSONAL_LAST_NAME

        steps = [
            ("Сидоров", handler.handle_last_name),
            ("Сидор", handler.handle_first_name),
            ("Сидорович", handler.handle_patronymic),
            ("+79005554433", handler.handle_phone),
            ("03.03.1993", handler.handle_birth_date),
            ("1111 222333", handler.handle_passport),
            ("РФ", handler.handle_citizenship),
        ]

        for text, step_handler in steps:
            message_update = build_message_update(username, text)
            await step_handler(message_update, context)

        confirm_update = build_callback_update(username, "personal_data_confirm_save")
        state = await handler.confirm_personal_data(confirm_update, context)

        assert state == -1
        confirm_update.callback_query.edit_message_text.assert_called()
        final_text = confirm_update.callback_query.edit_message_text.call_args.args[0]
        assert final_text == "Выберите направление:"
