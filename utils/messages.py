"""
Утилиты для форматирования сообщений
"""

from collections import defaultdict
from typing import Dict, List, Optional

from config.settings import MESSAGES
from models.entities import Bus, Passenger, Reservation, WaitingListRecord


def format_bus_info(bus: Bus, booked_count: int, manual_reserved_count: int = 0) -> str:
    """Форматирует информацию об автобусе"""
    free = max(bus.capacity - booked_count - manual_reserved_count, 0)
    status = f"Свободных мест: {free}" if free > 0 else "Мест нет"
    return f"Автобус {bus.number} ({bus.departure_date} {bus.departure_time}): {status}"


def format_booking_info(reservation: Reservation, bus: Bus) -> str:
    """Форматирует информацию о бронировании"""
    return (
        f"Автобус: {bus.number} ({bus.departure_date} {bus.departure_time}) "
        f"({bus.departure_place}-{bus.destination})-{bus.direction}"
    )


def format_waiting_info(record: WaitingListRecord, bus: Optional[Bus]) -> str:
    """Форматирует информацию о записи в листе ожидания"""
    if not bus:
        return f"Автобус: ID {record.bus_id}"

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
    buses: List[Bus],
    reservations: List[Reservation],
    direction: str,
    manual_reserved_by_bus: Optional[Dict[int, int]] = None,
) -> str:
    """Форматирует сообщение со списком автобусов"""
    message = f"Доступные автобусы для направления {direction}:\n\n"
    manual_reserved_by_bus = manual_reserved_by_bus or {}

    for bus in buses:
        booked = len([r for r in reservations if r.bus_id == bus.id])
        manual_reserved_count = manual_reserved_by_bus.get(bus.id, 0)
        message += format_bus_info(bus, booked, manual_reserved_count) + "\n"

    return message


def format_available_seats_summary(
    buses: List[Bus], available_seats_by_bus: Dict[int, int]
) -> str:
    """Форматирует сводку доступных мест по направлениям."""
    if not buses:
        return "Информация о доступных местах:\nНет доступных автобусов"

    buses_by_direction = defaultdict(list)
    for bus in buses:
        direction = (bus.direction or "Не указано").strip() or "Не указано"
        buses_by_direction[direction].append(bus)

    lines = ["Информация о доступных местах:\n"]
    sorted_directions = sorted(buses_by_direction.keys(), reverse=False)

    for index, direction in enumerate(sorted_directions):
        if index > 0:
            lines.append("")
        lines.append(f"Направление: {direction}")

        direction_buses = sorted(
            buses_by_direction[direction],
            key=lambda bus: (
                bus.departure_time or "",
                bus.number or "",
            ),
        )
        for bus in direction_buses:
            bus_label = f"Автобус {bus.number or 'без номера'}"
            departure_time = bus.departure_time or "время не указано"
            free_seats = available_seats_by_bus.get(bus.id, 0)
            if free_seats > 0:
                lines.append(f"{bus_label} {departure_time} - {free_seats} мест")
            else:
                lines.append(f"{bus_label} {departure_time} - Доступен лист ожидания")

    return "\n".join(lines)


def format_user_bookings_message(
    reservations: List[Reservation],
    buses: List[Bus],
    waiting_records: Optional[List[WaitingListRecord]] = None,
) -> str:
    """Форматирует сообщение с бронированиями и листом ожидания пользователя"""
    waiting_records = waiting_records or []
    if not reservations and not waiting_records:
        return MESSAGES["no_bookings"]

    sections = ["Бронирования"]

    if reservations:
        bookings_message = "Ваши записи:\n\n"
        for res in reservations:
            bus = next((b for b in buses if b.id == res.bus_id), None)
            if bus:
                bookings_message += format_booking_info(res, bus) + "\n"
            else:
                bookings_message += f"Автобус ID {res.bus_id} (бронирование закрыто)\n"
        sections.append(bookings_message.strip())

    if waiting_records:
        waiting_message = "Вы в листе ожидания:\n\n"
        for record in waiting_records:
            bus = next((b for b in buses if b.id == record.bus_id), None)
            waiting_message += format_waiting_info(record, bus) + "\n"
        sections.append(waiting_message.strip())

    return "\n\n".join(sections)


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
