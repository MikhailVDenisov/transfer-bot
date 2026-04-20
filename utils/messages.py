"""
Утилиты для форматирования сообщений
"""

from typing import List

from config.settings import MESSAGES
from models.entities import Bus, Passenger, Reservation


def format_bus_info(bus: Bus, booked_count: int) -> str:
    """Форматирует информацию об автобусе"""
    free = bus.capacity - booked_count
    status = f"Свободных мест: {free}" if free > 0 else "Мест нет"
    return f"Автобус {bus.number} ({bus.departure_date} {bus.departure_time}): {status}"


def format_booking_info(reservation: Reservation, bus: Bus) -> str:
    """Форматирует информацию о бронировании"""
    return (
        f"Автобус: {bus.number} ({bus.departure_date} {bus.departure_time}) "
        f"({bus.departure_place}-{bus.destination})-{bus.direction}"
    )


def format_booking_success_message(bus: Bus) -> str:
    """Форматирует сообщение об успешном бронировании"""
    return MESSAGES["booking_success"].format(
        bus_number=bus.number,
        date=bus.departure_date,
        time=bus.departure_time,
        route=f"{bus.departure_place}-{bus.destination}",
    )


def format_waiting_notification_message(bus: Bus) -> str:
    """Форматирует сообщение уведомления из листа ожидания"""
    return MESSAGES["waiting_notification"].format(
        bus_number=bus.number, date=bus.departure_date, time=bus.departure_time
    )


def format_buses_list_message(
    buses: List[Bus], reservations: List[Reservation], direction: str
) -> str:
    """Форматирует сообщение со списком автобусов"""
    message = f"Доступные автобусы для направления {direction}:\n\n"

    for bus in buses:
        booked = len([r for r in reservations if r.bus_id == bus.id])
        message += format_bus_info(bus, booked) + "\n"

    return message


def format_user_bookings_message(
    reservations: List[Reservation], buses: List[Bus]
) -> str:
    """Форматирует сообщение с бронированиями пользователя"""
    if not reservations:
        return MESSAGES["no_bookings"]

    message = "Ваши записи:\n\n"
    for res in reservations:
        bus = next((b for b in buses if b.id == res.bus_id), None)
        if bus:
            message += format_booking_info(res, bus) + "\n"

    return message


def format_personal_data_confirmation_message(personal_data: dict) -> str:
    """Форматирует сообщение для подтверждения персональных данных"""
    patronymic = personal_data.get("patronymic") or "не указано"
    return (
        "Проверьте введенные данные:\n\n"
        f"Фамилия: {personal_data.get('last_name')}\n"
        f"Имя: {personal_data.get('first_name')}\n"
        f"Отчество: {patronymic}\n"
        f"Телефон: {personal_data.get('phone')}\n"
        f"Дата рождения: {personal_data.get('birth_date')}\n"
        f"Паспорт: {personal_data.get('passport_number')}\n"
        f"Гражданство: {personal_data.get('citizenship')}"
    )


def format_personal_data_view_message(passenger: Passenger) -> str:
    """Форматирует сообщение просмотра персональных данных"""
    return (
        "Ваши персональные данные:\n\n"
        f"Фамилия: {passenger.last_name or 'не указано'}\n"
        f"Имя: {passenger.first_name or 'не указано'}\n"
        f"Отчество: {passenger.patronymic or 'не указано'}\n"
        f"Телефон: {passenger.phone or 'не указано'}\n"
        f"Дата рождения: {passenger.birth_date or 'не указано'}\n"
        f"Паспорт: {passenger.passport_number or 'не указано'}\n"
        f"Гражданство: {passenger.citizenship or 'не указано'}\n"
    )
