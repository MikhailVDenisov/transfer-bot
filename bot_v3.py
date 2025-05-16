import os
import json
import asyncio

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv(".env")

# Получение переменных из env
TOKEN = os.getenv("TELEGRAM_TOKEN")
spreadsheet_id = os.getenv("GOOGLE_OAUTH_TOKEN")
credentials_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

credentials_info = json.loads(credentials_json_str)
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info)
client = gspread.authorize(credentials)

spreadsheet = client.open_by_key(spreadsheet_id)

# Получение листов
passengers_sheet = spreadsheet.worksheet("Passengers")
buses_sheet = spreadsheet.worksheet("Buses")
reservations_sheet = spreadsheet.worksheet("Reservations")


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
        try:
            # Попытка найти запись по username
            # Предполагаем, что в таблице есть столбец "Telegram_username"
            cell = passengers_sheet.find(username)
            # Проверка, если поле ChatID пустое, обновляем его
            chatid_col_idx = None
            headers = passengers_sheet.row_values(1)
            if "ChatID" in headers:
                chatid_col_idx = headers.index("ChatID") + 1
            if chatid_col_idx:
                current_value = passengers_sheet.cell(cell.row, chatid_col_idx).value
                if not current_value and chat_id:
                    passengers_sheet.update_cell(cell.row, chatid_col_idx, str(chat_id))
        except:
            # Пользователь не найден в таблице, можно оставить так или добавить лог
            pass

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
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(welcome_message, reply_markup=reply_markup)

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
    elif query.data == "back_to_menu":
        await start(update, context)

async def step_select_direction(query, context):
    buses = buses_sheet.get_all_records()

    # Получение уникальных направлений, которые есть у автобусов
    directions = sorted(set(b['Direction'] for b in buses if 'Direction' in b and b['Direction'].strip()))
    
    # Проверка, есть ли вообще направления
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
    buses = buses_sheet.get_all_records()
    reservations = reservations_sheet.get_all_records()

    username = query.from_user.username
    passengers = passengers_sheet.get_all_records()
    passenger = next((p for p in passengers if p["Telegram_username"] == username), None)
    if not passenger:
        await query.edit_message_text(
            "К сожалению, я не вижу тебя в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему, либо напиши: @havingfreckles"
        )
        return

    # Проверка, есть ли уже регистрация у пользователя на данное направление
    existing_res = [
        r for r in reservations
        if r["Passenger"] == passenger["ID"] and r.get("Direction", "") == direction
    ]
    if existing_res:
        await query.edit_message_text("Вы уже зарегистрированы на это направление.")
        return

    # Фильтрация автобусов по выбранному направлению
    buses_for_direction = [b for b in buses if b.get("Direction") == direction]

    # Собираем информацию о занятости и статусе автобусов
    bus_info_list = []
    for bus in buses_for_direction:
        bus_id = bus["ID"]
        capacity_value = bus.get("Capacity", "")
        try:
            capacity = int(capacity_value.strip())
        except:
            capacity = 0
        bus_reservations = [r for r in reservations if r["Bus"] == bus_id]
        booked = len(bus_reservations)
        free_places = capacity - booked
        bus['FreePlaces'] = free_places
        has_places = free_places > 0
        bus_info_list.append((bus, has_places))

    # Отобрать все автобусы даже если они заполнены
    all_buses = buses_for_direction

    # Формируем сообщение
    message = f"Все автобусы для направления {direction}:\n\n"

    for bus in all_buses:
        capacity_str = bus.get("Capacity", "0")
        try:
            capacity = int(capacity_str)
        except:
            capacity = 0
        booked = sum(1 for r in reservations if r["Bus"] == bus["ID"])
        free = capacity - booked
        if free <= 0:
            status = "Свободных мест: 0"
        else:
            status = f"Свободных мест: {free}"
        message += (
            f"Автобус {bus['ID']} ({bus['DepartureDate']} {bus['DepartureTime']}): {status}\n"
        )

    # Создавать кнопки для всех автобусов:
    # - тех, у которых есть свободные места — кнопка для регистрации
    # - тех, что заполнены — кнопка для постановки в очередь
    keyboard = []

    for bus in all_buses:
        capacity_str = bus.get("Capacity", "0")
        try:
            capacity = int(capacity_str)
        except:
            capacity = 0
        booked = sum(1 for r in reservations if r["Bus"] == bus["ID"])
        free = capacity - booked
        if free > 0:
            # Есть свободные места — кнопка "Записаться"
            keyboard.append([
                InlineKeyboardButton(
                    f"Автобус {bus['Number']} - {free} мест",
                    callback_data=f"select_bus_{bus['ID']}"
                )
            ])
        else:
            # Полностью заполнен — кнопка "Записан и в очередь"
            keyboard.append([
                InlineKeyboardButton(
                    f"Автобус {bus['Number']} - в лист ожидания",
                    callback_data=f"set_waiting_bus_{bus['ID']}"
                )
            ])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup)


async def view_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    username = query.from_user.username
    passengers = passengers_sheet.get_all_records()
    passenger = next((p for p in passengers if p["Telegram_username"] == username), None)
    if not passenger:
        await query.edit_message_text(
            "К сожалению, я не вижу тебя в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему, либо напиши: @havingfreckles"
        )
        return

    reservations = reservations_sheet.get_all_records()
    buses = buses_sheet.get_all_records()

    user_res = [r for r in reservations if r["Passenger"] == passenger["ID"]]
    if not user_res:
        await query.edit_message_text("Вы не записаны ни на один автобус")
        return

    message = "Ваши записи:\n\n"
    keyboard = []
    for res in user_res:
        bus = next((b for b in buses if b["ID"] == res["Bus"]), None)
        if bus:
            message += (
                f"Автобус: {bus['Number']} ({bus['DepartureDate']} {bus['DepartureTime']}) "
                f"({bus['Departure_Place']}-{bus['Destination']})-{bus['Direction']}\n"
            )
            keyboard.append([InlineKeyboardButton(f"Отменить бронь: Автобус: {bus['Number']}-{bus['Direction']}", callback_data=f"cancel_reservation_{res['ID']}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)

async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    username = query.from_user.username
    passengers = passengers_sheet.get_all_records()
    passenger = next((p for p in passengers if p["Telegram_username"] == username), None)
    if not passenger:
        await query.edit_message_text(
            "К сожалению, я не вижу тебя в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему, либо напиши: @havingfreckles"
        )
        return

    reservations = reservations_sheet.get_all_records()
    buses = buses_sheet.get_all_records()

    user_res = [r for r in reservations if r["Passenger"] == passenger["ID"]]
    if not user_res:
        await query.edit_message_text("У вас нет записей для отмены")
        return

    keyboard = []
    for res in user_res:
        bus = next((b for b in buses if b["ID"] == res["Bus"]), None)
        if bus:
            button_text = (
                f"Автобус {bus['Number']} ({bus['DepartureDate']} {bus['DepartureTime']}) Направление: {bus['Direction']}"
            )
            keyboard.append(
                [InlineKeyboardButton(
                    button_text,
                    callback_data=f"cancel_reservation_{res['ID']}"
                )]
            )

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите запись для отмены:", reply_markup=reply_markup
    )

async def delete_reservation(update, context, reservation_id):
    """Удаление записи"""
    query = update.callback_query
    username = query.from_user.username

    reservations = reservations_sheet.get_all_records()
    reservation = next((r for r in reservations if str(r["ID"]) == str(reservation_id)), None)

    if not reservation:
        await query.edit_message_text("Запись не найдена.")
        return

    passengers = passengers_sheet.get_all_records()
    passenger = next((p for p in passengers if p["Telegram_username"] == username), None)

    if not passenger or str(reservation["Passenger"]) != str(passenger["ID"]):
        await query.edit_message_text("Ошибка: эта запись вам не принадлежит.")
        return

    cell = reservations_sheet.find(str(reservation_id))
    reservations_sheet.delete_rows(cell.row)
    await query.edit_message_text("Ваша запись отменена.")

async def show_how_to_get_there(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_message = (
        "Планируете добираться до мероприятия самостоятельно?\n"
        "Мы собрали для вас удобные варианты проезда различными видами транспорта – выбирайте свой!\n"
        "**Адрес отеля**: Московская область, Ногинский район, д. Новая Купавна, местечко Родинки, ул. Сиреневая, д.21 стр.1\n"
        "**Метки на картах**: [Гугл-карта](https://goo.gl/maps/7doSnWnGg4mb8QqG6), [Яндекс-карта](https://yandex.ru/maps/-/CCUWeOGxwD)\n\n"
        "На электричке (время в пути ~2,5 часа)\n"
        "от Курского или Белорусского вокзала до станции Купавна (цена билета ~150 руб), \n"
        "затем 20-30 мин на такси (~650 руб.) до отеля Ареал\n"
        "или автобусе 37щ до ост. Улица Орлова, 26 и пешком/на такси (~350 руб.) до отеля 3 км.\n\n"
        "Расписание электричек*: [туда](https://ticket.rzd.ru/searchresults/v/1/5a323c29340c7441a0a556bb/5cd18d837081a600437b02f2/) и [обратно](https://ticket.rzd.ru/searchresults/v/1/5cd18d837081a600437b02f2/5a323c29340c7441a0a556bb/) (пожалуйста, внимательно проверяйте станцию отправления и прибытия в Москве, расписание указано для двух вокзалов).\n\n"
        "На автобусе (время в пути ~1,5 часа)\n"
        "от ст. м. Партизанская/МЦК Измайлово (1 выход из метро) - автобусы [№322](https://t/$', '') или [№399](https://t.$') или [№444](https://t.$')\n"
        "от м. Новогиреево маршрутное такси [№1209к](https://t.$'), [№587к](https://t.$') или [№886к](https://t.$') (6 выход из метро); \n"
        "до ост. Новая Купавна, перейти Горьковское шоссе, \n"
        "далее на такси 5-7 мин (~250 руб.) или пешком около 2,3 км по указателям (для спортивных участников).\n\n"
        "Расписание автобусов*: [туда](https://rasp.yandex.ru/search/bus/?fromId=c213&fromName=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0&toId=c33762&toName=%D0%9D%D0%BE%D0%B2%D0%B0%D1%8F+%D0%9A%D1%83%D0%BF%D0%B0%D0%B2%D0%BD%D0%B0&when=23+%D0%BC%D0%B0%D1%8F)/[обратно](https://rasp.yandex.ru/search/bus/?fromId=c33762&fromName=%D0%9D%D0%BE%D0%B2%D0%B0%D1%8F+%D0%9A%D1%83%D0%BF%D0%B0%D0%B2%D0%BD%D0%B0&toId=c213&toName=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0&when=25+%D0%BC%D0%B0%D1%8F) (пожалуйста, внимательно проверяйте даты отправления и прибытия, данные актуальны для пятницы 23 мая и воскресенья 25 мая соответственно).\n\n"
        "На машине (время в пути ~1 час)\n"
        "на территории отеля есть бесплатная парковка на 190 мест, находится перед въездом в отель (пропуск не требуется). Подъезд со стороны Горьковского шоссе. \n"
        "Если есть свободные места и вы можете взять попутчиков, укажите это в чате: https://t.me/c/123456789/101112, начните знакомство еще до кэмпа!😉\n\n"
        "**Из аэропортов Москвы**\n"
        "Шереметьево (~2,5 часа)\n"
        "[Аэроэкспрессе](https://aeroexpress.ru/)(~650 руб.) до Окружной, пересесть на МЦК до ст. Измайловская;\n"
        "или [Экспресс автобус](https://aeroexpress.ru/) (~400 руб.) до Ховрино, затем на МЦК до ст. Партизанская.\n"
        "далее на автобусе [№322](https://t.$'), [№399](https://t.$') или [№444](https://t.$') до ост. Новая Купавна, далее на такси (~250 руб.) или пешком около 2,3 км.\n"
        "Внуково (~2,5 часа)\n"
        "на метро от ст. Аэропорт Внуково до ст. Партизанская, далее на автобусе [№322](https://t.$'), [№399](https://t.$') или [№444](https://t.$') до ост. Новая Купавна, далее на такси (~250 руб.) или пешком 2,3 км.\n"
        "Домодедово (~2,5 часа)\n"
        "на [Аэроэкспрессе](https://aeroexpress.ru/) (~650 руб.) до Верхних Котлов, пересесть на МЦК до ст. Измайловская, далее на автобусе (№322, 399 или №444) до ост. Новая Купавна, затем на такси (~250 руб.) или пешком 2,3 км.\n"
        "❗️ Учитывайте, что в пятницу вечером и субботу утром трассы могут быть пробки, а в воскресенье вечером - обратный маршрут❗️"
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
        "7. **Куда писать, если ничего не работает?** Если бот не пускает или что-то сломалось, напиши Данилу @maximovd или в [общий чат](https://t.me/c/2339287372/1173) ProductCamp во вкладку «Трансфер»\n"
        "\n"
        "8. **Что значит «в листе ожидания»?** Это значит, что автобус, на который ты хотел(а) записаться, уже заполнен. Однако бот всё равно добавил тебя в лист ожидания. Если кто-то отменит бронь — ты получишь уведомление и сможешь забронировать освободившееся место.\n"
        "\n"
        "9. **Можно ли записаться на несколько автобусов сразу?** Нет, по одному направлению можно иметь только одну активную запись. Сначала отмени предыдущую, если хочешь сменить автобус.\n"
        "\n"
        "10.**А если я хочу добраться до ProductCamp самостоятельно?** В боте ты сможешь найти информацию о маршрутах и способах доехать до ProductCamp. Для этого просто зайди в бота, нажми «/start», а затем в меню нажми на кнопку «Как добраться до Product Camp».\n"
        "\n"
        "11.**Почему автобусов так мало и расписание такое неудобное?** Мы понимаем, что расписание может подойти не всем. У нас ограниченный бюджет, и мы старались распределить автобусы так, чтобы охватить максимальное число кэмпчан. Надеемся, что выбранные будут удобными для большинства.\n"
        "\n"
        "Пользуйся ботом, экономь своё время и не забудь забронировать место заранее! Если будут вопросы — мы будем в общем чате ProductCamp во вкладке «Трансфер» 😊\n"
    )
    query = update.callback_query
    await query.edit_message_text(faq_text, parse_mode="Markdown")

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
    
    passengers = passengers_sheet.get_all_records()
    passenger = next((p for p in passengers if p["Telegram_username"] == username), None)

    if not passenger:
        await query.edit_message_text(
            "К сожалению, я не вижу тебя в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему, либо напиши: @havingfreckles"
        )
        return

    buses = buses_sheet.get_all_records()
    reservations = reservations_sheet.get_all_records()

    bus = next((b for b in buses if b["ID"] == bus_id), None)
    if not bus:
        await query.edit_message_text("Автобус не найден.")
        return

    # Получаем вместимость автобуса
    capacity_value = bus.get("Capacity", "")
    if isinstance(capacity_value, str):
        capacity_str = capacity_value.strip()
        try:
            capacity = int(capacity_str)
        except ValueError:
            capacity = 0
    elif isinstance(capacity_value, int):
        capacity = capacity_value
    else:
        capacity = 0

    # Проверка, заняты ли все места
    bus_reservations = [r for r in reservations if r["Bus"] == str(bus_id)]
    if len(bus_reservations) >= capacity:
        await query.edit_message_text("Все места в автобусе уже заняты.")
        return

    # Проверка, есть ли регистрация на этот автобус и направление
    direction_value = bus.get("Direction", "")
    existing_res = [
        r for r in reservations
        if r["Passenger"] == str(passenger["ID"]) and r["Bus"] == str(bus_id) and r.get("Direction", "") == direction_value
    ]
    if existing_res:
        await query.edit_message_text("Вы уже зарегистрированы на этот автобус и направление.")
        return

    # Создание новой брони
    existing_ids = [int(val) for val in reservations_sheet.col_values(1) if val.replace('.', '', 1).isdigit()]
    max_id = max(existing_ids) if existing_ids else 0
    new_id = str(max_id + 1)
    direction = bus.get("Direction", "")

    new_reservation = [
        new_id,
        str(passenger["ID"]),
        str(bus_id),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        direction,
    ]
    reservations_sheet.append_row(new_reservation)
    await query.edit_message_text(
        f"Вы успешно записаны на автобус: {bus['Number']} "
        f"({bus['DepartureDate']} {bus['DepartureTime']}) "
        f"{bus['Departure_Place']}-{bus['Destination']}"
    )

    # Если есть запись на бронирование в статусе Waiting, удалить её
    reservations = reservations_sheet.get_all_records()  # обновляем список
    waiting_res = [
        r for r in reservations
        if r["Passenger"] == str(passenger["ID"]) and r["Bus"] == str(bus_id) and r.get("Status") == "Waiting"
    ]
    for res in waiting_res:
        cell = reservations_sheet.find(str(res["ID"]))
        reservations_sheet.delete_rows(cell.row)


async def process_waiting_list(application: Application):
    """Автоматическая проверка и оповещение, если есть места и люди в очереди."""
    ws = spreadsheet.worksheet("WaitingList")
    reservations_ws = reservations_sheet
    buses = buses_sheet.get_all_records()
    reservations = reservations_ws.get_all_records()
    waiting_records = ws.get_all_records()
    # Исправляем получение Capacity: convertим в int и добавляем проверку на некорректные значения
    bus_capacity = {}
    for b in buses:
        capacity_str = b.get('Capacity', '0')
        try:
            capacity_int = int(capacity_str)
        except:
            capacity_int = 0
        bus_capacity[b['ID']] = capacity_int

    bus_reserved_counts = {}
    for b in buses:
        bus_reserved_counts[b['ID']] = sum(1 for r in reservations if r["Bus"] == b['ID'])
        # Обязательно проверяйте, что они сравнивают с правильным статусом и количеством

    for wait in waiting_records:
        if wait["Status"] != "Waiting":
            continue

        bus_id = wait["BusID"]
        passenger_id = wait["PassengerID"]
        if bus_id not in bus_capacity:
            continue

        free_places = bus_capacity[bus_id] - bus_reserved_counts.get(bus_id, 0)

        # Исправляем условие, чтобы оно учитывало правильное сравнение
        if free_places > 0:
            # Меняем статус в листе ожидания на "Confirmed"
            cells = ws.findall(str(wait["ID"]))
            for cell in cells:
                ws.update_cell(cell.row, 5, "Confirmed")
            # Уведомление пассажира

            passengers = passengers_sheet.get_all_records()
            passenger = next((p for p in passengers if p["ID"] == passenger_id), None)
            buses_list = buses_sheet.get_all_records()
            bus = next((b for b in buses_list if b["ID"] == bus_id), None)

            if passenger and bus:
                callback_data = f"select_bus_{bus['ID']}"
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Подтвердить бронь",
                            callback_data=callback_data
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await application.bot.send_message(
                    chat_id=passenger["ChatID"],
                    text=f"Место на автобус {bus['Number']} ({bus['DepartureDate']} {bus['DepartureTime']}) доступно! Хотите подтвердить бронь?",
                    reply_markup=reply_markup
                )


async def post_init(application: Application):
    asyncio.create_task(periodic(application))


async def confirm_waiting(update, context):
    user = update.message.from_user
    passenger = next((p for p in passengers_sheet.get_all_records() if p["Telegram_username"] == user.username), None)
    if not passenger:
        await update.message.reply_text("Пользователь не найден.")
        return
    ws = spreadsheet.worksheet("WaitingList")
    all_records = ws.get_all_records()
    for rec in all_records:
        if rec["PassengerID"] == str(passenger["ID"]) and rec["Status"] == "Confirmed":
            await update.message.reply_text("Вы уже подтвердили бронь.")
            return
        elif rec["PassengerID"] == str(passenger["ID"]) and rec["Status"] == "Waiting":
            ws.update_cell(ws.find(rec["ID"]).row, 5, "Confirmed")
            # Создать бронь
            reservations = reservations_sheet.get_all_records()
            buses = buses_sheet.get_all_records()
            bus_id = rec["BusID"]
            bus = next((b for b in buses if b["ID"] == bus_id), None)
            if not bus:
                await update.message.reply_text("Автобус не найден.")
                return
            current_res = [r for r in reservations if r["Bus"] == bus_id and r.get("Status") == "Booked"]
            if len(current_res) >= int(bus.get("Capacity", "0").strip()):
                await update.message.reply_text("Места в автобусе уже заняты.")
                return
            existing_ids = [int(r["ID"]) for r in reservations if r["ID"].isdigit()]
            new_id = str(max(existing_ids) + 1 if existing_ids else 1)
            reservations_sheet.append_row([
                new_id,
                str(passenger["ID"]),
                str(bus_id),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Booked",
                bus.get("Direction", "")
            ])
            await update.message.reply_text("Бронь подтверждена. Удачи!")
            return
    await update.message.reply_text("Нет ожидающих для подтверждения или уже подтверждены.")

async def add_user_to_waiting_list_callback(update, context):
    query = update.callback_query
    user = query.from_user
    passenger = next((p for p in passengers_sheet.get_all_records() if p["Telegram_username"] == user.username), None)
    if not passenger:
        await query.answer("Пользователь не найден.")
        return
    # Предложить выбрать автобус для постановки в очередь
    buses = buses_sheet.get_all_records()
    if not buses:
        await query.answer("Нет автобусов для очереди.")
        return
    keyboard = [
        [InlineKeyboardButton(f"Автобус {b['Number']} ({b['DepartureDate']} {b['DepartureTime']})", callback_data=f"set_waiting_bus_{b['ID']}")]
        for b in buses
    ]
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите автобус для постановки в очередь:", reply_markup=reply_markup)

async def handle_select_waiting_bus(update, context):
    query = update.callback_query
    if query.data.startswith("set_waiting_bus_"):
        bus_id = query.data.split("_", 3)[3]
        user = query.from_user
        passenger = next((p for p in passengers_sheet.get_all_records() if p["Telegram_username"] == user.username), None)

        if not passenger:
            await query.answer("Пользователь не найден.")
            return

        ws = spreadsheet.worksheet("WaitingList")
        existing = ws.findall(str(passenger["ID"]))

        for cell in existing:
            row = cell.row
            b_id_cell = ws.cell(row, 3)
            status_cell = ws.cell(row, 5)
            if b_id_cell.value == bus_id and status_cell.value == "Waiting":
                await query.edit_message_text("Вы уже в очереди на этот автобус.")
                await query.answer()
                return

        existing_records = ws.get_all_records()
        print(existing_records)
        new_id = max([int(r["ID"]) for r in existing_records]+[0]) + 1
        ws.append_row([
            str(new_id),
            str(passenger["ID"]),
            str(bus_id),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Waiting",
            "No"
        ])
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
            import pdb; pdb.set_trace()
            print(f"Ошибка: {e}")
        await asyncio.sleep(300)  # TODO: Вынести это в переменную окружения


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
