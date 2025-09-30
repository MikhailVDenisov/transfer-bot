"""
Валидаторы для проверки данных
"""

from typing import Tuple


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
        return True, ""  # Телефон не обязателен

    phone = phone.strip()

    # Удаляем все символы кроме цифр и +
    clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")

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
        return True, ""  # Мобильные номера без кода страны

    if len(clean_phone) > 15:
        return False, "Номер телефона слишком длинный"

    return True, ""


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
