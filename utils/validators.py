"""
Валидаторы для проверки данных
"""

import re
from datetime import datetime
from typing import Tuple


def validate_name_part(
    value: str, field_name: str, optional: bool = False
) -> Tuple[bool, str]:
    """Валидирует часть ФИО"""
    if not value:
        return (True, "") if optional else (False, f"{field_name} не может быть пустым")

    value = value.strip()
    if not value:
        return (True, "") if optional else (False, f"{field_name} не может быть пустым")

    if len(value) < 2:
        return False, f"{field_name} должно содержать не менее 2 символов"

    if len(value) > 50:
        return False, f"{field_name} не может содержать более 50 символов"

    if not all(c.isalpha() or c in " -" for c in value):
        return False, f"{field_name} может содержать только буквы, пробелы и дефисы"

    return True, ""


def validate_fio(fio: str) -> Tuple[bool, str]:
    """
    Валидирует ФИО

    Args:
        fio: ФИО для проверки

    Returns:
        Tuple[bool, str]: (валидно_ли, сообщение_об_ошибке)
    """
    if not fio:
        return False, "ФИО не может быть пустым"

    fio = fio.strip()

    if len(fio) < 5:
        return False, "ФИО должно содержать не менее 5 символов"

    if len(fio) > 50:
        return False, "ФИО не может содержать более 50 символов"

    # Проверяем, что ФИО содержит только буквы, пробелы и дефисы
    if not all(c.isalpha() or c.isspace() or c == "-" for c in fio):
        return False, "ФИО может содержать только буквы, пробелы и дефисы"

    # Проверяем, что есть хотя бы два слова (имя и фамилия)
    words = fio.split()
    if len(words) < 2:
        return False, "ФИО должно содержать минимум имя и фамилию"

    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """
    Валидирует номер телефона

    Args:
        phone: Номер телефона для проверки

    Returns:
        Tuple[bool, str]: (валидно_ли, сообщение_об_ошибке)
    """
    if not phone:
        return False, "Номер телефона не может быть пустым"

    phone = phone.strip()
    if not all(c.isdigit() or c == "+" for c in phone):
        return False, "Номер телефона может содержать только цифры и символ +"

    if phone.count("+") > 1 or ("+" in phone and not phone.startswith("+")):
        return False, "Номер телефона может содержать только цифры и символ +"

    clean_phone = phone

    if len(clean_phone) < 10:
        return False, "Номер телефона слишком короткий"

    # Проверяем российские номера (начинающиеся с +7 или 8)
    if clean_phone.startswith("+7") and len(clean_phone) == 12:
        return True, ""
    elif clean_phone.startswith("8") and len(clean_phone) == 11:
        return True, ""
    elif clean_phone.startswith("7") and len(clean_phone) == 11:
        return True, ""
    elif clean_phone.startswith("9") and len(clean_phone) == 10:
        return True, ""

    if len(clean_phone) > 12:
        return False, "Номер телефона слишком длинный"

    return True, ""


def validate_birth_date(birth_date: str) -> Tuple[bool, str]:
    """Валидирует дату рождения в формате дд.мм.гггг"""
    if not birth_date:
        return False, "Дата рождения не может быть пустой"

    try:
        parsed_date = datetime.strptime(birth_date.strip(), "%d.%m.%Y")
    except ValueError:
        return False, "Дата рождения должна быть в формате дд.мм.гггг"

    if parsed_date.date() >= datetime.now().date():
        return False, "Дата рождения должна быть раньше текущей даты"

    return True, ""


def validate_passport_number(passport_number: str) -> Tuple[bool, str]:
    """Валидирует серию и номер паспорта"""
    if not passport_number:
        return False, "Серия и номер паспорта не могут быть пустыми"

    return True, ""


def validate_citizenship(citizenship: str) -> Tuple[bool, str]:
    """Валидирует гражданство как текстовое поле"""
    normalized_value = normalize_citizenship(citizenship)

    if normalized_value == "РФ":
        return True, ""

    if not normalized_value.strip():
        return False, "Гражданство не может быть пустым"

    if len(normalized_value) < 2:
        return False, "Гражданство должно содержать не менее 2 символов"

    if len(normalized_value) > 50:
        return False, "Гражданство не может содержать более 50 символов"

    if not all(c.isalpha() or c in " -" for c in normalized_value):
        return (
            False,
            "Гражданство должно быть текстом и может содержать только буквы, пробелы и дефисы",
        )

    return True, ""


def normalize_citizenship(citizenship: str) -> str:
    """Приводит гражданство к сохраняемому виду"""
    if not citizenship:
        return "РФ"

    normalized_value = citizenship.strip()
    if normalized_value in {"рф", "РФ", "россия", "Россия"}:
        return "РФ"

    return normalized_value


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Валидирует username

    Args:
        username: Username для проверки

    Returns:
        Tuple[bool, str]: (валидно_ли, сообщение_об_ошибке)
    """
    if not username:
        return False, "Username не может быть пустым"

    username = username.strip()

    if len(username) < 3:
        return False, "Username должен содержать не менее 3 символов"

    if len(username) > 32:
        return False, "Username не может содержать более 32 символов"

    # Проверяем, что username содержит только буквы, цифры и подчеркивания
    if not username.replace("_", "").isalnum():
        return False, "Username может содержать только буквы, цифры и подчеркивания"

    return True, ""
