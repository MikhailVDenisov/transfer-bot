"""
Сервис для работы с пассажирами
"""

import logging
from typing import Optional, Tuple

from database.repositories import PassengerRepository
from models.entities import Passenger

logger = logging.getLogger(__name__)


class PassengerService:
    """Сервис для работы с пассажирами"""

    def __init__(self):
        self.repository = PassengerRepository()

    def get_or_create_passenger(
        self, username: str, chat_id: Optional[str] = None
    ) -> Tuple[Passenger, bool]:
        """
        Получает пассажира или создает нового

        Returns:
            Tuple[Passenger, bool]: (пассажир, был_ли_создан_новый)
        """
        passenger = self.repository.get_by_username(username)

        if passenger:
            # Обновляем chat_id если он пустой
            if not passenger.chat_id and chat_id:
                self.repository.update_chat_id(username, chat_id)
                passenger.chat_id = chat_id
            return passenger, False
        else:
            # Создаем нового пассажира
            passenger = self.repository.create(username, chat_id)
            return passenger, True

    def check_user_fio(self, username: str) -> Tuple[bool, Optional[Passenger]]:
        """
        Проверяет, есть ли у пользователя заполненное ФИО

        Returns:
            Tuple[bool, Optional[Passenger]]: (есть_ли_фио, пассажир)
        """
        try:
            passenger = self.repository.get_by_username(username)
            if passenger and passenger.has_fio():
                return True, passenger
            return False, passenger
        except Exception as e:
            logger.error(f"Ошибка при проверке ФИО: {str(e)}")
            return False, None

    def update_fio(self, username: str, fio: str) -> bool:
        """
        Обновляет ФИО пассажира

        Returns:
            bool: Успешность операции
        """
        try:
            if not fio or len(fio.strip()) < 5:
                return False

            self.repository.update_fio(username, fio.strip())
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении ФИО: {str(e)}")
            return False

    def is_admin(self, username: str) -> bool:
        """Проверяет, является ли пользователь администратором"""
        passenger = self.repository.get_by_username(username)
        return passenger.is_admin() if passenger else False

    def is_chief(self, username: str) -> bool:
        """Проверяет, является ли пользователь шефом автобуса"""
        passenger = self.repository.get_by_username(username)
        return passenger.is_chief() if passenger else False
