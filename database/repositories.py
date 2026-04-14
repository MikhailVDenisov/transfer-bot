"""
Репозитории для работы с данными
"""

import logging
from datetime import datetime
from typing import List, Optional

from database.connection import db_connection
from models.entities import Bus, BusOwner, Passenger, Reservation, WaitingListRecord

logger = logging.getLogger(__name__)


class PassengerRepository:
    """Репозиторий для работы с пассажирами"""

    @staticmethod
    def get_by_username(username: str) -> Optional[Passenger]:
        """Получает пассажира по username"""
        result = db_connection.execute_query(
            "SELECT * FROM Passengers WHERE Telegram_username = ?",
            (username,),
            fetch_one=True,
        )
        return Passenger.from_tuple(result) if result else None

    @staticmethod
    def create(username: str, chat_id: Optional[str] = None) -> Passenger:
        """Создает нового пассажира"""
        db_connection.execute_query(
            "INSERT INTO Passengers (Telegram_username, ChatID) VALUES (?, ?)",
            (username, str(chat_id) if chat_id else None),
        )
        return PassengerRepository.get_by_username(username)

    @staticmethod
    def update_chat_id(username: str, chat_id: str) -> None:
        """Обновляет chat_id пассажира"""
        db_connection.execute_query(
            "UPDATE Passengers SET ChatID = ? WHERE Telegram_username = ?",
            (str(chat_id), username),
        )

    @staticmethod
    def update_fio(username: str, fio: str) -> None:
        """Обновляет ФИО пассажира"""
        db_connection.execute_query(
            "UPDATE Passengers SET FIO = ? WHERE Telegram_username = ?", (fio, username)
        )

    @staticmethod
    def get_all() -> List[Passenger]:
        """Получает всех пассажиров"""
        results = db_connection.execute_query(
            "SELECT * FROM Passengers", fetch_all=True
        )
        return [Passenger.from_tuple(row) for row in results] if results else []

    @staticmethod
    def get_by_bus(bus_id: int) -> List[Passenger]:
        """Получает пассажиров по автобусу и направлению"""
        results = db_connection.execute_query(
            "SELECT p.* FROM Passengers p JOIN Reservations r ON p.ID = r.PassengerID  WHERE r.BusID = ?",
            (bus_id,),
            fetch_all=True,
        )

        return [Passenger.from_tuple(row) for row in results] if results else []


class BusRepository:
    """Репозиторий для работы с автобусами"""

    @staticmethod
    def get_all() -> List[Bus]:
        """Получает все автобусы"""
        results = db_connection.execute_query("SELECT * FROM Buses", fetch_all=True)
        return [Bus.from_tuple(row) for row in results] if results else []

    @staticmethod
    def get_by_id(bus_id: int) -> Optional[Bus]:
        """Получает автобус по ID"""
        result = db_connection.execute_query(
            "SELECT * FROM Buses WHERE ID = ?", (bus_id,), fetch_one=True
        )
        return Bus.from_tuple(result) if result else None

    @staticmethod
    def get_active_buses() -> List[Bus]:
        """Получает только активные автобусы"""
        results = db_connection.execute_query(
            "SELECT * FROM Buses WHERE is_active = TRUE OR is_active IS NULL",
            fetch_all=True,
        )
        return [Bus.from_tuple(row) for row in results] if results else []

    @staticmethod
    def get_by_direction(direction: str) -> List[Bus]:
        """Получает автобусы по направлению"""
        results = db_connection.execute_query(
            "SELECT * FROM Buses WHERE Direction = ? AND (is_active = TRUE OR is_active IS NULL)",
            (direction,),
            fetch_all=True,
        )
        return [Bus.from_tuple(row) for row in results] if results else []

    @staticmethod
    def get_by_chief(chief_id: int) -> List[Bus]:
        """Получает автобусы по владельцу и направлению"""
        results = db_connection.execute_query(
            "SELECT b.* FROM Buses b JOIN BusOwners bo ON b.ID = bo.BusID WHERE bo.chiefID = ? AND (is_active = TRUE OR is_active IS NULL)",
            (chief_id,),
            fetch_all=True,
        )
        return [Bus.from_tuple(row) for row in results] if results else []


class ReservationRepository:
    """Репозиторий для работы с бронированиями"""

    @staticmethod
    def get_all() -> List[Reservation]:
        """Получает все бронирования"""
        results = db_connection.execute_query(
            "SELECT * FROM Reservations", fetch_all=True
        )
        return [Reservation.from_tuple(row) for row in results] if results else []

    @staticmethod
    def get_by_bus(bus_id: int) -> List[Reservation]:
        """Получает бронирования по автобусу"""
        results = db_connection.execute_query(
            "SELECT * FROM Reservations WHERE BusID = ?", (bus_id,), fetch_all=True
        )
        return [Reservation.from_tuple(row) for row in results] if results else []

    @staticmethod
    def get_by_passenger(passenger_id: int) -> List[Reservation]:
        """Получает бронирования по пассажиру"""
        results = db_connection.execute_query(
            "SELECT * FROM Reservations WHERE PassengerID = ?",
            (passenger_id,),
            fetch_all=True,
        )
        return [Reservation.from_tuple(row) for row in results] if results else []

    @staticmethod
    def create(passenger_id: int, bus_id: int, direction: str) -> None:
        """Создает новое бронирование"""
        db_connection.execute_query(
            "INSERT INTO Reservations (PassengerID, BusID, ReservationDate, Direction) VALUES (?, ?, ?, ?)",
            (
                passenger_id,
                bus_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                direction,
            ),
        )

    @staticmethod
    def delete_by_id(reservation_id: int) -> None:
        """Удаляет бронирование по ID"""
        db_connection.execute_query(
            "DELETE FROM Reservations WHERE ID = ?", (reservation_id,)
        )

    @staticmethod
    def get_by_id_and_passenger(
        reservation_id: int, passenger_id: int
    ) -> Optional[Reservation]:
        """Получает бронирование по ID и пассажиру"""
        result = db_connection.execute_query(
            "SELECT * FROM Reservations WHERE ID = ? AND PassengerID = ?",
            (reservation_id, passenger_id),
            fetch_one=True,
        )
        return Reservation.from_tuple(result) if result else None


class WaitingListRepository:
    """Репозиторий для работы с листом ожидания"""

    @staticmethod
    def get_all() -> List[WaitingListRecord]:
        """Получает все записи листа ожидания"""
        results = db_connection.execute_query(
            "SELECT * FROM WaitingList", fetch_all=True
        )
        return [WaitingListRecord.from_tuple(row) for row in results] if results else []

    @staticmethod
    def create(passenger_id: int, bus_id: int) -> None:
        """Создает запись в листе ожидания"""
        db_connection.execute_query(
            "INSERT INTO WaitingList (PassengerID, BusID, RequestTime) VALUES (?, ?, ?)",
            (passenger_id, bus_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    @staticmethod
    def update_notification(record_id: int, status: str) -> None:
        """Обновляет статус уведомления"""
        db_connection.execute_query(
            "UPDATE WaitingList SET NotificationSent = ? WHERE ID = ?",
            (status, record_id),
        )

    @staticmethod
    def update_status(record_id: int, status: str) -> None:
        """Обновляет статус записи"""
        db_connection.execute_query(
            "UPDATE WaitingList SET Status = ? WHERE ID = ?", (status, record_id)
        )

    @staticmethod
    def get_waiting_records() -> List[WaitingListRecord]:
        """Получает записи в статусе ожидания"""
        results = db_connection.execute_query(
            "SELECT * FROM WaitingList WHERE Status = 'Waiting'", fetch_all=True
        )
        return [WaitingListRecord.from_tuple(row) for row in results] if results else []

    @staticmethod
    def get_by_passenger_and_bus(
        passenger_id: int, bus_id: int
    ) -> List[WaitingListRecord]:
        """Получает записи по пассажиру и автобусу"""
        results = db_connection.execute_query(
            "SELECT * FROM WaitingList WHERE PassengerID = ? AND BusID = ? AND Status = 'Waiting'",
            (passenger_id, bus_id),
            fetch_all=True,
        )
        return [WaitingListRecord.from_tuple(row) for row in results] if results else []


class BusOwnerRepository:
    """Репозиторий для работы с владельцами автобусов"""

    @staticmethod
    def get_all() -> List[BusOwner]:
        """Получает всех владельцев автобусов"""
        results = db_connection.execute_query("SELECT * FROM BusOwners", fetch_all=True)
        return [BusOwner.from_tuple(row) for row in results] if results else []

    @staticmethod
    def get_by_bus(bus_id: int) -> List[BusOwner]:
        """Получает владельцев по автобусу"""
        results = db_connection.execute_query(
            "SELECT * FROM BusOwners WHERE BusID = ?", (bus_id,), fetch_all=True
        )
        return [BusOwner.from_tuple(row) for row in results] if results else []
