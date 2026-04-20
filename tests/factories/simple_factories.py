"""
Простые фабрики для создания тестовых моделей данных (без polyfactory)
"""

from faker import Faker

from models.entities import Bus, BusOwner, Passenger, Reservation, WaitingListRecord

fake = Faker("ru_RU")

# Глобальные счетчики для уникальных значений
_username_counter = 0
_chat_id_counter = 200000000


class SimplePassengerFactory:
    """Простая фабрика для создания тестовых пассажиров"""

    @staticmethod
    def build(**kwargs):
        global _username_counter, _chat_id_counter
        _username_counter += 1
        _chat_id_counter += 1

        defaults = {
            "id": kwargs.get("id"),
            "telegram_username": kwargs.get(
                "telegram_username", f"test_user_{_username_counter}"
            ),
            "chat_id": kwargs.get("chat_id", str(_chat_id_counter)),
            "last_name": kwargs.get("last_name", fake.last_name()),
            "first_name": kwargs.get("first_name", fake.first_name()),
            "patronymic": kwargs.get("patronymic", fake.middle_name()),
            "fio": kwargs.get(
                "fio", f"{fake.last_name()} {fake.first_name()} {fake.middle_name()}"
            ),
            "phone": kwargs.get("phone", fake.phone_number()),
            "birth_date": kwargs.get("birth_date", fake.date(pattern="%d.%m.%Y")),
            "passport_number": kwargs.get("passport_number", "1234 567890"),
            "citizenship": kwargs.get("citizenship", "РФ"),
            "personal_data_confirmed": kwargs.get("personal_data_confirmed", True),
            "comment": kwargs.get("comment", fake.text(max_nb_chars=100)),
            "role": kwargs.get("role", "user"),  # По умолчанию user для тестов
        }
        defaults.update(kwargs)
        return Passenger(**defaults)


class SimpleBusFactory:
    """Простая фабрика для создания тестовых автобусов"""

    @staticmethod
    def build(**kwargs):
        defaults = {
            "id": kwargs.get("id"),
            "number": kwargs.get("number", f"БУС-{fake.random_int(min=1, max=999)}"),
            "departure_place": kwargs.get(
                "departure_place",
                fake.random_element(elements=("Москва", "Санкт-Петербург", "Казань")),
            ),
            "destination": kwargs.get(
                "destination",
                fake.random_element(
                    elements=("Переславль-Залесский", "Ярославль", "Кострома")
                ),
            ),
            "departure_date": kwargs.get(
                "departure_date", fake.date(pattern="%Y-%m-%d")
            ),
            "departure_time": kwargs.get("departure_time", fake.time(pattern="%H:%M")),
            "capacity": kwargs.get("capacity", fake.random_int(min=20, max=50)),
            "direction": kwargs.get(
                "direction", fake.random_element(elements=("Туда", "Обратно"))
            ),
            "is_active": kwargs.get(
                "is_active", fake.boolean(chance_of_getting_true=80)
            ),
        }
        defaults.update(kwargs)
        return Bus(**defaults)


class SimpleReservationFactory:
    """Простая фабрика для создания тестовых бронирований"""

    @staticmethod
    def build(**kwargs):
        defaults = {
            "id": kwargs.get("id"),
            "passenger_id": kwargs.get(
                "passenger_id", fake.random_int(min=1, max=1000)
            ),
            "bus_id": kwargs.get("bus_id", fake.random_int(min=1, max=100)),
            "reservation_date": kwargs.get(
                "reservation_date", fake.date_time().strftime("%Y-%m-%d %H:%M:%S")
            ),
            "direction": kwargs.get(
                "direction", fake.random_element(elements=("Туда", "Обратно"))
            ),
        }
        defaults.update(kwargs)
        return Reservation(**defaults)


class SimpleWaitingListRecordFactory:
    """Простая фабрика для создания тестовых записей листа ожидания"""

    @staticmethod
    def build(**kwargs):
        defaults = {
            "id": kwargs.get("id"),
            "passenger_id": kwargs.get(
                "passenger_id", fake.random_int(min=1, max=1000)
            ),
            "bus_id": kwargs.get("bus_id", fake.random_int(min=1, max=100)),
            "request_time": kwargs.get(
                "request_time", fake.date_time().strftime("%Y-%m-%d %H:%M:%S")
            ),
            "status": kwargs.get(
                "status",
                fake.random_element(elements=("Waiting", "Confirmed", "Cancelled")),
            ),
            "notification_sent": kwargs.get(
                "notification_sent", fake.random_element(elements=("Yes", "No"))
            ),
        }
        defaults.update(kwargs)
        return WaitingListRecord(**defaults)


class SimpleBusOwnerFactory:
    """Простая фабрика для создания тестовых владельцев автобусов"""

    @staticmethod
    def build(**kwargs):
        defaults = {
            "id": kwargs.get("id"),
            "bus_id": kwargs.get("bus_id", fake.random_int(min=1, max=100)),
            "chief_id": kwargs.get("chief_id", fake.random_int(min=1, max=1000)),
        }
        defaults.update(kwargs)
        return BusOwner(**defaults)
