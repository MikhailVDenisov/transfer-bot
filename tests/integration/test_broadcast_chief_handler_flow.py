"""
Интеграционные тесты BroadcastChiefHandler: реальная БД и сервисы, моки Telegram.

Подключение к БД теста — только ``database.connection.db_connection`` во время
вызова (см. conftest), не ``from database.connection import db_connection`` на
уровне модуля.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User
from telegram.ext import ContextTypes

import database.connection
from handlers.broadcast_chief_handler import BroadcastChiefHandler
from services.passenger_service import PassengerService
from utils.const import (
    BROADCAST_CHIEF_CANCEL,
    BROADCAST_CHIEF_SELECT_BUS,
    BROADCAST_CHIEF_SEND,
)


