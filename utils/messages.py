"""
Утилиты для форматирования сообщений
"""

from typing import List

from config.settings import MESSAGES
from models.entities import Bus, Reservation


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
