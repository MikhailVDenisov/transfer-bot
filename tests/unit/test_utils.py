"""
Тесты для утилит
"""

import pytest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from models.entities import Bus, Reservation
from tests.factories import BusFactory, ReservationFactory
from utils.const import BROADCAST_CHIEF_CANCEL, BROADCAST_CHIEF_SELECT_BUS
from utils.keyboards import (
    create_back_keyboard,
    create_booking_cancel_keyboard,
    create_buses_keyboard,
    create_cancel_broadcast_chief_keyboard,
    create_chief_buses_keyboard,
    create_citizenship_keyboard,
    create_confirm_booking_keyboard,
    create_directions_keyboard,
    create_main_menu_keyboard,
    create_personal_data_confirm_keyboard,
    create_personal_data_export_buses_keyboard,
    create_personal_data_prompt_keyboard,
    create_personal_data_view_keyboard,
    create_reply_keyboard_remove,
    create_waiting_list_keyboard,
)
from utils.messages import (
    format_booking_info,
    format_booking_success_message,
    format_bus_info,
    format_buses_list_message,
    format_user_bookings_message,
    format_waiting_notification_message,
)
from utils.validators import (
    validate_citizenship,
    validate_fio,
    validate_passport_number,
    validate_phone,
    validate_username,
)


class TestKeyboards:
    """Тесты для утилит создания клавиатур"""

    def test_create_main_menu_keyboard_user(self):
        """Тест создания главного меню для обычного пользователя"""
        keyboard = create_main_menu_keyboard(is_admin=False)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 6  # 6 основных кнопок

        # Проверяем наличие основных кнопок
        button_texts = [
            button.text for row in keyboard.inline_keyboard for button in row
        ]
        assert "Записаться на автобус" in button_texts
        assert "Персональные данные" in button_texts
        assert "Посмотреть свою бронь" in button_texts
        assert "Отменить запись" in button_texts
        assert "Как добраться?" in button_texts
        assert "FAQ" in button_texts
        assert "Выгрузить персональные данные пассажиров" not in button_texts

    def test_create_main_menu_keyboard_admin(self):
        """Тест создания главного меню для администратора"""
        keyboard = create_main_menu_keyboard(is_admin=True)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 7  # 6 основных + 1 админская

        # Проверяем наличие админской кнопки
        button_texts = [
            button.text for row in keyboard.inline_keyboard for button in row
        ]
        assert "Выгрузить персональные данные пассажиров" in button_texts

    def test_create_directions_keyboard(self):
        """Тест создания клавиатуры с направлениями"""
        directions = ["Туда", "Обратно"]
        keyboard = create_directions_keyboard(directions)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 3  # 2 направления + кнопка "Назад"

        # Проверяем наличие кнопок направлений
        button_texts = [
            button.text for row in keyboard.inline_keyboard for button in row
        ]
        assert "Обратно" in button_texts  # Должно быть в обратном порядке
        assert "Туда" in button_texts
        assert "Назад" in button_texts

    def test_create_buses_keyboard(self):
        """Тест создания клавиатуры с автобусами"""
        buses = [
            BusFactory.build(id=1, number="БУС-001", capacity=30),
            BusFactory.build(id=2, number="БУС-002", capacity=25),
        ]
        reservations = [
            ReservationFactory.build(bus_id=1),
            ReservationFactory.build(bus_id=1),
            ReservationFactory.build(bus_id=2),
        ]

        keyboard = create_buses_keyboard(buses, reservations)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 3  # 2 автобуса + кнопка "Назад"

        # Проверяем наличие кнопок автобусов
        button_texts = [
            button.text for row in keyboard.inline_keyboard for button in row
        ]
        assert any("БУС-001" in text for text in button_texts)
        assert any("БУС-002" in text for text in button_texts)
        assert "Назад" in button_texts

    def test_create_buses_keyboard_full_bus(self):
        """Тест создания клавиатуры с полностью занятым автобусом"""
        buses = [BusFactory.build(id=1, number="БУС-001", capacity=2)]
        reservations = [
            ReservationFactory.build(bus_id=1),
            ReservationFactory.build(bus_id=1),
        ]

        keyboard = create_buses_keyboard(buses, reservations)

        # Проверяем, что для занятого автобуса показывается кнопка "в лист ожидания"
        button_texts = [
            button.text for row in keyboard.inline_keyboard for button in row
        ]
        assert any("в лист ожидания" in text for text in button_texts)

    def test_create_booking_cancel_keyboard(self):
        """Тест создания клавиатуры для отмены бронирований"""
        buses = [
            BusFactory.build(
                id=1,
                number="БУС-001",
                departure_date="2024-01-15",
                departure_time="10:00",
                direction="Туда",
            )
        ]
        reservations = [ReservationFactory.build(id=1, bus_id=1)]

        keyboard = create_booking_cancel_keyboard(reservations, buses)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 2  # 1 бронирование + кнопка "Назад"

        # Проверяем наличие кнопки отмены
        button_texts = [
            button.text for row in keyboard.inline_keyboard for button in row
        ]
        assert any("БУС-001" in text for text in button_texts)
        assert "Назад" in button_texts

    def test_create_waiting_list_keyboard(self):
        """Тест создания клавиатуры для листа ожидания"""
        buses = [
            BusFactory.build(
                id=1,
                number="БУС-001",
                departure_date="2024-01-15",
                departure_time="10:00",
            ),
            BusFactory.build(
                id=2,
                number="БУС-002",
                departure_date="2024-01-15",
                departure_time="12:00",
            ),
        ]

        keyboard = create_waiting_list_keyboard(buses)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 3  # 2 автобуса + кнопка "Отмена"

        # Проверяем наличие кнопок автобусов
        button_texts = [
            button.text for row in keyboard.inline_keyboard for button in row
        ]
        assert any("БУС-001" in text for text in button_texts)
        assert any("БУС-002" in text for text in button_texts)
        assert "Отмена" in button_texts

    def test_create_back_keyboard(self):
        """Тест создания простой клавиатуры с кнопкой 'Назад'"""
        keyboard = create_back_keyboard()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].text == "Назад"
        assert keyboard.inline_keyboard[0][0].callback_data == "back_to_menu"

    def test_create_personal_data_prompt_keyboard(self):
        """Тест клавиатуры перехода к вводу персональных данных"""
        keyboard = create_personal_data_prompt_keyboard("personal_data_from_booking")

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 2
        assert keyboard.inline_keyboard[0][0].text == "Заполнить данные"
        assert (
            keyboard.inline_keyboard[0][0].callback_data == "personal_data_from_booking"
        )

    def test_create_citizenship_keyboard(self):
        """Тест клавиатуры гражданства со значением по умолчанию"""
        keyboard = create_citizenship_keyboard()

        assert isinstance(keyboard, ReplyKeyboardMarkup)
        assert keyboard.keyboard[0][0].text == "РФ"

    def test_create_personal_data_confirm_keyboard(self):
        """Тест клавиатуры подтверждения персональных данных"""
        keyboard = create_personal_data_confirm_keyboard()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert keyboard.inline_keyboard[0][0].text == "Подтвердить данные"
        assert (
            keyboard.inline_keyboard[0][0].callback_data == "personal_data_confirm_save"
        )

    def test_create_personal_data_view_keyboard(self):
        """Тест клавиатуры просмотра персональных данных"""
        keyboard = create_personal_data_view_keyboard()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert keyboard.inline_keyboard[0][0].text == "Редактировать"
        assert keyboard.inline_keyboard[0][0].callback_data == "personal_data_edit"
        assert keyboard.inline_keyboard[1][0].text == "Назад"

    def test_create_reply_keyboard_remove(self):
        """Тест удаления reply-клавиатуры"""
        keyboard = create_reply_keyboard_remove()

        assert keyboard is not None

    def test_create_confirm_booking_keyboard(self):
        """Тест создания клавиатуры для подтверждения брони"""
        keyboard = create_confirm_booking_keyboard(bus_id=1)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].text == "Подтвердить бронь"
        assert keyboard.inline_keyboard[0][0].callback_data == "select_bus_1"

    def test_create_chief_buses_keyboard(self):
        """Тест создания клавиатуры с автобусами для рассылки шефа"""
        buses = [
            BusFactory.build(id=1, number="БУС-001", destination="Переславль"),
            BusFactory.build(id=2, number="БУС-002", destination="Москва"),
        ]

        keyboard = create_chief_buses_keyboard(buses)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 3  # 2 автобуса + «Назад»

        button_texts = [
            button.text for row in keyboard.inline_keyboard for button in row
        ]
        assert any("БУС-001" in text for text in button_texts)
        assert any("Переславль" in text for text in button_texts)
        assert any("БУС-002" in text for text in button_texts)
        assert any("Москва" in text for text in button_texts)
        assert "Назад" in button_texts

        assert keyboard.inline_keyboard[0][0].callback_data == (
            f"{BROADCAST_CHIEF_SELECT_BUS}1"
        )
        assert keyboard.inline_keyboard[1][0].callback_data == (
            f"{BROADCAST_CHIEF_SELECT_BUS}2"
        )
        assert keyboard.inline_keyboard[2][0].callback_data == "back_to_menu"

    def test_create_chief_buses_keyboard_empty(self):
        """Тест клавиатуры шефа при отсутствии автобусов — только «Назад»"""
        keyboard = create_chief_buses_keyboard([])

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 1
        assert keyboard.inline_keyboard[0][0].text == "Назад"
        assert keyboard.inline_keyboard[0][0].callback_data == "back_to_menu"

    def test_cancel_broadcast_chief_keyboard(self):
        """Тест клавиатуры отмены рассылки шефа"""
        keyboard = create_cancel_broadcast_chief_keyboard()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].text == "Отмена"
        assert keyboard.inline_keyboard[0][0].callback_data == BROADCAST_CHIEF_CANCEL

    def test_create_personal_data_export_buses_keyboard(self):
        """Тест клавиатуры выбора автобусов для выгрузки персональных данных"""
        buses = [
            BusFactory.build(
                id=1,
                number="БУС-001",
                departure_date="2024-01-15",
                departure_time="10:00",
            ),
            BusFactory.build(
                id=2,
                number="БУС-002",
                departure_date="2024-01-15",
                departure_time="12:00",
            ),
        ]

        keyboard = create_personal_data_export_buses_keyboard(buses, [2])

        assert isinstance(keyboard, InlineKeyboardMarkup)
        button_texts = [
            button.text for row in keyboard.inline_keyboard for button in row
        ]
        assert "⬜ Автобус БУС-001 (2024-01-15 10:00)" in button_texts
        assert "✅ Автобус БУС-002 (2024-01-15 12:00)" in button_texts
        assert "Сформировать выгрузку" in button_texts
        assert "Назад" in button_texts


class TestMessages:
    """Тесты для утилит форматирования сообщений"""

    def test_format_bus_info_with_free_places(self):
        """Тест форматирования информации об автобусе со свободными местами"""
        bus = BusFactory.build(
            number="БУС-001",
            departure_date="2024-01-15",
            departure_time="10:00",
            capacity=30,
        )
        booked_count = 5

        result = format_bus_info(bus, booked_count)

        expected = "Автобус БУС-001 (2024-01-15 10:00): Свободных мест: 25"
        assert result == expected

    def test_format_bus_info_no_free_places(self):
        """Тест форматирования информации об автобусе без свободных мест"""
        bus = BusFactory.build(
            number="БУС-001",
            departure_date="2024-01-15",
            departure_time="10:00",
            capacity=30,
        )
        booked_count = 30

        result = format_bus_info(bus, booked_count)

        expected = "Автобус БУС-001 (2024-01-15 10:00): Мест нет"
        assert result == expected

    def test_format_booking_info(self):
        """Тест форматирования информации о бронировании"""
        bus = BusFactory.build(
            number="БУС-001",
            departure_date="2024-01-15",
            departure_time="10:00",
            departure_place="Москва",
            destination="Переславль-Залесский",
            direction="Туда",
        )
        reservation = ReservationFactory.build()

        result = format_booking_info(reservation, bus)

        expected = (
            "Автобус: БУС-001 (2024-01-15 10:00) (Москва-Переславль-Залесский)-Туда"
        )
        assert result == expected

    def test_format_booking_success_message(self):
        """Тест форматирования сообщения об успешном бронировании"""
        bus = BusFactory.build(
            number="БУС-001",
            departure_date="2024-01-15",
            departure_time="10:00",
            departure_place="Москва",
            destination="Переславль-Залесский",
        )

        result = format_booking_success_message(bus)

        expected = "Вы успешно записаны на автобус: БУС-001 (2024-01-15 10:00) Москва-Переславль-Залесский"
        assert result == expected

    def test_format_waiting_notification_message(self):
        """Тест форматирования сообщения уведомления из листа ожидания"""
        bus = BusFactory.build(
            number="БУС-001", departure_date="2024-01-15", departure_time="10:00"
        )

        result = format_waiting_notification_message(bus)

        expected = "🚌 Место на автобус БУС-001 (2024-01-15 10:00) теперь доступно!\n❗У вас есть 10 минут, чтобы подтвердить бронь, после бот отправит пуш следующему в листе ожидания. \nНажмите кнопку ниже чтобы подтвердить бронь:"
        assert result == expected

    def test_format_buses_list_message(self):
        """Тест форматирования сообщения со списком автобусов"""
        buses = [
            BusFactory.build(
                number="БУС-001",
                departure_date="2024-01-15",
                departure_time="10:00",
                capacity=30,
            ),
            BusFactory.build(
                number="БУС-002",
                departure_date="2024-01-15",
                departure_time="12:00",
                capacity=25,
            ),
        ]
        reservations = [
            ReservationFactory.build(bus_id=buses[0].id),
            ReservationFactory.build(bus_id=buses[0].id),
            ReservationFactory.build(bus_id=buses[1].id),
        ]
        direction = "Туда"

        result = format_buses_list_message(buses, reservations, direction)

        assert "Доступные автобусы для направления Туда:" in result
        assert "БУС-001" in result
        assert "БУС-002" in result
        assert "Свободных мест: 27" in result  # 30 - 3 (2 резервации + 1 из фабрики)
        assert "Свободных мест: 22" in result  # 25 - 3 (1 резервация + 2 из фабрики)

    def test_format_user_bookings_message_with_bookings(self):
        """Тест форматирования сообщения с бронированиями пользователя"""
        buses = [
            BusFactory.build(
                id=1,
                number="БУС-001",
                departure_date="2024-01-15",
                departure_time="10:00",
                departure_place="Москва",
                destination="Переславль-Залесский",
                direction="Туда",
            )
        ]
        reservations = [ReservationFactory.build(bus_id=1)]

        result = format_user_bookings_message(reservations, buses)

        assert "Ваши записи:" in result
        assert "БУС-001" in result
        assert "Москва-Переславль-Залесский" in result

    def test_format_user_bookings_message_no_bookings(self):
        """Тест форматирования сообщения без бронирований"""
        result = format_user_bookings_message([], [])

        assert result == "Вы не записаны ни на один автобус"


class TestValidators:
    """Тесты для валидаторов"""

    def test_validate_fio_valid(self):
        """Тест валидации корректного ФИО"""
        valid_fios = [
            "Иванов Иван Иванович",
            "Петров Петр",
            "Сидоров-Козлов Алексей Михайлович",
            "Мария-Анна Петрова",
        ]

        for fio in valid_fios:
            is_valid, error_msg = validate_fio(fio)
            assert is_valid is True, f"ФИО '{fio}' должно быть валидным"
            assert error_msg == ""

    def test_validate_fio_invalid(self):
        """Тест валидации некорректного ФИО"""
        invalid_cases = [
            ("", "ФИО не может быть пустым"),
            ("Ив", "ФИО должно содержать не менее 5 символов"),
            ("Иванов", "ФИО должно содержать минимум имя и фамилию"),
            ("Иванов123", "ФИО может содержать только буквы, пробелы и дефисы"),
            (
                "Иванов Иван Иванович Иванович Иванович Иванович Иванович Иванович Иванович Иванович Иванович",
                "ФИО не может содержать более 50 символов",
            ),
        ]

        for fio, expected_error in invalid_cases:
            is_valid, error_msg = validate_fio(fio)
            assert is_valid is False, f"ФИО '{fio}' должно быть невалидным"
            assert expected_error in error_msg

    def test_validate_phone_valid(self):
        """Тест валидации корректного номера телефона"""
        valid_phones = [
            "+7900123456",
            "8900123456",
            "9001234567",
            "+79001234567",
        ]

        for phone in valid_phones:
            is_valid, error_msg = validate_phone(phone)
            assert is_valid is True, f"Телефон '{phone}' должен быть валидным"
            assert error_msg == ""

    def test_validate_phone_invalid(self):
        """Тест валидации некорректного номера телефона"""
        invalid_cases = [
            ("", "Номер телефона не может быть пустым"),
            (
                "+7 (900) 123-45-67",
                "Номер телефона может содержать только цифры и символ +",
            ),
            (
                "8900-123-45-67",
                "Номер телефона может содержать только цифры и символ +",
            ),
            ("8 9001234567", "Номер телефона может содержать только цифры и символ +"),
            ("123", "Номер телефона слишком короткий"),
            ("12345678901234567890", "Номер телефона слишком длинный"),
        ]

        for phone, expected_error in invalid_cases:
            is_valid, error_msg = validate_phone(phone)
            assert is_valid is False, f"Телефон '{phone}' должен быть невалидным"
            assert expected_error in error_msg

    def test_validate_passport_number_valid(self):
        """Тест валидации корректного номера паспорта"""
        is_valid, error_msg = validate_passport_number("1234 567890")

        assert is_valid is True
        assert error_msg == ""

    def test_validate_passport_number_invalid(self):
        """Тест валидации некорректного номера паспорта"""
        invalid_cases = [
            ("", "Серия и номер паспорта не могут быть пустыми"),
        ]

        for passport_number, expected_error in invalid_cases:
            is_valid, error_msg = validate_passport_number(passport_number)
            assert is_valid is False
            assert expected_error in error_msg

    def test_validate_citizenship_valid(self):
        """Тест валидации корректного гражданства"""
        valid_values = ["РФ", "Россия", "Беларусь", "Казахстан", "Нью-Зеландия"]

        for citizenship in valid_values:
            is_valid, error_msg = validate_citizenship(citizenship)
            assert is_valid is True
            assert error_msg == ""

    def test_validate_citizenship_invalid(self):
        """Тест валидации некорректного гражданства"""
        invalid_cases = [
            ("-", "Гражданство должно содержать не менее 2 символов"),
            ("1", "Гражданство должно содержать не менее 2 символов"),
            ("РФ123", "Гражданство должно быть текстом"),
            ("USA!", "Гражданство должно быть текстом"),
        ]

        for citizenship, expected_error in invalid_cases:
            is_valid, error_msg = validate_citizenship(citizenship)
            assert is_valid is False
            assert expected_error in error_msg

    def test_validate_username_valid(self):
        """Тест валидации корректного username"""
        valid_usernames = [
            "test_user",
            "user123",
            "test_user_123",
            "user",
            "a" * 32,  # Максимальная длина
        ]

        for username in valid_usernames:
            is_valid, error_msg = validate_username(username)
            assert is_valid is True, f"Username '{username}' должен быть валидным"
            assert error_msg == ""

    def test_validate_username_invalid(self):
        """Тест валидации некорректного username"""
        invalid_cases = [
            ("", "Username не может быть пустым"),
            ("ab", "Username должен содержать не менее 3 символов"),
            ("a" * 33, "Username не может содержать более 32 символов"),
            (
                "user@123",
                "Username может содержать только буквы, цифры и подчеркивания",
            ),
            (
                "user-123",
                "Username может содержать только буквы, цифры и подчеркивания",
            ),
        ]

        for username, expected_error in invalid_cases:
            is_valid, error_msg = validate_username(username)
            assert is_valid is False, f"Username '{username}' должен быть невалидным"
            assert expected_error in error_msg
