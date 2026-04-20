import logging
from typing import Dict, Optional, Tuple

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

    def update_personal_data(
        self, username: str, data: Dict[str, str]
    ) -> Tuple[bool, str]:
        """Обновляет персональные данные пассажира"""
        try:
            self.repository.update_personal_data(
                username=username,
                last_name=data["last_name"],
                first_name=data["first_name"],
                patronymic=data.get("patronymic"),
                phone=data["phone"],
                birth_date=data["birth_date"],
                passport_number=data["passport_number"],
                citizenship=data["citizenship"],
            )
            return True, ""
        except Exception as e:
            logger.error(f"Ошибка при обновлении персональных данных: {str(e)}")
            return False, "Не удалось сохранить персональные данные"

    def is_admin(self, username: str) -> bool:
        """Проверяет, является ли пользователь администратором"""
        passenger = self.repository.get_by_username(username)
        return passenger.is_admin() if passenger else False

    def is_chief(self, username: str) -> bool:
        """Проверяет, является ли пользователь шефом автобуса"""
        passenger = self.repository.get_by_username(username)
        return passenger.is_chief() if passenger else False
