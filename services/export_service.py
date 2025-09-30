"""
Сервис для экспорта данных
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import List

import openpyxl

from database.repositories import (
    BusOwnerRepository,
    BusRepository,
    PassengerRepository,
    ReservationRepository,
)
from models.entities import Bus, BusOwner, Passenger, Reservation

logger = logging.getLogger(__name__)


class ExportService:
    """Сервис для экспорта данных"""

    def __init__(self):
        self.bus_repository = BusRepository()
        self.reservation_repository = ReservationRepository()
        self.passenger_repository = PassengerRepository()
        self.bus_owner_repository = BusOwnerRepository()

    async def export_buses_to_excel(self) -> str:
        """
        Экспортирует данные об автобусах в Excel файл

        Returns:
            str: Путь к временному файлу
        """
        try:
            # Получаем данные из базы
            buses = self.bus_repository.get_all()
            reservations = self.reservation_repository.get_all()
            passengers = self.passenger_repository.get_all()
            bus_owners = self.bus_owner_repository.get_all()

            # Создаем временный файл
            temp_file = f"temp_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            # Генерируем Excel файл в отдельном потоке
            await asyncio.to_thread(
                self._generate_excel_file,
                buses,
                reservations,
                passengers,
                bus_owners,
                temp_file,
            )

            return temp_file

        except Exception as e:
            logger.error(f"Ошибка при экспорте данных: {str(e)}")
            raise

    def _generate_excel_file(
        self,
        buses: List[Bus],
        reservations: List[Reservation],
        passengers: List[Passenger],
        bus_owners: List[BusOwner],
        filename: str,
    ):
        """Генерирует Excel файл с данными"""
        wb = openpyxl.Workbook()

        # Если нет автобусов, оставляем дефолтный лист с сообщением
        if not buses:
            ws = wb.active
            ws.title = "Нет данных"
            ws.append(["Данные об автобусах отсутствуют"])
            wb.save(filename)
            return

        wb.remove(wb.active)  # Удаляем дефолтный лист только если есть данные

        # Группируем пассажиров по автобусам
        bus_passengers = {}
        for res in reservations:
            bus_id = str(res.bus_id)
            passenger = next(
                (p for p in passengers if str(p.id) == str(res.passenger_id)), None
            )
            if passenger:
                if bus_id not in bus_passengers:
                    bus_passengers[bus_id] = []
                bus_passengers[bus_id].append(passenger)

        # Создаем листы для каждого автобуса
        for bus in buses:
            bus_id = str(bus.id)
            sheet_name = f"Автобус {bus.number}"[:31]  # Ограничиваем длину имени листа
            ws = wb.create_sheet(title=sheet_name)

            # Добавляем заголовок с информацией об автобусе
            bus_info = [
                f"Автобус: {bus.number}",
                f"Маршрут: {bus.departure_place} - {bus.destination}",
                f"Направление: {bus.direction}",
                f"Дата/время: {bus.departure_date} {bus.departure_time}",
                f"Вместимость: {bus.capacity}",
            ]

            # Находим ответственных за автобус
            owners = [o for o in bus_owners if str(o.bus_id) == bus_id]
            responsible_persons = []
            for owner in owners:
                chief = next(
                    (p for p in passengers if str(p.id) == str(owner.chief_id)), None
                )
                if chief:
                    responsible_persons.append(
                        f"{chief.fio} (@{chief.telegram_username})"
                    )

            if responsible_persons:
                bus_info.append(f"Ответственные: {', '.join(responsible_persons)}")

            # Записываем информацию об автобусе
            for line in bus_info:
                ws.append([line])

            # Пустая строка для разделения
            ws.append([])

            # Заголовки таблицы пассажиров
            ws.append(["№", "ФИО", "Username", "Телефон", "Комментарий"])

            # Данные пассажиров
            for idx, passenger in enumerate(bus_passengers.get(bus_id, []), start=1):
                ws.append(
                    [
                        idx,
                        passenger.fio or "",
                        (
                            f"@{passenger.telegram_username}"
                            if passenger.telegram_username
                            else ""
                        ),
                        passenger.phone or "",
                        passenger.comment or "",
                    ]
                )

        wb.save(filename)

    def cleanup_temp_file(self, filepath: str):
        """Удаляет временный файл"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            logger.error(f"Ошибка при удалении временного файла {filepath}: {str(e)}")
