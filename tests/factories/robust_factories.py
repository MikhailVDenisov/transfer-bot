"""
Надежные фабрики для создания тестовых моделей данных
Не зависят от внешних библиотек, кроме faker
"""

import random
from datetime import datetime, timedelta

from models.entities import Bus, BusOwner, Passenger, Reservation, WaitingListRecord

# Простые функции для генерации данных без faker
# Глобальные счетчики для уникальных значений
_username_counter = 0
_chat_id_counter = 100000000


def random_username():
    """Генерирует уникальное имя пользователя"""
    global _username_counter
    _username_counter += 1
    names = ["user", "test", "demo", "admin", "guest", "visitor"]
    return f"{random.choice(names)}{_username_counter}"


def random_chat_id():
    """Генерирует уникальный chat_id"""
    global _chat_id_counter
    _chat_id_counter += 1
    return str(_chat_id_counter)


def random_fio():
    """Генерирует случайное ФИО"""
    last_names = ["Иванов", "Петров", "Сидоров", "Козлов", "Морозов"]
    first_names = ["Иван", "Петр", "Сидор", "Алексей", "Дмитрий"]
    middle_names = ["Иванович", "Петрович", "Сидорович", "Алексеевич", "Дмитриевич"]
    return f"{random.choice(last_names)} {random.choice(first_names)} {random.choice(middle_names)}"


def random_phone():
    """Генерирует случайный телефон"""
    return f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}"


def random_comment():
    """Генерирует случайный комментарий"""
    comments = [
        "Обычный пассажир",
        "VIP клиент",
        "Частый пользователь",
        "Новый клиент",
        "Корпоративный клиент",
    ]
    return random.choice(comments)


def random_role():
    """Генерирует случайную роль"""
    return "user"  # По умолчанию user для тестов


def random_bus_number():
    """Генерирует случайный номер автобуса"""
    return f"БУС-{random.randint(1, 999):03d}"


def random_place():
    """Генерирует случайное место"""
    places = ["Москва", "Санкт-Петербург", "Казань", "Екатеринбург", "Новосибирск"]
    return random.choice(places)


def random_destination():
    """Генерирует случайное место назначения"""
    destinations = ["Переславль-Залесский", "Ярославль", "Кострома", "Ростов", "Углич"]
    return random.choice(destinations)


def random_date():
    """Генерирует случайную дату"""
    start_date = datetime.now()
    random_days = random.randint(1, 365)
    return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")


def random_time():
    """Генерирует случайное время"""
    hour = random.randint(6, 22)
    minute = random.choice([0, 15, 30, 45])
    return f"{hour:02d}:{minute:02d}"


def random_capacity():
    """Генерирует случайную вместимость"""
    return random.randint(20, 50)


def random_direction():
    """Генерирует случайное направление"""
    return random.choice(["Туда", "Обратно"])


def random_status():
    """Генерирует случайный статус"""
    return "Waiting"  # По умолчанию Waiting для тестов


def random_notification():
    """Генерирует случайное уведомление"""
    return "No"  # По умолчанию No для тестов


class RobustPassengerFactory:
    """Надежная фабрика для создания тестовых пассажиров"""

    @staticmethod
    def build(**kwargs):
        defaults = {
            "id": kwargs.get("id"),
            "telegram_username": kwargs.get("telegram_username", random_username()),
            "chat_id": kwargs.get("chat_id", random_chat_id()),
            "last_name": kwargs.get("last_name", "Иванов"),
            "first_name": kwargs.get("first_name", "Иван"),
            "patronymic": kwargs.get("patronymic", "Иванович"),
            "fio": kwargs.get("fio", random_fio()),
            "phone": kwargs.get("phone", random_phone()),
            "birth_date": kwargs.get("birth_date", "01.01.1990"),
            "passport_number": kwargs.get("passport_number", "1234 567890"),
            "citizenship": kwargs.get("citizenship", "РФ"),
            "personal_data_confirmed": kwargs.get("personal_data_confirmed", True),
            "comment": kwargs.get("comment", random_comment()),
            "role": kwargs.get("role", random_role()),
        }
        defaults.update(kwargs)
        return Passenger(**defaults)


class RobustBusFactory:
    """Надежная фабрика для создания тестовых автобусов"""

    @staticmethod
    def build(**kwargs):
        defaults = {
            "id": kwargs.get("id"),
            "number": kwargs.get("number", random_bus_number()),
            "departure_place": kwargs.get("departure_place", random_place()),
            "destination": kwargs.get("destination", random_destination()),
            "departure_date": kwargs.get("departure_date", random_date()),
            "departure_time": kwargs.get("departure_time", random_time()),
            "capacity": kwargs.get("capacity", random_capacity()),
            "direction": kwargs.get("direction", random_direction()),
            "is_active": kwargs.get("is_active", True),
        }
        defaults.update(kwargs)
        return Bus(**defaults)


class RobustReservationFactory:
    """Надежная фабрика для создания тестовых бронирований"""

    @staticmethod
    def build(**kwargs):
        defaults = {
            "id": kwargs.get("id"),
            "passenger_id": kwargs.get("passenger_id", random.randint(1, 1000)),
            "bus_id": kwargs.get("bus_id", random.randint(1, 100)),
            "reservation_date": kwargs.get(
                "reservation_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
            "direction": kwargs.get("direction", random_direction()),
        }
        defaults.update(kwargs)
        return Reservation(**defaults)


class RobustWaitingListRecordFactory:
    """Надежная фабрика для создания тестовых записей листа ожидания"""

    @staticmethod
    def build(**kwargs):
        defaults = {
            "id": kwargs.get("id"),
            "passenger_id": kwargs.get("passenger_id", random.randint(1, 1000)),
            "bus_id": kwargs.get("bus_id", random.randint(1, 100)),
            "request_time": kwargs.get(
                "request_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
            "status": kwargs.get("status", random_status()),
            "notification_sent": kwargs.get("notification_sent", random_notification()),
        }
        defaults.update(kwargs)
        return WaitingListRecord(**defaults)


class RobustBusOwnerFactory:
    """Надежная фабрика для создания тестовых владельцев автобусов"""

    @staticmethod
    def build(**kwargs):
        defaults = {
            "id": kwargs.get("id"),
            "bus_id": kwargs.get("bus_id", random.randint(1, 100)),
            "chief_id": kwargs.get("chief_id", random.randint(1, 1000)),
        }
        defaults.update(kwargs)
        return BusOwner(**defaults)
