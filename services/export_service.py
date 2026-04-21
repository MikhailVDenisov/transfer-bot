"""
Сервис для экспорта данных
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List

import openpyxl

from database.repositories import (
    BusOwnerRepository,
    BusRepository,
    PassengerRepository,
    ReservationRepository,
    WaitingListRepository,
)
from models.entities import Bus, BusOwner, Passenger, Reservation, WaitingListRecord

logger = logging.getLogger(__name__)


class ExportService:
    """Сервис для экспорта данных"""

    def __init__(self):
        self.bus_repository = BusRepository()
        self.reservation_repository = ReservationRepository()
        self.passenger_repository = PassengerRepository()
        self.bus_owner_repository = BusOwnerRepository()
        self.waiting_list_repository = WaitingListRepository()

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

    async def export_personal_data_to_excel(self, bus_ids: List[int]) -> str:
        """
        Экспортирует персональные данные пассажиров и лист ожидания по выбранным автобусам

        Returns:
            str: Путь к временному файлу
        """
        try:
            buses = [
                bus
                for bus in self.bus_repository.get_all()
                if bus.id in {int(bus_id) for bus_id in bus_ids}
            ]
            passengers = self.passenger_repository.get_all()
            reservations = self.reservation_repository.get_all()
            waiting_records = self.waiting_list_repository.get_waiting_records()

            temp_file = f"temp_personal_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            await asyncio.to_thread(
                self._generate_personal_data_excel_file,
                buses,
                passengers,
                reservations,
                waiting_records,
                temp_file,
            )

            return temp_file

        except Exception as e:
            logger.error(f"Ошибка при экспорте персональных данных: {str(e)}")
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

    def _generate_personal_data_excel_file(
        self,
        buses: List[Bus],
        passengers: List[Passenger],
        reservations: List[Reservation],
        waiting_records: List[WaitingListRecord],
        filename: str,
    ):
        """Генерирует Excel файл с персональными данными по выбранным автобусам"""
        wb = openpyxl.Workbook()

        if not buses:
            ws = wb.active
            ws.title = "Нет данных"
            ws.append(["Нет автобусов для выгрузки персональных данных"])
            wb.save(filename)
            return

        wb.remove(wb.active)
        passengers_by_id: Dict[int, Passenger] = {
            passenger.id: passenger
            for passenger in passengers
            if passenger.id is not None
        }

        reservations_by_bus: Dict[int, List[Reservation]] = {}
        for reservation in reservations:
            reservations_by_bus.setdefault(reservation.bus_id, []).append(reservation)

        waiting_by_bus: Dict[int, List[WaitingListRecord]] = {}
        for waiting_record in waiting_records:
            waiting_by_bus.setdefault(waiting_record.bus_id, []).append(waiting_record)

        for bus in buses:
            sheet_name = f"Автобус {bus.number}"[:31]
            ws = wb.create_sheet(title=sheet_name)

            bus_info = [
                f"Автобус: {bus.number}",
                f"Маршрут: {bus.departure_place} - {bus.destination}",
                f"Направление: {bus.direction}",
                f"Дата/время: {bus.departure_date} {bus.departure_time}",
            ]

            for line in bus_info:
                ws.append([line])

            ws.append([])
            ws.append(
                [
                    "№",
                    "Статус",
                    "Фамилия",
                    "Имя",
                    "Отчество",
                    "Телефон",
                    "Дата рождения",
                    "Паспорт",
                    "Гражданство",
                    "Telegram",
                    "Дата добавления",
                ]
            )

            row_number = 1

            bus_reservations = sorted(
                reservations_by_bus.get(bus.id, []),
                key=lambda item: item.reservation_date or "",
            )
            for reservation in bus_reservations:
                passenger = passengers_by_id.get(reservation.passenger_id)
                if not passenger:
                    continue

                ws.append(
                    [
                        row_number,
                        "Пассажир",
                        passenger.last_name or "",
                        passenger.first_name or "",
                        passenger.patronymic or "",
                        passenger.phone or "",
                        passenger.birth_date or "",
                        passenger.passport_number or "",
                        passenger.citizenship or "",
                        (
                            f"@{passenger.telegram_username}"
                            if passenger.telegram_username
                            else ""
                        ),
                        reservation.reservation_date or "",
                    ]
                )
                row_number += 1

            bus_waiting_records = sorted(
                waiting_by_bus.get(bus.id, []),
                key=lambda item: item.request_time or "",
            )
            for waiting_record in bus_waiting_records:
                passenger = passengers_by_id.get(waiting_record.passenger_id)
                if not passenger:
                    continue

                ws.append(
                    [
                        row_number,
                        "Очередь",
                        passenger.last_name or "",
                        passenger.first_name or "",
                        passenger.patronymic or "",
                        passenger.phone or "",
                        passenger.birth_date or "",
                        passenger.passport_number or "",
                        passenger.citizenship or "",
                        (
                            f"@{passenger.telegram_username}"
                            if passenger.telegram_username
                            else ""
                        ),
                        waiting_record.request_time or "",
                    ]
                )
                row_number += 1

            if row_number == 1:
                ws.append(["Нет пассажиров и записей в очереди"])

        wb.save(filename)

    def cleanup_temp_file(self, filepath: str):
        """Удаляет временный файл"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            logger.error(f"Ошибка при удалении временного файла {filepath}: {str(e)}")
