import os
import json
import asyncio
import sqlite3
import logging as logger
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)
from dotenv import load_dotenv

load_dotenv(".env")
logging = logger.getLogger(__name__)

# Получение переменных из env
TOKEN = os.getenv("TELEGRAM_TOKEN")
DB_PATH = os.getenv("DB_PATH", "transfer_bot.db")

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Создание таблицы Passengers
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Passengers (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Telegram_username TEXT UNIQUE,
        ChatID TEXT,
        FIO TEXT,
        Phone TEXT,
        Comment TEXT,
        Role TEXT DEFAULT 'user'
    )
    ''')

    # Создание таблицы Buses
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Buses (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Number TEXT,
        Departure_Place TEXT,
        Destination TEXT,
        DepartureDate TEXT,
        DepartureTime TEXT,
        Capacity INTEGER,
        Direction TEXT
    )
    ''')

    # Создание таблицы Reservations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Reservations (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        PassengerID INTEGER,
        BusID INTEGER,
        ReservationDate TEXT,
        Direction TEXT,
        FOREIGN KEY (PassengerID) REFERENCES Passengers (ID),
        FOREIGN KEY (BusID) REFERENCES Buses (ID)
    )
    ''')

    # Создание таблицы WaitingList
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS WaitingList (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        PassengerID INTEGER,
        BusID INTEGER,
        RequestTime TEXT,
        Status TEXT DEFAULT 'Waiting',
        NotificationSent TEXT DEFAULT 'No',
        FOREIGN KEY (PassengerID) REFERENCES Passengers (ID),
        FOREIGN KEY (BusID) REFERENCES Buses (ID)
    )
    ''')

    # Создание таблицы BusOwners
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS BusOwners (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        BusID INTEGER,
        ChiefID INTEGER,
        FOREIGN KEY (BusID) REFERENCES Buses (ID),
        FOREIGN KEY (ChiefID) REFERENCES Passengers (ID)
    )
    ''')

    conn.commit()
    conn.close()

# Инициализируем базу данных при запуске
init_db()

# Функции для работы с базой данных
def get_db_connection():
    return sqlite3.connect(DB_PATH)

def execute_query(query, params=(), fetch_one=False, fetch_all=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)

    if fetch_one:
        result = cursor.fetchone()
    elif fetch_all:
        result = cursor.fetchall()
    else:
        result = None

    conn.commit()
    conn.close()
    return result

def get_passenger_by_username(username):
    return execute_query(
        "SELECT * FROM Passengers WHERE Telegram_username = ?",
        (username,),
        fetch_one=True
    )

def create_passenger(username, chat_id=None):
    execute_query(
        "INSERT INTO Passengers (Telegram_username, ChatID) VALUES (?, ?)",
        (username, str(chat_id) if chat_id else None)
    )
    return execute_query(
        "SELECT * FROM Passengers WHERE Telegram_username = ?",
        (username,),
        fetch_one=True
    )

def update_passenger_chat_id(username, chat_id):
    execute_query(
        "UPDATE Passengers SET ChatID = ? WHERE Telegram_username = ?",
        (str(chat_id), username)
    )

def update_passenger_fio(username, fio):
    execute_query(
        "UPDATE Passengers SET FIO = ? WHERE Telegram_username = ?",
        (fio, username)
    )

def get_all_buses():
    return execute_query("SELECT * FROM Buses", fetch_all=True)

def get_bus_by_id(bus_id):
    return execute_query("SELECT * FROM Buses WHERE ID = ?", (bus_id,), fetch_one=True)

def get_all_reservations():
    return execute_query("SELECT * FROM Reservations", fetch_all=True)

def get_reservations_by_bus(bus_id):
    return execute_query("SELECT * FROM Reservations WHERE BusID = ?", (bus_id,), fetch_all=True)

def get_reservations_by_passenger(passenger_id):
    return execute_query("SELECT * FROM Reservations WHERE PassengerID = ?", (passenger_id,), fetch_all=True)

def create_reservation(passenger_id, bus_id, direction):
    execute_query(
        "INSERT INTO Reservations (PassengerID, BusID, ReservationDate, Direction) VALUES (?, ?, ?, ?)",
        (passenger_id, bus_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), direction)
    )

def delete_reservation_by_id(reservation_id):
    execute_query("DELETE FROM Reservations WHERE ID = ?", (reservation_id,))

def get_waiting_list_records():
    return execute_query("SELECT * FROM WaitingList", fetch_all=True)

def create_waiting_list_record(passenger_id, bus_id):
    execute_query(
        "INSERT INTO WaitingList (PassengerID, BusID, RequestTime) VALUES (?, ?, ?)",
        (passenger_id, bus_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

def update_waiting_list_notification(record_id, status):
    execute_query(
        "UPDATE WaitingList SET NotificationSent = ? WHERE ID = ?",
        (status, record_id)
    )

def get_bus_owners():
    return execute_query("SELECT * FROM BusOwners", fetch_all=True)

FIO, BUS_ID = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Получение chat_id и username пользователя
    chat_id = None
    username = None
    if update.message:
        chat_id = update.message.chat_id
        username = update.message.from_user.username
    elif update.callback_query:
        chat_id = update.callback_query.message.chat_id
        username = update.callback_query.from_user.username

    if username:
        # Проверка, есть ли пользователь в базе
        passenger = get_passenger_by_username(username)

        if passenger:
            # Обновляем ChatID, если он пустой
            if not passenger[2] and chat_id:  # ChatID находится в третьей колонке
                update_passenger_chat_id(username, chat_id)

            # Проверяем роль пользователя
            is_admin = passenger[6] and passenger[6].lower() == "admin"  # Role в седьмой колонке
        else:
            # Создаем нового пользователя
            passenger = create_passenger(username, chat_id)
            is_admin = False

    # Остальной код стартового сообщения
    welcome_message = (
        "Привет! Я трансфер-бот!\n\n"
        "С чем я могу помочь:\n"
        "✔️ Забронировать место в автобусе.\n"
        "✔️ Посмотреть твою текущую бронь.\n"
        "✔️ Отменить запись.\n"
        "✔️ Предоставить информацию о маршрутах и способах доехать до ProductCamp.\n\n"
        "Чтобы начать, выберите нужную кнопку или введите команду /start."
    )
    keyboard = [
        [InlineKeyboardButton("Записаться на автобус", callback_data="book_bus")],
        [InlineKeyboardButton("Посмотреть свою бронь", callback_data="view_booking")],
        [InlineKeyboardButton("Отменить запись", callback_data="cancel_booking")],
        [InlineKeyboardButton("Как добраться?", callback_data="how_to_get_there")],
        [InlineKeyboardButton("FAQ", callback_data="render_faq")],
    ]

    # Добавляем кнопку выгрузки только для администраторов
    if username and is_admin:
        keyboard.append([InlineKeyboardButton("Выгрузить данные", callback_data="export_buses")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(welcome_message, reply_markup=reply_markup)

async def check_user_fio(username):
    """Проверяет, есть ли у пользователя заполненное ФИО"""
    try:
        passenger = get_passenger_by_username(username)
        if passenger and passenger[3] and passenger[3].strip():  # FIO в четвертой колонке
            return True, passenger
        return False, passenger
    except Exception as e:
        logging.error(f"Ошибка при проверке ФИО: {str(e)}")
        return False, None

async def request_fio(update: Update, context: ContextTypes.DEFAULT_TYPE, bus_id=None):
    """Запрашивает ФИО у пользователя"""
    query = update.callback_query
    context.user_data['bus_id'] = bus_id

    if query:
        await query.answer()
        await query.edit_message_text(
            "📝 Для регистрации на автобус необходимо указать ваше ФИО (Фамилия Имя Отчество).\n\n"
            "Пожалуйста, введите ваше полное ФИО:"
        )
    else:
        await update.message.reply_text(
            "📝 Для регистрации на автобус необходимо указать ваше ФИО (Фамилия Имя Отчество).\n\n"
            "Пожалуйста, введите ваше полное ФИО:"
        )

    return FIO

async def handle_fio_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод ФИО пользователем"""
    fio = update.message.text.strip()

    if not fio or len(fio) < 5:
        await update.message.reply_text(
            "❌ ФИО должно содержать не менее 5 символов. Пожалуйста, введите ваше полное ФИО:"
        )
        return FIO

    # Сохраняем ФИО в базе данных
    username = update.message.from_user.username
    try:
        passenger = get_passenger_by_username(username)

        if passenger:
            update_passenger_fio(username, fio)

            # Продолжаем процесс регистрации, если был выбран автобус
            bus_id = context.user_data.pop('bus_id', None)
            if bus_id:
                await confirm_booking_from_fio(update, context, bus_id, fio)
            else:
                await update.message.reply_text(
                    f"✅ ФИО успешно сохранено: {fio}\n\n"
                    "Теперь вы можете записаться на автобус через главное меню."
                )
                await start(update, context)
        else:
            await update.message.reply_text(
                "❌ Ошибка: пользователь не найден в базе данных. Попробуйте начать с команды /start"
            )

    except Exception as e:
        logging.error(f"Ошибка при сохранении ФИО: {str(e)}")
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении ФИО. Попробуйте позже или обратитесь к администратору."
        )

    return ConversationHandler.END

async def cancel_fio_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет ввод ФИО"""
    await update.message.reply_text("Ввод ФИО отменен. Вы можете попробовать снова через главное меню.")
    context.user_data.pop('bus_id', None)
    return ConversationHandler.END

async def confirm_booking_from_fio(update: Update, context: ContextTypes.DEFAULT_TYPE, bus_id: int, fio: str):
    """Продолжает процесс подтверждения брони после ввода ФИО"""
    username = update.message.from_user.username
    passenger = get_passenger_by_username(username)

    if not passenger:
        await update.message.reply_text(
            "К сожалению, я не вижу тебя в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему, либо напиши: @maximovd"
        )
        return

    bus = get_bus_by_id(bus_id)
    if not bus:
        await update.message.reply_text("Автобус не найден.")
        return

    # Проверка, заняты ли все места
    bus_reservations = get_reservations_by_bus(bus_id)
    if len(bus_reservations) >= bus[6]:  # Capacity в седьмой колонке
        await update.message.reply_text("Все места в автобусе уже заняты.")
        return

    # Проверка, есть ли регистрация на этот автобус и направление
    direction_value = bus[7]  # Direction в восьмой колонке
    user_reservations = get_reservations_by_passenger(passenger[0])  # ID в первой колонке

    existing_res = [
        r for r in user_reservations
        if r[2] == bus_id and r[4] == direction_value  # BusID в третьей колонке, Direction в пятой
    ]

    if existing_res:
        await update.message.reply_text("Вы уже зарегистрированы на этот автобус и направление.")
        return

    # Создание новой брони
    create_reservation(passenger[0], bus_id, direction_value)

    await update.message.reply_text(
        f"Вы успешно записаны на автобус: {bus[1]} "  # Number во второй колонке
        f"({bus[4]} {bus[5]}) "  # DepartureDate в пятой, DepartureTime в шестой
        f"{bus[2]}-{bus[3]}\n\n"  # Departure_Place в третьей, Destination в четвертой
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "book_bus":
        await step_select_direction(query, context)
    elif query.data == "view_booking":
        await view_booking(update, context)
    elif query.data == "cancel_booking":
        await cancel_booking(update, context)
    elif query.data.startswith("select_direction_"):
        direction = query.data.split("_", 2)[2]
        await show_buses_for_direction(query, context, direction)
    elif query.data.startswith("select_bus_"):
        bus_id = int(query.data.split("_")[2])
        await confirm_booking(update, context, bus_id)
    elif query.data.startswith("cancel_reservation_"):
        reservation_id = int(query.data.split("_")[2])
        await delete_reservation(update, context, reservation_id)
    elif query.data == "how_to_get_there":
        await show_how_to_get_there(update, context)
    elif query.data == "route_to_hotel":
        await show_how_route_to_hotel(update, context)
    elif query.data == "join_waiting_list":
        await add_user_to_waiting_list_callback(update, context)
    elif query.data == "waiting_list_back":
        await start(update, context)
    elif query.data.startswith("set_waiting_bus_"):
        await handle_select_waiting_bus(update, context)
    elif query.data.startswith("render_faq"):
        await render_faq(update, context)
    elif query.data == "export_buses":
        await export_buses(update, context)
    elif query.data == "back_to_menu":
        await start(update, context)

async def export_buses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import openpyxl
    """Асинхронная выгрузка данных в Excel с обработкой всех ошибок"""
    try:
        # Проверка прав доступа
        user = update.effective_user
        if not user:
            if update.callback_query:
                await update.callback_query.answer("⚠️ Доступ запрещен", show_alert=True)
            return

        # Получаем данные о пользователе
        passenger = get_passenger_by_username(user.username)
        if not passenger or passenger[6].lower() != "admin":  # Role в седьмой колонке
            if update.callback_query:
                await update.callback_query.answer("⚠️ Доступ запрещен", show_alert=True)
            return

        # Уведомление о начале процесса
        if update.callback_query:
            await update.callback_query.answer()
            msg = await update.callback_query.edit_message_text("🔄 Подготовка отчета...")
        else:
            msg = await update.message.reply_text("🔄 Подготовка отчета...")

        # Получение данных из базы
        buses = get_all_buses()
        reservations = get_all_reservations()
        passengers = execute_query("SELECT * FROM Passengers", fetch_all=True)
        bus_owners = get_bus_owners()

        # Создаем временный файл
        temp_file = "temp_export.xlsx"

        try:
            # Создаем Excel-файл
            def generate_excel():
                wb = openpyxl.Workbook()
                wb.remove(wb.active)  # Удаляем дефолтный лист

                # Группируем пассажиров по автобусам
                bus_passengers = {}
                for res in reservations:
                    bus_id = str(res[2])  # BusID в третьей колонке
                    passenger = next((p for p in passengers if str(p[0]) == str(res[1])), None)  # ID в первой колонке
                    if passenger:
                        if bus_id not in bus_passengers:
                            bus_passengers[bus_id] = []
                        bus_passengers[bus_id].append(passenger)

                # Создаем листы для каждого автобуса
                for bus in buses:
                    bus_id = str(bus[0])  # ID в первой колонке
                    sheet_name = f"Автобус {bus[1]}"[:31]  # Number во второй колонке
                    ws = wb.create_sheet(title=sheet_name)

                    # Добавляем заголовок с информацией об автобусе
                    bus_info = [
                        f"Автобус: {bus[1]}",  # Number
                        f"Маршрут: {bus[2]} - {bus[3]}",  # Departure_Place, Destination
                        f"Направление: {bus[7]}",  # Direction
                        f"Дата/время: {bus[4]} {bus[5]}",  # DepartureDate, DepartureTime
                        f"Вместимость: {bus[6]}",  # Capacity
                    ]

                    # Находим ответственных за автобус
                    owners = [o for o in bus_owners if str(o[1]) == bus_id]  # BusID во второй колонке
                    responsible_persons = []
                    for owner in owners:
                        chief = next((p for p in passengers if str(p[0]) == str(owner[2])), None)  # ChiefID в третьей колонке
                        if chief:
                            responsible_persons.append(
                                f"{chief[3]} (@{chief[1]})"  # FIO в четвертой, Telegram_username во второй
                            )

                    if responsible_persons:
                        bus_info.append(f"Ответственные: {', '.join(responsible_persons)}")

                    # Записываем информацию об автобусе
                    for line in bus_info:
                        ws.append([line])

                    # Пустая строка для разделения
                    ws.append([])

                    # Заголовки таблицы пассажиров
                    ws.append(["№", "ФИО", "Username", "Телефон", "Комментарий"])

                    # Данные пассажиров
                    for idx, passenger in enumerate(bus_passengers.get(bus_id, []), start=1):
                        ws.append([
                            idx,
                            passenger[3],  # FIO
                            f"@{passenger[1]}",  # Telegram_username
                            passenger[4],  # Phone
                            passenger[5]  # Comment
                        ])

                wb.save(temp_file)

            await asyncio.to_thread(generate_excel)
            await msg.edit_text("📤 Отправляем файл...")

            # Отправка файла
            with open(temp_file, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=f"bus_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    caption="✅ Отчет по автобусам"
                )

            await msg.delete()

        except Exception as e:
            error_msg = f"❌ Ошибка при генерации отчета: {str(e)}"
            await msg.edit_text(error_msg)
            return
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file):
                os.remove(temp_file)

    except Exception as e:
        error_msg = f"❌ Ошибка при выгрузке: {str(e)}"
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def step_select_direction(query, context):
    buses = get_all_buses()

    # Получение уникальных направлений только из активных автобусов
    directions = sorted(set(
        b[7] for b in buses
        if b[7] and b[7].strip() and (len(b) <= 8 or bool(b[8]))  # Только активные автобусы
    ))

    if not directions:
        await query.edit_message_text("На данный момент нет доступных направлений.")
        return

    # Формируем кнопки с направлениями
    keyboard = [
        [InlineKeyboardButton(direction, callback_data=f"select_direction_{direction}")]
        for direction in reversed(directions)
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите направление:", reply_markup=reply_markup)

async def show_buses_for_direction(query, context, direction):
    buses = get_all_buses()
    reservations = get_all_reservations()

    username = query.from_user.username
    passenger = get_passenger_by_username(username)
    if not passenger:
        await query.edit_message_text(
            "К сожалению, я не вижу тебя в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему, либо напиши: @maximovd"
        )
        return

    # Проверка, есть ли уже регистрация у пользователя на данное направление
    user_reservations = get_reservations_by_passenger(passenger[0])
    existing_res = [
        r for r in user_reservations
        if r[4] == direction
    ]
    if existing_res:
        await query.edit_message_text("Вы уже зарегистрированы на это направление.")
        return

    # Фильтрация автобусов по выбранному направлению и активности
    # Показываем только активные автобусы (is_active = TRUE или поле отсутствует)
    buses_for_direction = [
        b for b in buses
        if b[7] == direction and (len(b) <= 8 or bool(b[8]))  # is_active в девятой колонке
    ]

    # Если нет активных автобусов для направления
    if not buses_for_direction:
        await query.edit_message_text(
            f"На данный момент нет доступных автобусов для направления {direction}.\n"
            "Пожалуйста, проверьте позже или выберите другое направление."
        )
        return

    # Формируем сообщение
    message = f"Доступные автобусы для направления {direction}:\n\n"

    for bus in buses_for_direction:
        capacity = bus[6]
        booked = sum(1 for r in reservations if r[2] == bus[0])
        free = capacity - booked
        status = f"Свободных мест: {free}" if free > 0 else "Мест нет"
        message += (
            f"Автобус {bus[1]} ({bus[4]} {bus[5]}): {status}\n"
        )

    # Создавать кнопки для всех активных автобусов
    keyboard = []

    for bus in buses_for_direction:
        capacity = bus[6]
        booked = sum(1 for r in reservations if r[2] == bus[0])
        free = capacity - booked

        if free > 0:
            keyboard.append([
                InlineKeyboardButton(
                    f"Автобус {bus[1]} - {free} мест",
                    callback_data=f"select_bus_{bus[0]}"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    f"Автобус {bus[1]} - в лист ожидания",
                    callback_data=f"set_waiting_bus_{bus[0]}"
                )
            ])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup)

async def view_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    username = query.from_user.username
    passenger = get_passenger_by_username(username)

    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not passenger:
        await query.edit_message_text(
            "К сожалению, я не вижу тебя в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему, либо напиши: @maximovd",
            reply_markup=reply_markup,
        )
        return

    reservations = get_reservations_by_passenger(passenger[0])  # ID в первой колонке
    buses = get_all_buses()

    if not reservations:
        await query.edit_message_text("Вы не записаны ни на один автобус", reply_markup=reply_markup)
        return

    message = "Ваши записи:\n\n"
    keyboard = []
    for res in reservations:
        bus = next((b for b in buses if b[0] == res[2]), None)  # BusID в третьей колонке
        if bus:
            message += (
                f"Автобус: {bus[1]} ({bus[4]} {bus[5]}) "  # Number, DepartureDate, DepartureTime
                f"({bus[2]}-{bus[3]})-{bus[7]}\n"  # Departure_Place, Destination, Direction
            )
            keyboard.append([InlineKeyboardButton(
                f"Отменить бронь: Автобус: {bus[1]}-{bus[7]}",  # Number, Direction
                callback_data=f"cancel_reservation_{res[0]}"  # ID
            )])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)

async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    username = query.from_user.username
    passenger = get_passenger_by_username(username)

    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not passenger:
        await query.edit_message_text(
            "К сожалению, я не вижу тебя в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему, либо напиши: @maximovd",
            reply_markup=reply_markup,
        )
        return

    reservations = get_reservations_by_passenger(passenger[0])  # ID в первой колонке
    buses = get_all_buses()

    if not reservations:
        await query.edit_message_text("У вас нет записей для отмены", reply_markup=reply_markup)
        return

    keyboard = []
    for res in reservations:
        bus = next((b for b in buses if b[0] == res[2]), None)  # BusID в третьей колонке
        if bus:
            button_text = (
                f"Автобус {bus[1]} ({bus[4]} {bus[5]}) Направление: {bus[7]}"  # Number, DepartureDate, DepartureTime, Direction
            )
            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"cancel_reservation_{res[0]}"  # ID
                )
            ])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите запись для отмены:", reply_markup=reply_markup
    )

async def delete_reservation(update, context, reservation_id):
    """Удаление записи"""
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Проверяем, принадлежит ли запись пользователю
    username = query.from_user.username
    passenger = get_passenger_by_username(username)

    if not passenger:
        await query.edit_message_text("Ошибка: пользователь не найден.", reply_markup=reply_markup)
        return

    # Получаем запись
    reservation = execute_query(
        "SELECT * FROM Reservations WHERE ID = ? AND PassengerID = ?",
        (reservation_id, passenger[0]),  # ID в первой колонке
        fetch_one=True
    )

    if not reservation:
        await query.edit_message_text("Запись не найдена или вам не принадлежит.", reply_markup=reply_markup)
        return

    # Удаляем запись
    delete_reservation_by_id(reservation_id)
    await query.edit_message_text("Ваша запись отменена.", reply_markup=reply_markup)

async def show_how_to_get_there(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_message = ("""
    Альтернативные варианты как добраться из Москвы до отеля «Азимут Переславль-Залесский» и обратно:

    1). Поездом

    Поезда № 102Я, 104Я, 106Я Москва (Ярославский вокзал) - ст. Берендеево. По субботам и воскресеньям ходит дополнительный поезд 928М. Выйти нужно на станции Берендеево, путь до отеля займет 15 минут на такси.
    Актуальное расписание поездов на сайте РЖД: https://www.rzd.ru/

    2). Автобусом

    От Центрального автовокзала Москвы (м. Щелковская) автобусы прибывают на автовокзал Переславль-Залесский (Московская улица, 113). Путь до отеля займет 20 минут на такси.
    Актуальное расписание автобусов на сайте Туту: https://bus.tutu.ru

    3) Автомобиль или такси

    Адрес отеля  «Азимут Переславль-Залесский»: Ярославская обл., Переславский р-н, с. Иванисово, ул. Дачная, д. 100.
    Для гостей, не проживающих в отеле оплата парковки в размере - 200 руб. в сутки, первый час парковки бесплатный. Парковка для проживающих гостей бесплатная."""
)
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(info_message, reply_markup=reply_markup, parse_mode="Markdown")

async def render_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    faq_text = (
        "1. **Как записаться?** Открой бота → нажми /start → записаться на автобус → выбери направление → выбери автобус → нажми «Записаться». Готово!\n"
        "\n"
        "2. **Что, если я хочу и туда, и обратно?** Нужно пройти процесс записи дважды — сначала в одном направлении, потом в другом.\n"
        "\n"
        "3. **Что, если в нужном автобусе нет мест?** Это значит, что все места на выбранный автобус уже заняты. Однако ты всё равно можешь выбрать его в боте, чтобы попасть в лист ожидания. Если кто-то откажется от своей брони, ты получишь уведомление от бота и сможешь забронировать освободившееся место.\n"
        "\n"
        "4. **Как посмотреть свою бронь?** Через кнопку «Мои записи» в меню. Там же можно отменить любую бронь.\n"
        "\n"
        "5. **Могу ли я изменить автобус?** Да — сначала отмени текущую запись, потом выбери другой автобус.\n"
        "\n"
        "6. **Почему бот не пускает?** Вероятно, твой Telegram-ник не совпадает с базой волонтёров. Обратись к своему старшему или проверь, с какого аккаунта ты зашёл.\n"
        "\n"
        "7. **Куда писать, если ничего не работает?** Если бот не пускает или что-то сломалось, напиши Данилу @maximovd или в общий чат ProductCamp во вкладку «Трансфер»\n"
        "\n"
        "8. **Что значит «в листе ожидания»?** Это значит, что автобус, на который ты хотел(а) записаться, уже заполден. Однако бот всё равно добавил тебя в лист ожидания. Если кто-то отменит бронь — ты получишь уведомление и сможешь забронировать освободившееся место.\n"
        "\n"
        "9. **Можно ли записаться на несколько автобусов сразу?** Нет, по одному направлению можно иметь только одну активную запись. Сначала отмени предыдущую, если хочешь сменить автобус.\n"
        "\n"
        "10.**А если я хочу добраться до ProductCamp самостоятельно?** В боте ты сможешь найти информацию о маршрутах и способах доехать до ProductCamp. Для этого просто зайди в бота, нажми «/start», а затем в меню нажми на кнопку «Как добраться до Product Camp».\n"
        "\n"
        "11.**Почему автобусов так мало и расписание такое неудобное?** Мы понимаем, что расписание может подойти не всем. У нас ограниченный бюджет, и мы старались распределить автобусы так, чтобы охватить максимальное число кэмпчан. Надеемся, что выбранные будут удобными для большинства.\n"
        "\n"
        "Пользуйся ботом, экономь своё время и не забудь забронировать место заранее! Если будут вопросы — мы будем в общем чате ProductCamp во вкладку «Трансфер» 😊\n"
    )
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(faq_text, parse_mode="Markdown", reply_markup=reply_markup)

async def show_how_route_to_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    image_url = "https://lh7-rt.googleusercontent.com/docsz/AD_4nXeTgIHj8xL5841KSiK2TweN4zWuVuVyl9kEzjhLycPcNMlVY3Q2K4ArRzdy1ZpGIXbS6-hYWmNEpYq4h6B2py8EmfDX1w3K225docCZAXI3Esh6iKHBPKhad-QUSq1ND68n4HhE0w?key=pfElDP_kPhatX9dfoNbfQj_I"

    info_text = (
    "Мероприятие в конгресс-отеле [Ареал](https://www.areal-hotel.ru/about-the-hotel/) в Московской области.\n"
    "Адрес: Сиреневая ул., 21, микрорайон Родинки, д. Новая Купавна.\n"
    "Метки на картах: [гугл-карта](https://goo.gl/maps/7doSnWnGg4mb8QqG6), [яндекс-карта](https://yandex.ru/maps/-/CCUWeOGxwD)\n\n"
    "🚌 **Способы добраться до Отеля:**\n"
    "На организованном трансфере, время в пути около 1 часа: в соответствии с расписанием трансфера будут организованы автобусы от станции метро Партизанская.\n"
    "Ссылка на точку: https://clck.ru/348UK5"
    )
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_media(
        media=InputMediaPhoto(media=image_url, caption=info_text, parse_mode="Markdown"),
        reply_markup=reply_markup,
    )

async def confirm_booking(update, context, bus_id):
    """Подтверждение записи на автобус с проверкой занятости мест"""
    query = update.callback_query
    username = query.from_user.username
    passenger = get_passenger_by_username(username)

    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not passenger:
        await query.edit_message_text(
            "К сожалению, я не вижу тебя в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему, либо напиши: @maximovd",
            reply_markup=reply_markup,
        )
        return

    bus = get_bus_by_id(bus_id)
    if not bus:
        await query.edit_message_text("Автобус не найден.")
        return

    # Проверка, заняты ли все места
    bus_reservations = get_reservations_by_bus(bus_id)
    if len(bus_reservations) >= bus[6]:  # Capacity в седьмой колонке
        await query.edit_message_text("Все места в автобусе уже заняты.", reply_markup=reply_markup)
        return

    # Проверка, есть ли регистрация на этот автобус и направление
    direction_value = bus[7]  # Direction в восьмой колонке
    user_reservations = get_reservations_by_passenger(passenger[0])  # ID в первой колонке

    existing_res = [
        r for r in user_reservations
        if r[2] == bus_id and r[4] == direction_value  # BusID в третьей колонке, Direction в пятой
    ]

    if existing_res:
        await query.edit_message_text("Вы уже зарегистрированы на этот автобус и направление.")
        return

    # Создание новой брони
    create_reservation(passenger[0], bus_id, direction_value)

    await query.edit_message_text(
        f"Вы успешно записаны на автобус: {bus[1]} "  # Number во второй колонке
        f"({bus[4]} {bus[5]}) "  # DepartureDate в пятой, DepartureTime в шестой
        f"{bus[2]}-{bus[3]}",  # Departure_Place в третьей, Destination в четвертой
        reply_markup=reply_markup,
    )

    # Обновляем статус в листе ожидания, если есть
    waiting_records = execute_query(
        "SELECT * FROM WaitingList WHERE PassengerID = ? AND BusID = ? AND Status = 'Waiting'",
        (passenger[0], bus_id),
        fetch_all=True
    )

    for wait in waiting_records:
        execute_query(
            "UPDATE WaitingList SET Status = 'Confirmed', NotificationSent = 'Yes' WHERE ID = ?",
            (wait[0],)  # ID в первой колонке
        )

async def process_waiting_list(application: Application, single_notification: bool = True):
    """Автоматическая проверка и оповещение о свободных местах"""
    try:
        # Получаем все необходимые данные
        buses = get_all_buses()
        reservations = get_all_reservations()
        waiting_records = get_waiting_list_records()
        passengers = execute_query("SELECT * FROM Passengers", fetch_all=True)

        # Подготавливаем данные о вместимости автобусов
        bus_capacity = {}
        for b in buses:
            # Проверяем активен ли автобус
            if len(b) > 8 and not bool(b[8]):
                continue  # Пропускаем неактивные автобусы
            bus_capacity[b[0]] = b[6]

        # Подсчитываем количество броней для каждого автобуса
        bus_reserved_counts = {}
        for b in buses:
            bus_reserved_counts[b[0]] = sum(1 for r in reservations if r[2] == b[0])  # BusID в третьей колонке

        # Текущее время для проверки 2-х суток
        current_time = datetime.now()

        # Группируем ожидающих по автобусам
        bus_waiting_groups = {}
        for wait in waiting_records:
            if (wait[4] == "Waiting" and  # Status в пятой колонке
                wait[5] == "No" and  # NotificationSent в шестой колонке
                wait[3]):  # RequestTime в четвертой колонке

                try:
                    bus_id = wait[2]  # BusID в третьей колонке
                    if bus_id not in bus_waiting_groups:
                        bus_waiting_groups[bus_id] = []

                    request_time = datetime.strptime(wait[3], "%Y-%m-%d %H:%M:%S")
                    bus_waiting_groups[bus_id].append((request_time, wait))
                except (ValueError, TypeError):
                    continue

        # Для каждого автобуса с ожидающими и свободными местами
        for bus_id, waiting_list in bus_waiting_groups.items():
            # Пропускаем если автобус не существует или нет свободных мест
            if bus_id not in bus_capacity:
                continue

            free_places = bus_capacity[bus_id] - bus_reserved_counts.get(bus_id, 0)
            if free_places <= 0:
                continue

            # Если нужно отправить только одно уведомление - берем самого раннего
            if single_notification and waiting_list:
                waiting_list.sort(key=lambda x: x[0])
                waiting_list = [waiting_list[0]]

            for _, wait in waiting_list:
                passenger_id = wait[1]  # PassengerID во второй колонке

                # Проверка времени для сброса NotificationSent
                request_time_str = wait[3]  # RequestTime в четвертой колонке
                if request_time_str:
                    try:
                        request_time = datetime.strptime(request_time_str, "%Y-%m-%d %H:%M:%S")
                        time_diff = current_time - request_time

                        # Если прошло более 2 суток и статус Waiting
                        if time_diff.total_seconds() > 172800 and wait[5] == "Yes":  # NotificationSent в шестой колонке
                            execute_query(
                                "UPDATE WaitingList SET NotificationSent = 'No' WHERE ID = ?",
                                (wait[0],)  # ID в первой колонке
                            )
                            continue
                    except (ValueError, TypeError):
                        pass

                # Находим пассажира и автобус
                passenger = next((p for p in passengers if p[0] == passenger_id), None)  # ID в первой колонке
                bus = next((b for b in buses if b[0] == bus_id), None)  # ID в первой колонке

                if passenger and bus and passenger[2]:  # ChatID в третьей колонке
                    # Создаем клавиатуру для подтверждения
                    keyboard = [
                        [InlineKeyboardButton(
                            "Подтвердить бронь",
                            callback_data=f"select_bus_{bus_id}"
                        )]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    # Отправляем уведомление
                    try:
                        await application.bot.send_message(
                            chat_id=passenger[2],  # ChatID в третьей колонке
                            text=f"🚌 Место на автобус {bus[1]} ({bus[4]} {bus[5]}) теперь доступно!\n"  # Number, DepartureDate, DepartureTime
                                 "❗У вас есть 10 минут, чтобы подтвердить бронь, после бот отправит пуш следующему в листе ожидания. \n"
                                 "Нажмите кнопку ниже чтобы подтвердить бронь:",
                            reply_markup=reply_markup
                        )

                        # Обновляем статус NotificationSent
                        execute_query(
                            "UPDATE WaitingList SET NotificationSent = 'Yes' WHERE ID = ?",
                            (wait[0],)  # ID в первой колонке
                        )

                        # Логируем успешную отправку
                        logging.info(f"Уведомление отправлено пассажиру {passenger_id} для автобуса {bus_id}")

                    except Exception as e:
                        logging.error(f"Ошибка отправки уведомления пассажиру {passenger_id}: {str(e)}")

    except Exception as e:
        logging.error(f"Ошибка в process_waiting_list: {str(e)}")

async def post_init(application: Application):
    asyncio.create_task(periodic(application))

async def confirm_waiting(update, context):
    user = update.message.from_user
    passenger = get_passenger_by_username(user.username)
    if not passenger:
        await update.message.reply_text("Пользователь не найден.")
        return

    waiting_records = execute_query(
        "SELECT * FROM WaitingList WHERE PassengerID = ? AND Status = 'Confirmed'",
        (passenger[0],),  # ID в первой колонке
        fetch_all=True
    )

    if waiting_records:
        await update.message.reply_text("Вы уже подтвердили бронь.")
        return

    waiting_records = execute_query(
        "SELECT * FROM WaitingList WHERE PassengerID = ? AND Status = 'Waiting'",
        (passenger[0],),  # ID в первой колонке
        fetch_all=True
    )

    if not waiting_records:
        await update.message.reply_text("Нет ожидающих для подтверждения.")
        return

    for wait in waiting_records:
        bus_id = wait[2]  # BusID в третьей колонке
        bus = get_bus_by_id(bus_id)
        if not bus:
            await update.message.reply_text("Автобус не найден.")
            return

        # Проверяем, есть ли свободные места
        bus_reservations = get_reservations_by_bus(bus_id)
        if len(bus_reservations) >= bus[6]:  # Capacity в седьмой колонке
            await update.message.reply_text("Места в автобусе уже заняты.")
            return

        # Создаем бронь
        create_reservation(passenger[0], bus_id, bus[7])  # Direction в восьмой колонке

        # Обновляем статус в листе ожидания
        execute_query(
            "UPDATE WaitingList SET Status = 'Confirmed', NotificationSent = 'Yes' WHERE ID = ?",
            (wait[0],)  # ID в первой колонке
        )

        await update.message.reply_text("Бронь подтверждена. Удачи!")
        return

async def add_user_to_waiting_list_callback(update, context):
    query = update.callback_query
    user = query.from_user
    passenger = get_passenger_by_username(user.username)
    if not passenger:
        await query.answer("Пользователь не найден.")
        return

    # Предложить выбрать автобус для постановки в очередь
    buses = get_all_buses()
    if not buses:
        await query.answer("Нет автобусов для очереди.")
        return

    keyboard = [
        [InlineKeyboardButton(
            f"Автобус {b[1]} ({b[4]} {b[5]})",  # Number, DepartureDate, DepartureTime
            callback_data=f"set_waiting_bus_{b[0]}"  # ID
        )]
        for b in buses
    ]
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите автобус для постановки в очередь:", reply_markup=reply_markup)

async def handle_select_waiting_bus(update, context):
    query = update.callback_query

    if query.data.startswith("set_waiting_bus_"):
        bus_id = int(query.data.split("_", 3)[3])
        user = query.from_user
        passenger = get_passenger_by_username(user.username)

        if not passenger:
            await query.answer("Пользователь не найден.")
            return

        # Проверяем, не находится ли пользователь уже в очереди на этот автобус
        existing = execute_query(
            "SELECT * FROM WaitingList WHERE PassengerID = ? AND BusID = ? AND Status = 'Waiting'",
            (passenger[0], bus_id),  # ID в первой колонке
            fetch_all=True
        )

        if existing:
            await query.edit_message_text("Вы уже в очереди на этот автобус.")
            await query.answer()
            return

        # Добавляем в лист ожидания
        create_waiting_list_record(passenger[0], bus_id)
        await query.edit_message_text("Вы поставлены в очередь на выбранный автобус. Ожидайте уведомлений о доступных местах.")
        await query.answer()

async def handle_waiting_list_entry(update, context):
    # Пользователь вызвал команду или кнопку для вхождения в лист ожидания
    await add_user_to_waiting_list_callback(update, context)

async def handle_waiting_list_back(update, context):
    await start(update, context)

async def periodic(application):
    while True:
        try:
            await process_waiting_list(application)
        except Exception as e:
            print(f"Ошибка: {e}")
        await asyncio.sleep(600)

def main():
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("confirm", confirm_waiting))
    application.add_handler(CommandHandler("wait", handle_waiting_list_entry))
    # Периодическая обработка листа ожидания


    application.run_polling()

if __name__ == "__main__":
    main()
