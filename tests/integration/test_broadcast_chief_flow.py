"""
Интеграционные тесты для рассылки шефа автобуса (broadcast_chief).

Прямые SQL-вставки идут через ``database.connection.db_connection`` (актуальная
подмена из conftest), а не ``from database.connection import db_connection`` на
уровне модуля — иначе после фикстуры остаётся старое подключение.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from telegram import CallbackQuery, Chat, Message, Update, User
from telegram.ext import ContextTypes

import database.connection
from services.broadcast_service import BroadcastService
from services.bus_service import BusService
from handlers.broadcast_chief_handler import BroadcastChiefHandler
from services.passenger_service import PassengerService
from utils.const import (
    BROADCAST_CHIEF_CANCEL,
    BROADCAST_CHIEF_SELECT_BUS,
    BROADCAST_CHIEF_SEND,
)



@pytest.mark.integration
class TestBroadcastChiefFlow:
    """Интеграционные тесты: шеф, назначенные автобусы и список пассажиров для рассылки"""

    def _insert_bus(self) -> int:
        from database.connection import db_connection

        db_connection.execute_query(
            "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "БУС-BC",
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "10:00",
                30,
                "Туда",
                True,
            ),
        )
        row = db_connection.execute_query(
            "SELECT ID FROM Buses WHERE Number = ?", ("БУС-BC",), fetch_one=True
        )
        return row[0]

    def test_chief_sees_assigned_buses_via_bus_owners(self, temp_db):
        """Автобусы шефа подтягиваются из BusOwners (как в реальном сценарии меню рассылки)"""
        passenger_service = PassengerService()
        bus_service = BusService()


        from database.connection import db_connection

        # 1. Создаем шефа1
        chief, _ = passenger_service.get_or_create_passenger("chief_bc", "900001")
        db_connection.execute_query(
            "UPDATE Passengers SET Role = ? WHERE ID = ?", ("chief", chief.id)
        )

        # 2. Создаем шефа2
        other_chief, _ = passenger_service.get_or_create_passenger("other_chief", "900002")
        db_connection.execute_query(
            "UPDATE Passengers SET Role = ? WHERE ID = ?", ("chief", other_chief.id)
        )

        # 3. Создаем автобус
        bus_id = self._insert_bus()

        # 3. Добавляем шефа1 на автобус
        db_connection.execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (bus_id, chief.id)
        )

        # 4. Проверяем наличие автобуса у шефа1
        buses = bus_service.get_buses_by_chief(chief.id)
        assert len(buses) == 1
        assert buses[0].id == bus_id
        assert buses[0].number == "БУС-BC"

        # 4. Проверяем наличие автобуса у шефа2
        assert bus_service.get_buses_by_chief(other_chief.id) == []

    def test_get_passengers_for_broadcast_excludes_chief(self, temp_db):
        """В рассылку не попадает сам шеф, даже если у него есть бронь на этом автобусе"""
        passenger_service = PassengerService()
        broadcast_service = BroadcastService()

        from database.connection import db_connection
        # 1. Создаем шефа
        chief, _ = passenger_service.get_or_create_passenger("chief_bc", "900010")
        db_connection.execute_query(
            "UPDATE Passengers SET Role = ? WHERE ID = ?", ("chief", chief.id)
        )

        # 2. Создаем пассажира
        p1, _ = passenger_service.get_or_create_passenger("pass1", "900011")

        # 3. Создаем автобус
        bus_id = self._insert_bus()
        db_connection.execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (bus_id, chief.id)
        )

        # 3. Бронируем автобус шефом и пассажиром
        for pid in (chief.id, p1.id):
            db_connection.execute_query(
                "INSERT INTO Reservations (PassengerID, BusID, ReservationDate, Direction) VALUES (?, ?, ?, ?)",
                (pid, bus_id, "2024-01-15 10:00:00", "Туда"),
            )

        # 4. Получаем пассажиров для рассылки
        passengers = broadcast_service.get_passengers_for_broadcast(bus_id, chief.id)

        assert passengers is not None
        assert len(passengers) == 1
        assert passengers[0].id == p1.id

    def test_get_passengers_for_broadcast_all_regular_passengers(self, temp_db):
        """Несколько пассажиров с бронью — все попадают в список (кроме шефа)"""
        passenger_service = PassengerService()
        broadcast_service = BroadcastService()

        from database.connection import db_connection

        # 1. Создаем шефа

        chief, _ = passenger_service.get_or_create_passenger("chief_bc", "900020")
        db_connection.execute_query(
            "UPDATE Passengers SET Role = ? WHERE ID = ?", ("chief", chief.id)
        )

        # 2. Создаем пассажиров
        p1, _ = passenger_service.get_or_create_passenger("pass_a", "900021")
        p2, _ = passenger_service.get_or_create_passenger("pass_b", "900022")

        # 3. Создаем автобус
        bus_id = self._insert_bus()
        db_connection.execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (bus_id, chief.id)
        )

        # 4. Бронируем автобус пассажирами
        for pid in (p1.id, p2.id):
            db_connection.execute_query(
                "INSERT INTO Reservations (PassengerID, BusID, ReservationDate, Direction) VALUES (?, ?, ?, ?)",
                (pid, bus_id, "2024-01-15 10:00:00", "Туда"),
            )

        # 5. Получаем пассажиров для рассылки
        passengers = broadcast_service.get_passengers_for_broadcast(bus_id, chief.id)

        assert passengers is not None
        ids = {p.id for p in passengers}
        assert ids == {p1.id, p2.id}

    def test_get_passengers_for_broadcast_empty_without_reservations(self, temp_db):
        """Без бронирований список пассажиров для рассылки пустой"""
        passenger_service = PassengerService()
        broadcast_service = BroadcastService()

        from database.connection import db_connection

        # 1. Создаем шефа
        chief, _ = passenger_service.get_or_create_passenger("chief_bc", "900030")
        db_connection.execute_query(
            "UPDATE Passengers SET Role = ? WHERE ID = ?", ("chief", chief.id)
        )

        # 2. Создаем автобус
        bus_id = self._insert_bus()
        db_connection.execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (bus_id, chief.id)
        )

        # 3. Получаем пассажиров для рассылки
        passengers = broadcast_service.get_passengers_for_broadcast(bus_id, chief.id)
        assert passengers == []

    @pytest.mark.asyncio
    async def test_send_broadcast_calls_copy_for_each_passenger(self, temp_db):
        """Рассылка вызывает copy_message по каждому пассажиру из списка (мок бота)"""
        passenger_service = PassengerService()
        broadcast_service = BroadcastService()

        from database.connection import db_connection

        # 1. Создаем шефа
        chief, _ = passenger_service.get_or_create_passenger("chief_bc", "900040")
        db_connection.execute_query(
            "UPDATE Passengers SET Role = ? WHERE ID = ?", ("chief", chief.id)
        )

        # 2. Создаем пассажиров
        p1, _ = passenger_service.get_or_create_passenger("pass_x", "900041")
        p2, _ = passenger_service.get_or_create_passenger("pass_y", "900042")

        # 3. Создаем автобус
        bus_id = self._insert_bus()
        db_connection.execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (bus_id, chief.id)
        )

        # 4. Бронируем автобус пассажирами
        for pid in (p1.id, p2.id):
            db_connection.execute_query(
                "INSERT INTO Reservations (PassengerID, BusID, ReservationDate, Direction) VALUES (?, ?, ?, ?)",
                (pid, bus_id, "2024-01-15 10:00:00", "Туда"),
            )

        # 5. Получаем пассажиров для рассылки
        targets = broadcast_service.get_passengers_for_broadcast(bus_id, chief.id)
        bot = Mock()
        bot.copy_message = AsyncMock()

        # 6. Отправляем рассылку
        stats = await broadcast_service.send_broadcast(
            bot, targets, source_chat_id=999, source_message_id=100
        )

        assert stats.sent == 2
        assert stats.failed == 0
        assert stats.forbidden == 0
        assert bot.copy_message.await_count == 2
        chat_ids = {c.kwargs["chat_id"] for c in bot.copy_message.await_args_list}
        assert chat_ids == {p1.chat_id, p2.chat_id}

@pytest.mark.integration
class TestBroadcastChiefHandlerIntegration:
    """Интеграция обработчика рассылки шефа с БД и BusService / BroadcastService."""

    @staticmethod
    def _db():
        """Текущее подключение к тестовой БД (подменено фикстурой conftest)."""
        return database.connection.db_connection

    def _insert_bus(self, number: str = "БУС-H") -> int:
        """Добавляем автобус и возвращаем его ID."""
        db = self._db()
        db.execute_query(
            "INSERT INTO Buses (Number, Departure_Place, Destination, DepartureDate, DepartureTime, Capacity, Direction, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                number,
                "Москва",
                "Переславль-Залесский",
                "2024-01-15",
                "10:00",
                30,
                "Туда",
                True,
            ),
        )
        row = db.execute_query(
            "SELECT ID FROM Buses WHERE Number = ?", (number,), fetch_one=True
        )
        return row[0]

    def _callback_update(self, username: str, chat_id: int, callback_data: str):
        """Собираем Update с callback_query как в Telegram (меню / inline-кнопки)."""
        user = Mock(spec=User)
        user.username = username

        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.edit_message_reply_markup = AsyncMock()
        query.from_user = user
        query.data = callback_data

        msg = Mock(spec=Message)
        msg.chat_id = chat_id
        msg.reply_text = AsyncMock()
        query.message = msg

        update = Mock(spec=Update)
        update.callback_query = query
        update.message = None
        update.effective_user = user
        update.effective_chat = Mock(spec=Chat)
        update.effective_chat.id = chat_id
        return update, query

    def _message_update(self, username: str, chat_id: int, message_id: int = 501):
        """Update с обычным сообщением (шаг «отправь текст рассылки»)."""
        user = Mock(spec=User)
        user.username = username

        message = Mock(spec=Message)
        message.message_id = message_id
        message.from_user = user
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.callback_query = None
        update.message = message
        update.effective_user = user
        update.effective_chat = Mock(spec=Chat)
        update.effective_chat.id = chat_id
        return update

    def _context(self):
        """Контекст PTB: user_data и бот с асинхронными методами."""
        ctx = Mock(spec=ContextTypes.DEFAULT_TYPE)
        ctx.user_data = {}
        ctx.bot = Mock()
        ctx.bot.copy_message = AsyncMock()
        return ctx

    def _make_chief_in_db(self, username: str, chat_id: str) -> int:
        """Создаём пассажира и назначаем роль chief (как в админке)."""
        ps = PassengerService()
        chief, _ = ps.get_or_create_passenger(username, chat_id)
        # Повышаем права до шефа в БД (роль по умолчанию — user)
        self._db().execute_query(
            "UPDATE Passengers SET Role = ? WHERE ID = ?", ("chief", chief.id)
        )
        return chief.id

    @pytest.mark.asyncio
    async def test_broadcast_command_denied_for_regular_user(self, temp_db):
        """Обычный пользователь в БД не может открыть рассылку шефа."""
        # Регистрируем пользователя с ролью user (значение по умолчанию в таблице)
        PassengerService().get_or_create_passenger("plain_user", "920001")

        handler = BroadcastChiefHandler()
        update, query = self._callback_update("plain_user", 920001, "any")
        ctx = self._context()

        # Обработчик сам подтянет пассажира из БД по username из callback
        await handler.broadcast_command(update, ctx)

        # Ошибка уходит в то же сообщение меню (inline), callback не подтверждаем
        query.edit_message_text.assert_awaited_once()
        err_text = query.edit_message_text.await_args.args[0]
        assert "Доступ запрещен" in err_text
        query.answer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_broadcast_command_denied_without_telegram_username(self, temp_db):
        """Нет username в Telegram — пассажир не создаётся, доступ к рассылке закрыт."""
        handler = BroadcastChiefHandler()
        update, query = self._callback_update("ignored", 920002, "cmd")
        # Имитируем аккаунт без @username (from_user.username is None)
        update.callback_query.from_user.username = None
        update.effective_user.username = None
        ctx = self._context()

        await handler.broadcast_command(update, ctx)

        # Сначала базовый обработчик сообщит про username, затем ветка «не шеф»
        assert query.edit_message_text.await_count == 2
        texts = [c.args[0] for c in query.edit_message_text.await_args_list]
        assert any("Username не найден" in t for t in texts)
        assert any("Доступ запрещен" in t for t in texts)

    @pytest.mark.asyncio
    async def test_broadcast_command_chief_without_assigned_buses(self, temp_db):
        """Шеф без записей в BusOwners получает понятную ошибку."""
        # Шеф в Passengers есть, но ни одной строки в BusOwners — меню пустое
        self._make_chief_in_db("lonely_chief", "920010")
        handler = BroadcastChiefHandler()
        update, query = self._callback_update("lonely_chief", 920010, "start")
        ctx = self._context()

        await handler.broadcast_command(update, ctx)

        # Сначала отвечаем на callback (убираем «часики»), затем показываем причину отказа
        query.answer.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()
        assert "не назначено ни одного автобуса" in query.edit_message_text.await_args.args[0]

    @pytest.mark.asyncio
    async def test_broadcast_command_chief_sees_bus_keyboard(self, temp_db):
        """Шеф с назначенным автобусом видит клавиатуру выбора автобуса."""
        chief_id = self._make_chief_in_db("chief_menu", "920020")
        bus_id = self._insert_bus("БУС-MENU")
        # Связь шеф ↔ автобус (то, что отдаёт BusRepository.get_by_chief)
        self._db().execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (bus_id, chief_id)
        )

        handler = BroadcastChiefHandler()
        update, query = self._callback_update("chief_menu", 920020, "cmd")
        ctx = self._context()

        await handler.broadcast_command(update, ctx)

        query.answer.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()
        call = query.edit_message_text.await_args
        # edit_message_text(text, reply_markup=...) — текст может быть позиционным аргументом
        title = call.args[0] if call.args else call.kwargs.get("text")
        assert title == "Выберите автобус:"
        assert call.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_prepare_broadcast_invalid_callback_suffix(self, temp_db):
        """Некорректный callback (пустой суффикс после префикса) — ошибка до answer()."""
        # Достаточно роли chief; разбор callback падает раньше запроса автобусов из БД
        self._make_chief_in_db("chief_bad_cb", "920030")

        handler = BroadcastChiefHandler()
        # Ровно префикс без ID автобуса — парсер вернёт None
        update, query = self._callback_update(
            "chief_bad_cb", 920030, BROADCAST_CHIEF_SELECT_BUS
        )
        ctx = self._context()

        await handler.prepare_broadcast(update, ctx)

        query.answer.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()
        assert "Некорректный выбор автобуса" in query.edit_message_text.await_args.args[0]

    @pytest.mark.asyncio
    async def test_prepare_broadcast_bus_id_zero_rejected(self, temp_db):
        """ID автобуса 0 из callback отклоняется парсером (недопустимый id)."""
        self._make_chief_in_db("chief_zero", "920031")
        handler = BroadcastChiefHandler()
        update, query = self._callback_update(
            "chief_zero", 920031, f"{BROADCAST_CHIEF_SELECT_BUS}0"
        )
        ctx = self._context()

        await handler.prepare_broadcast(update, ctx)

        query.answer.assert_awaited_once()
        assert "Некорректный выбор автобуса" in query.edit_message_text.await_args.args[0]

    @pytest.mark.asyncio
    async def test_prepare_broadcast_bus_not_owned_by_chief(self, temp_db):
        """Автобус есть в БД, но не назначен этому шефу — отказ."""
        chief_id = self._make_chief_in_db("chief_own", "920040")
        mine = self._insert_bus("БУС-MINE")
        other = self._insert_bus("БУС-OTHER")
        # Шеф закреплён только за «mine», запросим «other»
        self._db().execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (mine, chief_id)
        )

        handler = BroadcastChiefHandler()
        update, query = self._callback_update(
            "chief_own", 920040, f"{BROADCAST_CHIEF_SELECT_BUS}{other}"
        )
        ctx = self._context()

        await handler.prepare_broadcast(update, ctx)

        query.answer.assert_awaited_once()
        assert "не назначен" in query.edit_message_text.await_args.args[0]

    @pytest.mark.asyncio
    async def test_prepare_broadcast_success_writes_user_data(self, temp_db):
        """Успешный выбор автобуса — bus_id, режим рассылки и сброс черновика."""
        chief_id = self._make_chief_in_db("chief_ok", "920050")
        bus_id = self._insert_bus("БУС-OK")
        self._db().execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (bus_id, chief_id)
        )

        handler = BroadcastChiefHandler()
        update, query = self._callback_update(
            "chief_ok", 920050, f"{BROADCAST_CHIEF_SELECT_BUS}{bus_id}"
        )
        ctx = self._context()

        await handler.prepare_broadcast(update, ctx)

        query.answer.assert_awaited_once()
        # Дальше пользователь шлёт контент — ждём handle_chief_message
        assert ctx.user_data["bus_id"] == bus_id
        assert ctx.user_data["broadcast_mode"] is True
        assert ctx.user_data["broadcast_message"] is None


    @pytest.mark.asyncio
    async def test_handle_chief_message_denied_for_non_chief_in_mode(self, temp_db):
        """Режим рассылки True, но пользователь в БД не шеф — ошибка в обычное сообщение."""
        PassengerService().get_or_create_passenger("not_chief", "920070")
        handler = BroadcastChiefHandler()
        update = self._message_update("not_chief", 920070)
        ctx = self._context()
        ctx.user_data["broadcast_mode"] = True

        await handler.handle_chief_message(update, ctx)

        # Для message-update ошибка идёт через reply_text (не edit)
        update.message.reply_text.assert_awaited_once()
        assert "Доступ запрещен" in update.message.reply_text.await_args.args[0]
        # _broadcast_error очищает состояние сценария
        assert "broadcast_mode" not in ctx.user_data

    @pytest.mark.asyncio
    async def test_handle_chief_message_success_stores_payload(self, temp_db):
        """Шеф в режиме рассылки: сохраняем ссылку на сообщение и показываем предпросмотр."""
        self._make_chief_in_db("chief_msg", "920080")
        handler = BroadcastChiefHandler()
        update = self._message_update("chief_msg", 920080, message_id=777)
        ctx = self._context()
        ctx.user_data["broadcast_mode"] = True

        await handler.handle_chief_message(update, ctx)

        # Эти поля потом читает broadcast_send + copy_message у пассажиров
        assert ctx.user_data["broadcast_message"] == {
            "chat_id": 920080,
            "message_id": 777,
        }
        update.message.reply_text.assert_awaited_once_with("Предпросмотр сообщения:")
        ctx.bot.copy_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_broadcast_send_denied_without_broadcast_mode(self, temp_db):
        """Отправка по кнопке без активного режима — ошибка и сброс user_data через _broadcast_error."""
        self._make_chief_in_db("chief_send1", "920090")
        handler = BroadcastChiefHandler()
        update, query = self._callback_update("chief_send1", 920090, BROADCAST_CHIEF_SEND)
        ctx = self._context()
        ctx.user_data["broadcast_message"] = {"chat_id": 1, "message_id": 2}

        await handler.broadcast_send(update, ctx)

        query.answer.assert_awaited_once()
        assert "Ошибка рассылки" in query.edit_message_text.await_args.args[0]

    @pytest.mark.asyncio
    async def test_broadcast_send_missing_stored_message(self, temp_db):
        """Режим есть, payload сообщения не сохранён — просим подготовить сообщение заново."""
        self._make_chief_in_db("chief_send2", "920091")
        handler = BroadcastChiefHandler()
        update, query = self._callback_update("chief_send2", 920091, BROADCAST_CHIEF_SEND)
        ctx = self._context()
        ctx.user_data["broadcast_mode"] = True
        ctx.user_data["bus_id"] = 1

        await handler.broadcast_send(update, ctx)

        query.answer.assert_awaited_once()
        assert "Не найдено сообщение для рассылки" in query.edit_message_text.await_args.args[0]

    @pytest.mark.asyncio
    async def test_broadcast_send_no_passengers_on_bus_integration(self, temp_db):
        """Реальный автобус шефа без пассажиров с бронью — нечего рассылать."""
        chief_id = self._make_chief_in_db("chief_empty", "920092")
        bus_id = self._insert_bus("БУС-EMPTY")
        self._db().execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (bus_id, chief_id)
        )

        handler = BroadcastChiefHandler()
        update, query = self._callback_update(
            "chief_empty", 920092, f"{BROADCAST_CHIEF_SEND}_1"
        )
        ctx = self._context()
        ctx.user_data["broadcast_mode"] = True
        ctx.user_data["bus_id"] = bus_id
        ctx.user_data["broadcast_message"] = {"chat_id": 920092, "message_id": 1}

        await handler.broadcast_send(update, ctx)

        # Реальный get_passengers_for_broadcast вернёт [] без Reservations
        assert "Не найдено пассажиров для рассылки" in query.edit_message_text.await_args.args[0]

    @pytest.mark.asyncio
    async def test_broadcast_send_success_calls_real_broadcast_service(self, temp_db):
        """Полный путь: реальные пассажиры из БД, рассылка через BroadcastService, бот замокан."""
        chief_id = self._make_chief_in_db("chief_full", "920100")
        ps = PassengerService()
        p1, _ = ps.get_or_create_passenger("pax_one", "920101")
        bus_id = self._insert_bus("БУС-FULL")
        self._db().execute_query(
            "INSERT INTO BusOwners (BusID, ChiefID) VALUES (?, ?)", (bus_id, chief_id)
        )
        # Один пассажир с бронью — он попадёт в выборку BroadcastService
        self._db().execute_query(
            "INSERT INTO Reservations (PassengerID, BusID, ReservationDate, Direction) VALUES (?, ?, ?, ?)",
            (p1.id, bus_id, "2024-01-15 10:00:00", "Туда"),
        )

        handler = BroadcastChiefHandler()
        update, query = self._callback_update(
            "chief_full", 920100, f"{BROADCAST_CHIEF_SEND}_55"
        )
        ctx = self._context()
        ctx.user_data["broadcast_mode"] = True
        ctx.user_data["bus_id"] = bus_id
        ctx.user_data["broadcast_message"] = {"chat_id": 920100, "message_id": 55}

        # Убираем реальные паузы rate-limit в тесте
        with patch("services.broadcast_service.asyncio.sleep", new_callable=AsyncMock):
            await handler.broadcast_send(update, ctx)

        query.answer.assert_awaited_once()
        query.edit_message_reply_markup.assert_awaited_once()
        # Сначала «Начинаю…», в конце — сводка по статистике
        final = query.message.reply_text.await_args_list[-1].args[0]
        assert "Рассылка завершена" in final
        assert "Успешно: 1" in final
        assert ctx.user_data.get("broadcast_mode") is False
        assert "broadcast_message" not in ctx.user_data
        assert "bus_id" not in ctx.user_data

    @pytest.mark.asyncio
    async def test_broadcast_cancel_clears_user_data_for_chief(self, temp_db):
        """Отмена сбрасывает режим и поля, убирает клавиатуру с предпросмотра."""
        self._make_chief_in_db("chief_cancel", "920110")
        handler = BroadcastChiefHandler()
        update, query = self._callback_update(
            "chief_cancel", 920110, BROADCAST_CHIEF_CANCEL
        )
        ctx = self._context()
        ctx.user_data["broadcast_mode"] = True
        ctx.user_data["bus_id"] = 99
        ctx.user_data["broadcast_message"] = {"chat_id": 1, "message_id": 2}

        await handler.broadcast_cancel(update, ctx)

        query.edit_message_reply_markup.assert_awaited_once()
        query.message.reply_text.assert_awaited_once_with("Рассылка отменена.")
        assert "broadcast_mode" not in ctx.user_data

    @pytest.mark.asyncio
    async def test_broadcast_cancel_denied_for_regular_user(self, temp_db):
        """Не-шеф не может отменить сценарий — показываем отказ."""
        PassengerService().get_or_create_passenger("user_cancel", "920120")
        handler = BroadcastChiefHandler()
        update, query = self._callback_update(
            "user_cancel", 920120, BROADCAST_CHIEF_CANCEL
        )
        ctx = self._context()

        await handler.broadcast_cancel(update, ctx)

        assert "Доступ запрещен" in query.edit_message_text.await_args.args[0]

    @pytest.mark.asyncio
    async def test_prepare_broadcast_non_digit_suffix(self, temp_db):
        """Суффикс с буквами после префикса — парсер отклоняет (не целое id)."""
        self._make_chief_in_db("chief_nan", "920130")
        handler = BroadcastChiefHandler()
        update, query = self._callback_update(
            "chief_nan", 920130, f"{BROADCAST_CHIEF_SELECT_BUS}12abc"
        )
        ctx = self._context()

        await handler.prepare_broadcast(update, ctx)

        query.answer.assert_awaited_once()
        assert "Некорректный выбор автобуса" in query.edit_message_text.await_args.args[0]
