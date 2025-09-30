"""
Утилиты для создания клавиатур
"""

from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from models.entities import Bus, Reservation


def create_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Создает главное меню"""
    keyboard = [
        [InlineKeyboardButton("Записаться на автобус", callback_data="book_bus")],
        [InlineKeyboardButton("Посмотреть свою бронь", callback_data="view_booking")],
        [InlineKeyboardButton("Отменить запись", callback_data="cancel_booking")],
        [InlineKeyboardButton("Как добраться?", callback_data="how_to_get_there")],
        [InlineKeyboardButton("FAQ", callback_data="render_faq")],
    ]

    # Добавляем кнопку выгрузки только для администраторов
    if is_admin:
        keyboard.append(
            [InlineKeyboardButton("Выгрузить данные", callback_data="export_buses")]
        )

    return InlineKeyboardMarkup(keyboard)


def create_directions_keyboard(directions: List[str]) -> InlineKeyboardMarkup:
    """Создает клавиатуру с направлениями"""
    keyboard = [
        [InlineKeyboardButton(direction, callback_data=f"select_direction_{direction}")]
        for direction in reversed(directions)
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def create_buses_keyboard(
    buses: List[Bus], reservations: List[Reservation]
) -> InlineKeyboardMarkup:
    """Создает клавиатуру с автобусами"""
    keyboard = []

    for bus in buses:
        # Подсчитываем занятые места
        booked = len([r for r in reservations if r.bus_id == bus.id])
        free = bus.capacity - booked

        if free > 0:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"Автобус {bus.number} - {free} мест",
                        callback_data=f"select_bus_{bus.id}",
                    )
                ]
            )
        else:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"Автобус {bus.number} - в лист ожидания",
                        callback_data=f"set_waiting_bus_{bus.id}",
                    )
                ]
            )

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def create_booking_cancel_keyboard(
    reservations: List[Reservation], buses: List[Bus]
) -> InlineKeyboardMarkup:
    """Создает клавиатуру для отмены бронирований"""
    keyboard = []

    for res in reservations:
        bus = next((b for b in buses if b.id == res.bus_id), None)
        if bus:
            button_text = f"Автобус {bus.number} ({bus.departure_date} {bus.departure_time}) Направление: {bus.direction}"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        button_text, callback_data=f"cancel_reservation_{res.id}"
                    )
                ]
            )

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def create_waiting_list_keyboard(buses: List[Bus]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора автобуса в лист ожидания"""
    keyboard = [
        [
            InlineKeyboardButton(
                f"Автобус {bus.number} ({bus.departure_date} {bus.departure_time})",
                callback_data=f"set_waiting_bus_{bus.id}",
            )
        ]
        for bus in buses
    ]
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def create_back_keyboard() -> InlineKeyboardMarkup:
    """Создает простую клавиатуру с кнопкой 'Назад'"""
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)


def create_confirm_booking_keyboard(bus_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения брони"""
    keyboard = [
        [
            InlineKeyboardButton(
                "Подтвердить бронь", callback_data=f"select_bus_{bus_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
