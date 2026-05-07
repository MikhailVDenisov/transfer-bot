"""
Утилиты для создания клавиатур
"""

from typing import List, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from models.entities import Bus, Reservation
from utils.const import (
    BROADCAST_CHIEF_CANCEL,
    BROADCAST_CHIEF_COMMAND,
    BROADCAST_CHIEF_SELECT_BUS,
    EXPORT_CHIEF_COMMAND,
    EXPORT_CHIEF_SELECT_BUS,
)


def create_main_menu_keyboard(
    is_admin: bool = False, is_chief: bool = False
) -> InlineKeyboardMarkup:
    """Создает главное меню"""
    keyboard = [
        [InlineKeyboardButton("Записаться на автобус", callback_data="book_bus")],
        [InlineKeyboardButton("Персональные данные", callback_data="personal_data")],
        [InlineKeyboardButton("Посмотреть свою бронь", callback_data="view_booking")],
        [InlineKeyboardButton("Отменить запись", callback_data="cancel_booking")],
        [InlineKeyboardButton("Как добраться?", callback_data="how_to_get_there")],
        [InlineKeyboardButton("FAQ", callback_data="render_faq")],
    ]

    # Добавляем кнопку отправить сообщение только для шефа
    if is_chief:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "Отправить сообщение моим пассажирам",
                    callback_data=BROADCAST_CHIEF_COMMAND,
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "Выгрузить список пассажиров",
                    callback_data=EXPORT_CHIEF_COMMAND,
                )
            ]
        )

    # Добавляем кнопку выгрузки только для администраторов
    if is_admin:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "Выгрузить персональные данные пассажиров",
                    callback_data="export_personal_data",
                )
            ],
        )
        # keyboard.append(
        #     [InlineKeyboardButton("Выгрузить данные", callback_data="export_buses")]
        # )

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


def create_back_keyboard(text: str = "Назад") -> InlineKeyboardMarkup:
    """Создает простую клавиатуру с кнопкой 'Назад'"""
    keyboard = [[InlineKeyboardButton(text, callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)


def create_personal_data_prompt_keyboard(
    callback_data: str = "personal_data",
) -> InlineKeyboardMarkup:
    """Создает клавиатуру для перехода к вводу персональных данных"""
    keyboard = [
        [InlineKeyboardButton("Заполнить данные", callback_data=callback_data)],
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_personal_data_view_keyboard(
    allow_edit: bool = True,
) -> InlineKeyboardMarkup:
    """Создает клавиатуру просмотра персональных данных"""
    keyboard = []
    if allow_edit:
        keyboard.append(
            [InlineKeyboardButton("Редактировать", callback_data="personal_data_edit")]
        )
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def create_citizenship_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру с гражданством по умолчанию"""
    keyboard = [[KeyboardButton("РФ")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def create_phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру запроса номера телефона из Telegram"""
    keyboard = [[KeyboardButton("Поделиться номером", request_contact=True)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def create_personal_data_confirm_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения персональных данных"""
    keyboard = [
        [
            InlineKeyboardButton(
                "Редактировать", callback_data="personal_data_confirm_edit"
            ),
            InlineKeyboardButton(
                "Подтвердить данные", callback_data="personal_data_confirm_save"
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_reply_keyboard_remove() -> ReplyKeyboardRemove:
    """Убирает reply-клавиатуру"""
    return ReplyKeyboardRemove()


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


def create_chief_buses_keyboard(
    buses: List[Bus],
) -> InlineKeyboardMarkup:
    """Создает клавиатуру с автобусами для владельца"""
    keyboard = []

    for bus in buses:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"Автобус №{bus.number}, направление - {bus.direction}",
                    callback_data=f"{BROADCAST_CHIEF_SELECT_BUS}{bus.id}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def create_cancel_broadcast_chief_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с отменой рассылки"""
    keyboard = [[InlineKeyboardButton("Отмена", callback_data=BROADCAST_CHIEF_CANCEL)]]
    return InlineKeyboardMarkup(keyboard)


def create_personal_data_export_buses_keyboard(
    buses: List[Bus], selected_bus_ids: Optional[List[int]] = None
) -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора автобусов для выгрузки персональных данных"""
    selected_bus_ids = selected_bus_ids or []
    selected_bus_ids_set = {int(bus_id) for bus_id in selected_bus_ids}
    keyboard = []

    for bus in buses:
        is_selected = bus.id in selected_bus_ids_set
        prefix = "✅" if is_selected else "⬜"
        button_text = (
            f"{prefix} Автобус {bus.number} ({bus.departure_date} {bus.departure_time})"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    button_text, callback_data=f"export_personal_data_bus_{bus.id}"
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "Сформировать выгрузку",
                callback_data="export_personal_data_generate",
            )
        ]
    )
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def create_chief_export_buses_keyboard(buses: List[Bus]) -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора автобуса для выгрузки шефом"""
    keyboard = []

    for bus in buses:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"Автобус {bus.number} ({bus.departure_date} {bus.departure_time}) {bus.direction}",
                    callback_data=f"{EXPORT_CHIEF_SELECT_BUS}{bus.id}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)
