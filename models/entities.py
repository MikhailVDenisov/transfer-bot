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
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    patronymic: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    passport_number: Optional[str] = None
    citizenship: Optional[str] = None
    personal_data_confirmed: bool = False
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
            passport_number=data[7] if len(data) > 7 else None,
            citizenship=data[8] if len(data) > 8 else None,
            last_name=data[9] if len(data) > 9 else None,
            first_name=data[10] if len(data) > 10 else None,
            patronymic=data[11] if len(data) > 11 else None,
            birth_date=data[12] if len(data) > 12 else None,
            personal_data_confirmed=bool(data[13]) if len(data) > 13 else False,
        )

    def is_admin(self) -> bool:
        """Проверяет, является ли пассажир администратором"""
        return self.role and self.role.lower() == "admin"

    def is_chief(self) -> bool:
        """Проверяет, является ли пассажир шефом автобуса"""
        return self.role and self.role.lower() == "chief"

    def has_personal_data(self) -> bool:
        """Проверяет, заполнены ли обязательные персональные данные"""
        return all(
            [
                self.last_name and self.last_name.strip(),
                self.first_name and self.first_name.strip(),
                self.phone and self.phone.strip(),
                self.birth_date and self.birth_date.strip(),
                self.passport_number and self.passport_number.strip(),
            ]
        )

    def has_confirmed_personal_data(self) -> bool:
        """Проверяет, заполнены и подтверждены ли персональные данные"""
        return self.has_personal_data() and self.personal_data_confirmed


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
    notification_sent_at: Optional[str] = None

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
            notification_sent_at=data[6] if len(data) > 6 else None,
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


@dataclass
class ManualReservation:
    """Модель ручной резервации места в автобусе"""

    id: Optional[int] = None
    telegram_username: Optional[str] = None
    bus_id: Optional[int] = None
    is_booked: bool = False
    created_at: Optional[str] = None

    @classmethod
    def from_tuple(cls, data: tuple) -> "ManualReservation":
        """Создает объект ManualReservation из кортежа данных из БД"""
        return cls(
            id=data[0],
            telegram_username=data[1],
            bus_id=data[2],
            is_booked=bool(data[3]) if len(data) > 3 else False,
            created_at=data[4] if len(data) > 4 else None,
        )
