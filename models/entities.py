"""
Модели данных для приложения трансфер-бота
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Passenger:
    """Модель пассажира"""

    id: Optional[int] = None
    telegram_username: Optional[str] = None
    chat_id: Optional[str] = None
    fio: Optional[str] = None
    phone: Optional[str] = None
    comment: Optional[str] = None
    role: str = "user"

    @classmethod
    def from_tuple(cls, data: tuple) -> "Passenger":
        """Создает объект Passenger из кортежа данных из БД"""
        return cls(
            id=data[0],
            telegram_username=data[1],
            chat_id=data[2],
            fio=data[3],
            phone=data[4],
            comment=data[5],
            role=data[6] if len(data) > 6 else "user",
        )

    def is_admin(self) -> bool:
        """Проверяет, является ли пассажир администратором"""
        return self.role and self.role.lower() == "admin"

    def is_chief(self) -> bool:
        """Проверяет, является ли пассажир шефом автобуса"""
        return self.role and self.role.lower() == "chief"

    def has_fio(self) -> bool:
        """Проверяет, заполнено ли ФИО"""
        return bool(self.fio and self.fio.strip())


@dataclass
class Bus:
    """Модель автобуса"""

    id: Optional[int] = None
    number: Optional[str] = None
    departure_place: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    departure_time: Optional[str] = None
    capacity: Optional[int] = None
    direction: Optional[str] = None
    is_active: bool = True

    @classmethod
    def from_tuple(cls, data: tuple) -> "Bus":
        """Создает объект Bus из кортежа данных из БД"""
        return cls(
            id=data[0],
            number=data[1],
            departure_place=data[2],
            destination=data[3],
            departure_date=data[4],
            departure_time=data[5],
            capacity=data[6],
            direction=data[7] if len(data) > 7 else None,
            is_active=bool(data[8]) if len(data) > 8 else True,
        )

    def get_route(self) -> str:
        """Возвращает строку маршрута"""
        return f"{self.departure_place}-{self.destination}"

    def get_departure_info(self) -> str:
        """Возвращает информацию о времени отправления"""
        return f"{self.departure_date} {self.departure_time}"


@dataclass
class Reservation:
    """Модель бронирования"""

    id: Optional[int] = None
    passenger_id: Optional[int] = None
    bus_id: Optional[int] = None
    reservation_date: Optional[str] = None
    direction: Optional[str] = None

    @classmethod
    def from_tuple(cls, data: tuple) -> "Reservation":
        """Создает объект Reservation из кортежа данных из БД"""
        return cls(
            id=data[0],
            passenger_id=data[1],
            bus_id=data[2],
            reservation_date=data[3],
            direction=data[4],
        )


@dataclass
class WaitingListRecord:
    """Модель записи в листе ожидания"""

    id: Optional[int] = None
    passenger_id: Optional[int] = None
    bus_id: Optional[int] = None
    request_time: Optional[str] = None
    status: str = "Waiting"
    notification_sent: str = "No"

    @classmethod
    def from_tuple(cls, data: tuple) -> "WaitingListRecord":
        """Создает объект WaitingListRecord из кортежа данных из БД"""
        return cls(
            id=data[0],
            passenger_id=data[1],
            bus_id=data[2],
            request_time=data[3],
            status=data[4] if len(data) > 4 else "Waiting",
            notification_sent=data[5] if len(data) > 5 else "No",
        )

    def is_waiting(self) -> bool:
        """Проверяет, находится ли запись в статусе ожидания"""
        return self.status == "Waiting"

    def is_confirmed(self) -> bool:
        """Проверяет, подтверждена ли запись"""
        return self.status == "Confirmed"

    def is_notification_sent(self) -> bool:
        """Проверяет, отправлено ли уведомление"""
        return self.notification_sent == "Yes"


@dataclass
class BusOwner:
    """Модель владельца автобуса"""

    id: Optional[int] = None
    bus_id: Optional[int] = None
    chief_id: Optional[int] = None

    @classmethod
    def from_tuple(cls, data: tuple) -> "BusOwner":
        """Создает объект BusOwner из кортежа данных из БД"""
        return cls(id=data[0], bus_id=data[1], chief_id=data[2])
