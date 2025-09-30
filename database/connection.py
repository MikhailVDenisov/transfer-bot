"""
Модуль для работы с подключением к базе данных
"""

import logging
import sqlite3
from typing import Any, List, Optional, Tuple

from config.settings import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Класс для управления подключением к базе данных"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """Получает подключение к базе данных"""
        return sqlite3.connect(self.db_path)

    def execute_query(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False,
    ) -> Optional[Any]:
        """
        Выполняет SQL запрос

        Args:
            query: SQL запрос
            params: Параметры для запроса
            fetch_one: Возвращать одну запись
            fetch_all: Возвращать все записи

        Returns:
            Результат запроса или None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)

            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                result = None

            conn.commit()
            conn.close()
            return result

        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {str(e)}")
            if "conn" in locals():
                conn.close()
            raise

    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """
        Выполняет SQL запрос для множества параметров

        Args:
            query: SQL запрос
            params_list: Список параметров для запроса
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Ошибка выполнения множественного запроса: {str(e)}")
            if "conn" in locals():
                conn.close()
            raise


# Глобальный экземпляр для использования в приложении
db_connection = DatabaseConnection()
