"""
Сервис для работы с автобусами
"""

import logging
from typing import List, Optional

from database.repositories import BusRepository, ReservationRepository
from models.entities import Bus

logger = logging.getLogger(__name__)


class BusService:
    """Сервис для работы с автобусами"""

    def __init__(self):
        self.bus_repository = BusRepository()
        self.reservation_repository = ReservationRepository()

    def get_available_directions(self) -> List[str]:
        """Получает список доступных направлений"""
        buses = self.bus_repository.get_active_buses()
        directions = sorted(
            set(
                bus.direction
                for bus in buses
                if bus.direction and bus.direction.strip()
            ),
            reverse=True,
        )
        return directions

    def get_buses_for_direction(self, direction: str) -> List[Bus]:
        """Получает автобусы для указанного направления"""
        return self.bus_repository.get_by_direction(direction)

    def get_bus_availability_info(self, bus: Bus) -> dict:
        """
        Получает информацию о доступности мест в автобусе

        Returns:
            dict: {
                'capacity': int,
                'booked': int,
                'free': int,
                'is_available': bool
            }
        """
        reservations = self.reservation_repository.get_by_bus(bus.id)
        booked = len(reservations)
        free = bus.capacity - booked

        return {
            "capacity": bus.capacity,
            "booked": booked,
            "free": free,
            "is_available": free > 0,
        }

    def get_bus_by_id(self, bus_id: int) -> Optional[Bus]:
        """Получает автобус по ID"""
        return self.bus_repository.get_by_id(bus_id)

    def get_all_buses(self) -> List[Bus]:
        """Получает все автобусы"""
        return self.bus_repository.get_all()

    def get_active_buses(self) -> List[Bus]:
        """Получает только активные автобусы"""
        return self.bus_repository.get_active_buses()

    def get_buses_by_chief(self, chief_id: int) -> List[Bus]:
        """Получает автобусы по шефу"""
        return self.bus_repository.get_by_chief(chief_id)
