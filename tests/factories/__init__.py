"""
Универсальный импорт фабрик с автоматическим выбором версии
"""

import sys


def get_factories():
    """Возвращает доступные фабрики с автоматическим выбором версии"""

    # Используем надежные фабрики (не зависят от внешних библиотек)
    try:
        from .robust_factories import RobustBusFactory as BusFactory
        from .robust_factories import RobustBusOwnerFactory as BusOwnerFactory
        from .robust_factories import RobustPassengerFactory as PassengerFactory
        from .robust_factories import RobustReservationFactory as ReservationFactory
        from .robust_factories import (
            RobustWaitingListRecordFactory as WaitingListRecordFactory,
        )

        print("✅ Используются надежные фабрики (без внешних зависимостей)")
        return {
            "PassengerFactory": PassengerFactory,
            "BusFactory": BusFactory,
            "ReservationFactory": ReservationFactory,
            "WaitingListRecordFactory": WaitingListRecordFactory,
            "BusOwnerFactory": BusOwnerFactory,
        }
    except ImportError as e:
        print(f"⚠️ Надежные фабрики недоступны: {e}")

        # Fallback на простые фабрики
        try:
            from .simple_factories import SimpleBusFactory as BusFactory
            from .simple_factories import SimpleBusOwnerFactory as BusOwnerFactory
            from .simple_factories import SimplePassengerFactory as PassengerFactory
            from .simple_factories import SimpleReservationFactory as ReservationFactory
            from .simple_factories import (
                SimpleWaitingListRecordFactory as WaitingListRecordFactory,
            )

            print("✅ Используются простые фабрики (fallback)")
            return {
                "PassengerFactory": PassengerFactory,
                "BusFactory": BusFactory,
                "ReservationFactory": ReservationFactory,
                "WaitingListRecordFactory": WaitingListRecordFactory,
                "BusOwnerFactory": BusOwnerFactory,
            }
        except ImportError as e2:
            print(f"❌ Все фабрики недоступны: {e2}")
            raise ImportError("Не удалось загрузить ни одну версию фабрик")


# Автоматически загружаем фабрики при импорте модуля
factories = get_factories()

# Экспортируем фабрики
PassengerFactory = factories["PassengerFactory"]
BusFactory = factories["BusFactory"]
ReservationFactory = factories["ReservationFactory"]
WaitingListRecordFactory = factories["WaitingListRecordFactory"]
BusOwnerFactory = factories["BusOwnerFactory"]

__all__ = [
    "PassengerFactory",
    "BusFactory",
    "ReservationFactory",
    "WaitingListRecordFactory",
    "BusOwnerFactory",
]
