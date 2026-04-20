"""
Тесты для обработчиков
"""

from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User
from telegram.ext import ContextTypes

from handlers.booking_handler import BookingHandler
from handlers.broadcast_chief_handler import BroadcastChiefHandler
from handlers.callback_handler import CallbackHandler
from handlers.export_handler import ExportHandler
from handlers.info_handler import InfoHandler
from handlers.start_handler import StartHandler
from handlers.view_booking_handler import ViewBookingHandler
from handlers.waiting_list_handler import WaitingListHandler
from models.entities import Bus, Passenger, Reservation
from services.broadcast_service import BroadcastStats
from tests.factories import BusFactory, PassengerFactory, ReservationFactory
from utils.const import BROADCAST_CHIEF_SELECT_BUS, BROADCAST_CHIEF_SEND


class TestStartHandler:
    """Тесты для StartHandler"""

    @pytest.fixture
    def mock_update(self):
        """Создает мок Update"""
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.chat_id = 123456789
        update.message.from_user = Mock(spec=User)
        update.message.from_user.username = "test_user"
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Создает мок Context"""
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @pytest.fixture
    def handler(self):
        """Создает экземпляр StartHandler"""
        return StartHandler()

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, mock_update, mock_context):
        """Тест успешной обработки команды /start"""
        mock_passenger = PassengerFactory.build(role="user")

        with patch.object(
            handler, "get_or_create_passenger", return_value=mock_passenger
        ) as mock_get_passenger:
            await handler.handle(mock_update, mock_context)

            mock_get_passenger.assert_called_once_with(mock_update)
            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_admin_user(self, handler, mock_update, mock_context):
        """Тест обработки команды /start для администратора"""
        mock_passenger = PassengerFactory.build(role="admin")

        with patch.object(
            handler, "get_or_create_passenger", return_value=mock_passenger
        ):
            await handler.handle(mock_update, mock_context)

            # Проверяем, что сообщение было отправлено
            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_no_passenger(self, handler, mock_update, mock_context):
        """Тест обработки команды /start без пассажира"""
        with patch.object(handler, "get_or_create_passenger", return_value=None):
            await handler.handle(mock_update, mock_context)

            # Сообщение не должно быть отправлено
            mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_exception(self, handler, mock_update, mock_context):
        """Тест обработки исключения в handle"""
        with patch.object(
            handler, "get_or_create_passenger", side_effect=Exception("Test error")
        ):
            await handler.handle(mock_update, mock_context)

            # Должно быть отправлено сообщение об ошибке
            mock_update.message.reply_text.assert_called_once()


class TestBookingHandler:
    """Тесты для BookingHandler"""

    @pytest.fixture
    def mock_callback_query(self):
        """Создает мок CallbackQuery"""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.from_user = Mock(spec=User)
        query.from_user.username = "test_user"
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Создает мок Update с CallbackQuery"""
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        return update

    @pytest.fixture
    def handler(self):
        """Создает экземпляр BookingHandler"""
        return BookingHandler()

    @pytest.mark.asyncio
    async def test_show_directions_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест успешного показа направлений"""
        mock_passenger = PassengerFactory.build()
        mock_directions = ["Туда", "Обратно"]

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.bus_service,
                "get_available_directions",
                return_value=mock_directions,
            ),
        ):
            await handler.show_directions(mock_update_with_callback, mock_context)

            mock_update_with_callback.callback_query.answer.assert_called_once()
            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_directions_no_directions(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест показа направлений когда их нет"""
        mock_passenger = PassengerFactory.build()

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.bus_service, "get_available_directions", return_value=[]
            ),
        ):
            await handler.show_directions(mock_update_with_callback, mock_context)

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_buses_for_direction_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест успешного показа автобусов для направления"""
        mock_passenger = PassengerFactory.build()
        mock_buses = [BusFactory.build()]
        mock_reservations = []

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.bus_service, "get_buses_for_direction", return_value=mock_buses
            ),
            patch.object(handler.booking_service, "get_user_bookings", return_value=[]),
            patch("database.repositories.ReservationRepository") as mock_repo,
        ):

            mock_repo.return_value.get_all.return_value = mock_reservations

            await handler.show_buses_for_direction(
                mock_update_with_callback, mock_context, "Туда"
            )

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_directions_requires_personal_data(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест запрета бронирования без персональных данных"""
        mock_passenger = PassengerFactory.build(passport_number="")

        with patch.object(
            handler, "get_or_create_passenger", return_value=mock_passenger
        ):
            await handler.show_directions(mock_update_with_callback, mock_context)

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_booking_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест успешного подтверждения бронирования"""
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build()

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler.bus_service, "get_bus_by_id", return_value=mock_bus),
            patch.object(
                handler.booking_service, "can_book_bus", return_value=(True, "")
            ),
            patch.object(handler.booking_service, "create_booking", return_value=True),
        ):

            await handler.confirm_booking(mock_update_with_callback, mock_context, 1)

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_booking_bus_not_found(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест подтверждения бронирования для несуществующего автобуса"""
        mock_passenger = PassengerFactory.build()

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler.bus_service, "get_bus_by_id", return_value=None),
        ):

            await handler.confirm_booking(mock_update_with_callback, mock_context, 999)

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()


class TestViewBookingHandler:
    """Тесты для ViewBookingHandler"""

    @pytest.fixture
    def mock_callback_query(self):
        """Создает мок CallbackQuery"""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.from_user = Mock(spec=User)
        query.from_user.username = "test_user"
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Создает мок Update с CallbackQuery"""
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        return update

    @pytest.fixture
    def handler(self):
        """Создает экземпляр ViewBookingHandler"""
        return ViewBookingHandler()

    @pytest.mark.asyncio
    async def test_view_bookings_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест успешного просмотра бронирований"""
        mock_passenger = PassengerFactory.build()
        mock_reservations = [ReservationFactory.build()]
        mock_buses = [BusFactory.build()]

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.booking_service,
                "get_user_bookings",
                return_value=mock_reservations,
            ),
            patch.object(handler.bus_service, "get_all_buses", return_value=mock_buses),
        ):

            await handler.view_bookings(mock_update_with_callback, mock_context)

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_booking_menu_no_bookings(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест меню отмены бронирований без бронирований"""
        mock_passenger = PassengerFactory.build()

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler.booking_service, "get_user_bookings", return_value=[]),
            patch.object(handler.bus_service, "get_all_buses", return_value=[]),
        ):

            await handler.cancel_booking_menu(mock_update_with_callback, mock_context)

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_booking_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест успешной отмены бронирования"""
        mock_passenger = PassengerFactory.build()

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler.booking_service, "cancel_booking", return_value=True),
        ):

            await handler.cancel_booking(mock_update_with_callback, mock_context, 1)

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()


class TestWaitingListHandler:
    """Тесты для WaitingListHandler"""

    @pytest.fixture
    def mock_callback_query(self):
        """Создает мок CallbackQuery"""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.from_user = Mock(spec=User)
        query.from_user.username = "test_user"
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Создает мок Update с CallbackQuery"""
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        return update

    @pytest.fixture
    def handler(self):
        """Создает экземпляр WaitingListHandler"""
        return WaitingListHandler()

    @pytest.mark.asyncio
    async def test_show_waiting_list_menu_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест успешного показа меню листа ожидания"""
        mock_passenger = PassengerFactory.build()
        mock_buses = [BusFactory.build()]

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler.bus_service, "get_all_buses", return_value=mock_buses),
        ):

            await handler.show_waiting_list_menu(
                mock_update_with_callback, mock_context
            )

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_to_waiting_list_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест успешного добавления в лист ожидания"""
        mock_passenger = PassengerFactory.build()
        mock_bus = BusFactory.build()

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler.bus_service, "get_bus_by_id", return_value=mock_bus),
            patch.object(
                handler.booking_service, "add_to_waiting_list", return_value=True
            ),
        ):

            await handler.add_to_waiting_list(
                mock_update_with_callback, mock_context, 1
            )

            mock_update_with_callback.callback_query.edit_message_text.assert_called_once()


class TestInfoHandler:
    """Тесты для InfoHandler"""

    @pytest.fixture
    def mock_callback_query(self):
        """Создает мок CallbackQuery"""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.edit_message_media = AsyncMock()
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Создает мок Update с CallbackQuery"""
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        return update

    @pytest.fixture
    def handler(self):
        """Создает экземпляр InfoHandler"""
        return InfoHandler()

    @pytest.mark.asyncio
    async def test_show_how_to_get_there(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест показа информации о том, как добраться"""
        await handler.show_how_to_get_there(mock_update_with_callback, mock_context)

        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_faq(self, handler, mock_update_with_callback, mock_context):
        """Тест показа FAQ"""
        await handler.show_faq(mock_update_with_callback, mock_context)

        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_route_to_hotel(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест показа маршрута до отеля"""
        await handler.show_route_to_hotel(mock_update_with_callback, mock_context)

        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_media.assert_called_once()


class TestExportHandler:
    """Тесты для ExportHandler"""

    @pytest.fixture
    def mock_callback_query(self):
        """Создает мок CallbackQuery"""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.from_user = Mock(spec=User)
        query.from_user.username = "admin_user"
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Создает мок Update с CallbackQuery"""
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        update.effective_user = mock_callback_query.from_user
        update.effective_chat = Mock(spec=Chat)
        update.effective_chat.id = 123456789
        return update

    @pytest.fixture
    def handler(self):
        """Создает экземпляр ExportHandler"""
        return ExportHandler()

    @pytest.mark.asyncio
    async def test_export_buses_admin_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест успешного экспорта данных администратором"""
        mock_passenger = PassengerFactory.build(role="admin")
        mock_context.bot.send_document = AsyncMock()

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.export_service,
                "export_buses_to_excel",
                return_value="temp_file.xlsx",
            ),
            patch.object(handler.export_service, "cleanup_temp_file"),
            patch("builtins.open", mock_open_file_content()),
        ):

            await handler.export_buses(mock_update_with_callback, mock_context)

            mock_update_with_callback.callback_query.answer.assert_called_once()
            mock_context.bot.send_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_buses_non_admin(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест экспорта данных не-администратором"""
        mock_passenger = PassengerFactory.build(role="user")

        with patch.object(
            handler, "get_or_create_passenger", return_value=mock_passenger
        ):
            await handler.export_buses(mock_update_with_callback, mock_context)

            mock_update_with_callback.callback_query.answer.assert_called_once_with(
                "⚠️ Доступ запрещен", show_alert=True
            )


class TestCallbackHandler:
    """Тесты для CallbackHandler"""

    @pytest.fixture
    def mock_callback_query(self):
        """Создает мок CallbackQuery"""
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.data = "book_bus"
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Создает мок Update с CallbackQuery"""
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        return update

    @pytest.fixture
    def handler(self):
        """Создает экземпляр CallbackHandler"""
        return CallbackHandler()

    @pytest.mark.asyncio
    async def test_handle_callback_book_bus(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест обработки callback для бронирования автобуса"""
        with patch.object(
            handler.booking_handler, "show_directions", new_callable=AsyncMock
        ) as mock_show_directions:
            await handler.handle_callback(mock_update_with_callback, mock_context)

            mock_show_directions.assert_called_once_with(
                mock_update_with_callback, mock_context
            )

    @pytest.mark.asyncio
    async def test_handle_callback_view_booking(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест обработки callback для просмотра бронирований"""
        mock_update_with_callback.callback_query.data = "view_booking"

        with patch.object(
            handler.view_booking_handler, "view_bookings", new_callable=AsyncMock
        ) as mock_view_bookings:
            await handler.handle_callback(mock_update_with_callback, mock_context)

            mock_view_bookings.assert_called_once_with(
                mock_update_with_callback, mock_context
            )

    @pytest.mark.asyncio
    async def test_handle_callback_unknown(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Тест обработки неизвестного callback"""
        mock_update_with_callback.callback_query.data = "unknown_callback"
        mock_update_with_callback.callback_query.edit_message_text = AsyncMock()

        await handler.handle_callback(mock_update_with_callback, mock_context)

        mock_update_with_callback.callback_query.edit_message_text.assert_called_once_with(
            "Неизвестная команда."
        )


class TestBroadcastChiefHandler:
    """Тесты для BroadcastChiefHandler"""

    @pytest.fixture
    def mock_callback_query(self):
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.edit_message_reply_markup = AsyncMock()
        query.from_user = Mock(spec=User)
        query.from_user.username = "chief_user"
        query.data = f"{BROADCAST_CHIEF_SELECT_BUS}42"
        query.message = Mock(spec=Message)
        query.message.reply_text = AsyncMock()
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        update.effective_user = mock_callback_query.from_user
        update.effective_chat = Mock(spec=Chat)
        update.effective_chat.id = 123456789
        return update

    @pytest.fixture
    def mock_update_with_message(self):
        update = Mock(spec=Update)
        update.callback_query = None
        update.message = Mock(spec=Message)
        update.message.message_id = 77
        update.message.reply_text = AsyncMock()
        update.effective_chat = Mock(spec=Chat)
        update.effective_chat.id = 555
        update.effective_user = Mock(spec=User)
        update.effective_user.username = "chief_user"
        return update

    @pytest.fixture
    def mock_context(self):
        ctx = Mock(spec=ContextTypes.DEFAULT_TYPE)
        ctx.user_data = {}
        ctx.bot = Mock()
        ctx.bot.copy_message = AsyncMock()
        return ctx

    @pytest.fixture
    def handler(self):
        return BroadcastChiefHandler()

    @pytest.mark.asyncio
    async def test_broadcast_command_forbidden_not_chief(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="user")

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.broadcast_command(mock_update_with_callback, mock_context)

        err.assert_called_once_with(
            mock_update_with_callback, mock_context, "Доступ запрещен"
        )
        mock_update_with_callback.callback_query.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_command_no_buses(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief")

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler.bus_service, "get_buses_by_chief", return_value=[]),
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.broadcast_command(mock_update_with_callback, mock_context)

        mock_update_with_callback.callback_query.answer.assert_called_once()
        err.assert_called_once_with(
            mock_update_with_callback,
            mock_context,
            "На вас не назначено ни одного автобуса",
        )

    @pytest.mark.asyncio
    async def test_broadcast_command_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief", id=10)
        buses = [BusFactory.build(id=1, number="1", destination="Туда")]

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler.bus_service, "get_buses_by_chief", return_value=buses),
        ):
            await handler.broadcast_command(mock_update_with_callback, mock_context)

        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_text.assert_called_once()
        call = mock_update_with_callback.callback_query.edit_message_text.call_args
        text = call.kwargs.get("text", call.args[0] if call.args else None)
        reply_markup = call.kwargs.get("reply_markup")
        assert text == "Выберите автобус:"
        assert reply_markup is not None

    @pytest.mark.asyncio
    async def test_prepare_broadcast_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief", id=3)
        chief_buses = [BusFactory.build(id=42, number="1", destination="Туда")]

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.bus_service,
                "get_buses_by_chief",
                return_value=chief_buses,
            ),
        ):
            await handler.prepare_broadcast(mock_update_with_callback, mock_context)

        assert mock_context.user_data["bus_id"] == 42
        assert mock_context.user_data["broadcast_mode"] is True
        assert mock_context.user_data["broadcast_message"] is None
        mock_update_with_callback.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_broadcast_forbidden(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="user")

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.prepare_broadcast(mock_update_with_callback, mock_context)

        err.assert_called_once_with(
            mock_update_with_callback, mock_context, "Доступ запрещен"
        )

    @pytest.mark.asyncio
    async def test_prepare_broadcast_invalid_callback_data(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief")
        mock_update_with_callback.callback_query.data = "not_a_bus_callback"

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.prepare_broadcast(mock_update_with_callback, mock_context)

        err.assert_called_once_with(
            mock_update_with_callback,
            mock_context,
            "Некорректный выбор автобуса",
        )
        mock_update_with_callback.callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_broadcast_bus_not_assigned_to_chief(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief", id=1)
        mock_update_with_callback.callback_query.data = (
            f"{BROADCAST_CHIEF_SELECT_BUS}42"
        )

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.bus_service,
                "get_buses_by_chief",
                return_value=[
                    BusFactory.build(id=7, number="7", destination="Обратно")
                ],
            ),
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.prepare_broadcast(mock_update_with_callback, mock_context)

        err.assert_called_once_with(
            mock_update_with_callback,
            mock_context,
            "Этот автобус вам не назначен",
        )
        mock_update_with_callback.callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_chief_message_no_broadcast_mode(
        self, handler, mock_update_with_message, mock_context
    ):
        with (
            patch.object(
                handler, "get_or_create_passenger", new_callable=AsyncMock
            ) as mock_get,
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.handle_chief_message(mock_update_with_message, mock_context)

        mock_get.assert_not_called()
        err.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_chief_message_success(
        self, handler, mock_update_with_message, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief")
        mock_context.user_data["broadcast_mode"] = True

        with patch.object(
            handler, "get_or_create_passenger", return_value=mock_passenger
        ):
            await handler.handle_chief_message(mock_update_with_message, mock_context)

        assert mock_context.user_data["broadcast_message"] == {
            "chat_id": 555,
            "message_id": 77,
        }
        mock_update_with_message.message.reply_text.assert_called_once_with(
            "Предпросмотр сообщения:"
        )
        mock_context.bot.copy_message.assert_called_once()
        copy_kw = mock_context.bot.copy_message.call_args.kwargs
        assert copy_kw["chat_id"] == 555
        assert copy_kw["from_chat_id"] == 555
        assert copy_kw["message_id"] == 77
        assert copy_kw["reply_markup"] is not None
        send_btn = copy_kw["reply_markup"].inline_keyboard[0][0]
        assert send_btn.callback_data == f"{BROADCAST_CHIEF_SEND}_77"

    @pytest.mark.asyncio
    async def test_broadcast_send_no_broadcast_mode(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief")
        mock_context.user_data["broadcast_message"] = {
            "chat_id": 1,
            "message_id": 2,
        }

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.broadcast_send(mock_update_with_callback, mock_context)

        err.assert_called_once_with(
            mock_update_with_callback, mock_context, "Ошибка рассылки"
        )

    @pytest.mark.asyncio
    async def test_broadcast_send_no_message_payload(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief")
        mock_context.user_data["broadcast_mode"] = True
        mock_context.user_data["bus_id"] = 1

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.broadcast_send(mock_update_with_callback, mock_context)

        err.assert_called_once_with(
            mock_update_with_callback,
            mock_context,
            "Не найдено сообщение для рассылки",
        )

    @pytest.mark.asyncio
    async def test_broadcast_send_no_passengers(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief")
        mock_context.user_data["broadcast_mode"] = True
        mock_context.user_data["bus_id"] = 1
        mock_context.user_data["broadcast_message"] = {
            "chat_id": 1,
            "message_id": 2,
        }

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.broadcast_service,
                "get_passengers_for_broadcast",
                return_value=[],
            ),
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.broadcast_send(mock_update_with_callback, mock_context)

        err.assert_called_once_with(
            mock_update_with_callback,
            mock_context,
            "Не найдено пассажиров для рассылки",
        )

    @pytest.mark.asyncio
    async def test_broadcast_send_success(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief", id=5)
        recipients = [PassengerFactory.build()]
        mock_context.user_data["broadcast_mode"] = True
        mock_context.user_data["bus_id"] = 1
        mock_context.user_data["broadcast_message"] = {
            "chat_id": 100,
            "message_id": 200,
        }
        mock_update_with_callback.callback_query.data = f"{BROADCAST_CHIEF_SEND}_200"
        mock_update_with_callback.effective_chat.id = 100
        stats = BroadcastStats(sent=3, failed=1, forbidden=0)

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.broadcast_service,
                "get_passengers_for_broadcast",
                return_value=recipients,
            ),
            patch.object(
                handler.broadcast_service,
                "send_broadcast",
                new_callable=AsyncMock,
                return_value=stats,
            ) as send_bc,
        ):
            await handler.broadcast_send(mock_update_with_callback, mock_context)

        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_reply_markup.assert_called_once_with(
            reply_markup=None
        )
        send_bc.assert_called_once_with(
            mock_context.bot,
            recipients,
            100,
            200,
            ANY,
        )
        assert "broadcast_mode" not in mock_context.user_data
        assert "broadcast_message" not in mock_context.user_data
        replies = (
            mock_update_with_callback.callback_query.message.reply_text.call_args_list
        )
        assert any("Начинаю рассылку" in c.args[0] for c in replies)
        completion = next(
            c for c in replies if c.args and "Рассылка завершена" in c.args[0]
        )
        assert "Успешно: 3" in completion.args[0]
        assert completion.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_broadcast_send_callback_message_id_overrides_stored_draft(
        self, handler, mock_update_with_callback, mock_context
    ):
        """Кнопка «Отправить» на старом предпросмотре шлёт то сообщение, чей id в callback."""
        mock_passenger = PassengerFactory.build(role="chief", id=5)
        recipients = [PassengerFactory.build()]
        mock_context.user_data["broadcast_mode"] = True
        mock_context.user_data["bus_id"] = 1
        mock_context.user_data["broadcast_message"] = {
            "chat_id": 100,
            "message_id": 999,
        }
        mock_update_with_callback.callback_query.data = f"{BROADCAST_CHIEF_SEND}_200"
        mock_update_with_callback.effective_chat.id = 100
        stats = BroadcastStats(sent=1, failed=0, forbidden=0)

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(
                handler.broadcast_service,
                "get_passengers_for_broadcast",
                return_value=recipients,
            ),
            patch.object(
                handler.broadcast_service,
                "send_broadcast",
                new_callable=AsyncMock,
                return_value=stats,
            ) as send_bc,
        ):
            await handler.broadcast_send(mock_update_with_callback, mock_context)

        send_bc.assert_called_once_with(
            mock_context.bot,
            recipients,
            100,
            200,
            ANY,
        )

    @pytest.mark.asyncio
    async def test_broadcast_cancel_forbidden(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="user")

        with (
            patch.object(
                handler, "get_or_create_passenger", return_value=mock_passenger
            ),
            patch.object(handler, "_broadcast_error", new_callable=AsyncMock) as err,
        ):
            await handler.broadcast_cancel(mock_update_with_callback, mock_context)

        err.assert_called_once_with(
            mock_update_with_callback, mock_context, "Доступ запрещен"
        )

    @pytest.mark.asyncio
    async def test_broadcast_cancel_clears_state(
        self, handler, mock_update_with_callback, mock_context
    ):
        mock_passenger = PassengerFactory.build(role="chief")
        mock_context.user_data["broadcast_mode"] = True
        mock_context.user_data["broadcast_message"] = {"chat_id": 1, "message_id": 2}
        mock_context.user_data["bus_id"] = 9

        with patch.object(
            handler, "get_or_create_passenger", return_value=mock_passenger
        ):
            await handler.broadcast_cancel(mock_update_with_callback, mock_context)

        assert "broadcast_mode" not in mock_context.user_data
        assert "broadcast_message" not in mock_context.user_data
        assert "bus_id" not in mock_context.user_data


def mock_open_file_content():
    """Создает мок для открытия файла"""
    from unittest.mock import mock_open

    return mock_open(read_data=b"fake excel content")
