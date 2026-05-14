"""
Репозитории для работы с данными
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from database.connection import db_connection
from models.entities import (
    Bus,
    BusOwner,
    ManualReservation,
    Passenger,
    Reservation,
    WaitingListRecord,
)

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
    def update_personal_data(
        username: str,
        last_name: str,
        first_name: str,
        patronymic: Optional[str],
        phone: str,
        birth_date: str,
        passport_number: str,
        citizenship: str,
    ) -> None:
        """Обновляет персональные данные пассажира"""
        fio_parts = [last_name.strip(), first_name.strip()]
        if patronymic and patronymic.strip():
            fio_parts.append(patronymic.strip())

        db_connection.execute_query(
            """
            UPDATE Passengers
            SET LastName = ?,
                FirstName = ?,
                Patronymic = ?,
                FIO = ?,
                Phone = ?,
                BirthDate = ?,
                PassportNumber = ?,
                Citizenship = ?,
                PersonalDataConfirmed = TRUE
            WHERE Telegram_username = ?
            """,
            (
                last_name.strip(),
                first_name.strip(),
                patronymic.strip() if patronymic and patronymic.strip() else None,
                " ".join(fio_parts),
                phone.strip(),
                birth_date.strip(),
                passport_number.strip(),
                citizenship.strip(),
                username,
            ),
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
            "SELECT b.* FROM Buses b JOIN BusOwners bo ON b.ID = bo.BusID WHERE bo.chiefID = ?",
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
        if status == "Yes":
            db_connection.execute_query(
                "UPDATE WaitingList SET NotificationSent = ?, NotificationSentAt = ? WHERE ID = ?",
                (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), record_id),
            )
            return

        db_connection.execute_query(
            "UPDATE WaitingList SET NotificationSent = ?, NotificationSentAt = NULL WHERE ID = ?",
            (status, record_id),
        )

    @staticmethod
    def update_status(record_id: int, status: str) -> None:
        """Обновляет статус записи"""
        db_connection.execute_query(
            "UPDATE WaitingList SET Status = ? WHERE ID = ?", (status, record_id)
        )

    @staticmethod
    def update_request_time(record_id: int, request_time: str) -> None:
        """Обновляет время заявки для перестановки в конец очереди"""
        db_connection.execute_query(
            "UPDATE WaitingList SET RequestTime = ? WHERE ID = ?",
            (request_time, record_id),
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

    @staticmethod
    def get_by_passenger(passenger_id: int) -> List[WaitingListRecord]:
        """Получает активные записи листа ожидания по пассажиру"""
        results = db_connection.execute_query(
            "SELECT * FROM WaitingList WHERE PassengerID = ? AND Status = 'Waiting'",
            (passenger_id,),
            fetch_all=True,
        )
        return [WaitingListRecord.from_tuple(row) for row in results] if results else []

    @staticmethod
    def delete_by_passenger_and_bus(passenger_id: int, bus_id: int) -> None:
        """Удаляет активные записи ожидания по пассажиру и автобусу"""
        db_connection.execute_query(
            "DELETE FROM WaitingList WHERE PassengerID = ? AND BusID = ? AND Status = 'Waiting'",
            (passenger_id, bus_id),
        )


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


class ManualReservationRepository:
    """Репозиторий для работы с ручными резервациями"""

    @staticmethod
    def _normalize_username(username: Optional[str]) -> str:
        if not username:
            return ""
        return username.strip().lstrip("@").lower()

    @staticmethod
    def get_all() -> List[ManualReservation]:
        """Получает все ручные резервации"""
        results = db_connection.execute_query(
            "SELECT * FROM ManualReservations", fetch_all=True
        )
        return [ManualReservation.from_tuple(row) for row in results] if results else []

    @staticmethod
    def create(telegram_username: str, bus_id: int, is_booked: bool = False) -> None:
        """
        Создает или обновляет ручную резервацию.
        В случае конфликта по пользователю и автобусу обновляет флаг брони.
        """
        db_connection.execute_query(
            """
            INSERT INTO ManualReservations (TelegramUsername, BusID, IsBooked)
            VALUES (?, ?, ?)
            ON CONFLICT(TelegramUsername, BusID)
            DO UPDATE SET IsBooked = excluded.IsBooked
            """,
            (telegram_username, bus_id, bool(is_booked)),
        )

    @staticmethod
    def has_unbooked_by_username_and_bus(telegram_username: str, bus_id: int) -> bool:
        """Проверяет, есть ли незакрытая ручная резервация для пользователя и автобуса"""
        normalized_username = ManualReservationRepository._normalize_username(
            telegram_username
        )
        if not normalized_username:
            return False

        result = db_connection.execute_query(
            """
            SELECT 1
            FROM ManualReservations
            WHERE BusID = ?
              AND (IsBooked = FALSE OR IsBooked IS NULL)
              AND lower(ltrim(TelegramUsername, '@')) = ?
            LIMIT 1
            """,
            (bus_id, normalized_username),
            fetch_one=True,
        )
        return bool(result)

    @staticmethod
    def get_unbooked_count_by_bus(bus_id: int) -> int:
        """Возвращает количество незакрытых ручных резерваций по автобусу"""
        result = db_connection.execute_query(
            """
            SELECT COUNT(*)
            FROM ManualReservations
            WHERE BusID = ?
              AND (IsBooked = FALSE OR IsBooked IS NULL)
            """,
            (bus_id,),
            fetch_one=True,
        )
        return int(result[0]) if result else 0

    @staticmethod
    def get_unbooked_counts_by_bus(bus_ids: List[int]) -> Dict[int, int]:
        """Возвращает количество незакрытых ручных резерваций по списку автобусов"""
        if not bus_ids:
            return {}

        placeholders = ", ".join(["?"] * len(bus_ids))
        results = db_connection.execute_query(
            f"""
            SELECT BusID, COUNT(*)
            FROM ManualReservations
            WHERE BusID IN ({placeholders})
              AND (IsBooked = FALSE OR IsBooked IS NULL)
            GROUP BY BusID
            """,
            tuple(bus_ids),
            fetch_all=True,
        )
        if not results:
            return {}

        return {int(row[0]): int(row[1]) for row in results}

    @staticmethod
    def mark_booked_by_username_and_bus(telegram_username: str, bus_id: int) -> None:
        """Отмечает ручную резервацию как использованную после фактического бронирования"""
        normalized_username = ManualReservationRepository._normalize_username(
            telegram_username
        )
        if not normalized_username:
            return

        db_connection.execute_query(
            """
            UPDATE ManualReservations
            SET IsBooked = TRUE
            WHERE BusID = ?
              AND (IsBooked = FALSE OR IsBooked IS NULL)
              AND lower(ltrim(TelegramUsername, '@')) = ?
            """,
            (bus_id, normalized_username),
        )
