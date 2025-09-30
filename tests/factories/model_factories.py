"""
Фабрики для создания тестовых моделей данных
"""

from faker import Faker
from polyfactory import BaseFactory

from models.entities import Bus, BusOwner, Passenger, Reservation, WaitingListRecord

fake = Faker("ru_RU")


class PassengerFactory(BaseFactory):
    """Фабрика для создания тестовых пассажиров"""

    __model__ = Passenger

    @classmethod
    def telegram_username(cls) -> str:
        return fake.user_name()

    @classmethod
    def chat_id(cls) -> str:
        return str(fake.random_int(min=100000000, max=999999999))

    @classmethod
    def fio(cls) -> str:
        return f"{fake.last_name()} {fake.first_name()} {fake.middle_name()}"

    @classmethod
    def phone(cls) -> str:
        return fake.phone_number()

    @classmethod
    def comment(cls) -> str:
        return fake.text(max_nb_chars=100)

    @classmethod
    def role(cls) -> str:
        return fake.random_element(elements=("user", "admin"))


class BusFactory(BaseFactory):
    """Фабрика для создания тестовых автобусов"""

    __model__ = Bus

    @classmethod
    def number(cls) -> str:
        return f"БУС-{fake.random_int(min=1, max=999)}"

    @classmethod
    def departure_place(cls) -> str:
        return fake.random_element(elements=("Москва", "Санкт-Петербург", "Казань"))

    @classmethod
    def destination(cls) -> str:
        return fake.random_element(
            elements=("Переславль-Залесский", "Ярославль", "Кострома")
        )

    @classmethod
    def departure_date(cls) -> str:
        return fake.date(pattern="%Y-%m-%d")

    @classmethod
    def departure_time(cls) -> str:
        return fake.time(pattern="%H:%M")

    @classmethod
    def capacity(cls) -> int:
        return fake.random_int(min=20, max=50)

    @classmethod
    def direction(cls) -> str:
        return fake.random_element(elements=("Туда", "Обратно"))

    @classmethod
    def is_active(cls) -> bool:
        return fake.boolean(chance_of_getting_true=80)


class ReservationFactory(BaseFactory):
    """Фабрика для создания тестовых бронирований"""

    __model__ = Reservation

    @classmethod
    def passenger_id(cls) -> int:
        return fake.random_int(min=1, max=1000)

    @classmethod
    def bus_id(cls) -> int:
        return fake.random_int(min=1, max=100)

    @classmethod
    def reservation_date(cls) -> str:
        return fake.date_time().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def direction(cls) -> str:
        return fake.random_element(elements=("Туда", "Обратно"))


class WaitingListRecordFactory(BaseFactory):
    """Фабрика для создания тестовых записей листа ожидания"""

    __model__ = WaitingListRecord

    @classmethod
    def passenger_id(cls) -> int:
        return fake.random_int(min=1, max=1000)

    @classmethod
    def bus_id(cls) -> int:
        return fake.random_int(min=1, max=100)

    @classmethod
    def request_time(cls) -> str:
        return fake.date_time().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def status(cls) -> str:
        return fake.random_element(elements=("Waiting", "Confirmed", "Cancelled"))

    @classmethod
    def notification_sent(cls) -> str:
        return fake.random_element(elements=("Yes", "No"))


class BusOwnerFactory(BaseFactory):
    """Фабрика для создания тестовых владельцев автобусов"""

    __model__ = BusOwner

    @classmethod
    def bus_id(cls) -> int:
        return fake.random_int(min=1, max=100)

    @classmethod
    def chief_id(cls) -> int:
        return fake.random_int(min=1, max=1000)
