import os
import json

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
        [
            InlineKeyboardButton("Записаться на автобус", callback_data="book_bus"),
            InlineKeyboardButton("Посмотреть свои запись", callback_data="view_booking"),
        ],
        [
            InlineKeyboardButton("Отменить запись", callback_data="cancel_booking"),
            InlineKeyboardButton("Как добраться?", callback_data="how_to_get_there"),
        ],
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
    elif query.data == "back_to_menu":
        await start(update, context)

async def step_select_direction(query, context):
    buses = buses_sheet.get_all_records()
    directions = sorted(set(b['Direction'] for b in buses if 'Direction' in b and b['Direction'].strip()))
    keyboard = [
        [InlineKeyboardButton(direction, callback_data=f"select_direction_{direction}")]
        for direction in directions
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
            "К сожалению, я не вижу вас в списках участиников кэмпа, "
            "для решение данного вопроса, обратись к своему старшему."
        )
        return

    # Проверка, есть ли уже регистрация у пользователя на данное направление
    existing_res = [
        r for r in reservations
        if r["Passenger"] == passenger["ID"]
        and r.get("Direction", "") == direction
    ]
    if existing_res:
        await query.edit_message_text("Вы уже зарегистрированы на это направление.")
        return

    # Фильтрация автобусов по выбранному направлению
    buses_for_direction = [b for b in buses if b.get("Direction") == direction]

    available_buses = []
    for bus in buses_for_direction:
        bus_reservations = [r for r in reservations if r["Bus"] == bus["ID"]]
        if len(bus_reservations) < int(bus["Capacity"]):
            available_buses.append(bus)

    if not available_buses:
        await query.edit_message_text("Нет доступных автобусов для выбранного направления.")
        return

    keyboard = [
        [
            InlineKeyboardButton(
                f"Автобус {bus['Number']} ({bus['DepartureDate']} {bus['DepartureTime']})",
                callback_data=f"select_bus_{bus['ID']}"
            )
        ] for bus in available_buses
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите автобус:", reply_markup=reply_markup)

async def confirm_booking(update, context, bus_id):
    """Подтверждение записи на автобус"""
    query = update.callback_query
    username = query.from_user.username
    passengers = passengers_sheet.get_all_records()
    passenger = next((p for p in passengers if p["Telegram_username"] == username), None)
    if not passenger:
        await query.edit_message_text(
            "К сожалению, вы не входите в списки участников трансфера, "
            "для проверки ситуации свяжитесь с администратором (@mdensov)."
        )
        return

    buses = buses_sheet.get_all_records()
    reservations = reservations_sheet.get_all_records()

    bus = next((b for b in buses if b["ID"] == bus_id), None)

    if not bus:
        await query.edit_message_text("Автобус не найден.")
        return

    # Проверка, что пользователь не зарегистрирован на этот автобус
    user_res = [
        r for r in reservations
        if r["Passenger"] == passenger["ID"] and r["Bus"] == bus_id
    ]
    if user_res:
        await query.edit_message_text("Вы уже записаны на этот автобус.")
        return

    # Проверка свободных мест
    bus_reservations = [r for r in reservations if r["Bus"] == bus_id]
    if len(bus_reservations) >= int(bus["Capacity"]):
        await query.edit_message_text("К сожалению, места на автобус закончились.")
        return

    # Расчет нового ID для брони
    existing_ids = [float(val) for val in reservations_sheet.col_values(1) if val.replace('.', '', 1).isdigit()]
    max_id = max(existing_ids) if existing_ids else 0

    # Вытаскиваем направление автобуса
    direction = bus.get("Direction", "")

    # Создаем новую запись
    new_reservation = [
        str(max_id + 1),
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

async def view_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    username = query.from_user.username
    passengers = passengers_sheet.get_all_records()
    passenger = next((p for p in passengers if p["Telegram_username"] == username), None)
    if not passenger:
        await query.edit_message_text(
            "К сожалению, вы не входите в списки участников трансфера, "
            "для проверки ситуации свяжитесь с администратором (@mdensov)."
        )
        return

    reservations = reservations_sheet.get_all_records()
    buses = buses_sheet.get_all_records()

    user_res = [r for r in reservations if r["Passenger"] == passenger["ID"]]
    if not user_res:
        await query.edit_message_text("Вы не записаны ни на один автобус")
        return

    message = "Ваши записи:\n\n"
    for res in user_res:
        bus = next((b for b in buses if b["ID"] == res["Bus"]), None)
        if bus:
            message += (
                f"Автобус: {bus['Number']} ({bus['DepartureDate']} {bus['DepartureTime']}) "
                f"({bus['Departure_Place']}-{bus['Destination']})-{bus['Direction']}\n"
            )

    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)

async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    username = query.from_user.username
    passengers = passengers_sheet.get_all_records()
    passenger = next((p for p in passengers if p["Telegram_username"] == username), None)
    if not passenger:
        await query.edit_message_text(
            "К сожалению, вы не входите в списки участников трансфера, "
            "для проверки ситуации свяжитесь с администратором (@mdensov)."
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
        "🚶‍♂️ Своим ходом из Москвы, время в пути около 1-1,5 часа:\n"
        "🛤️ На электричке\n"
        "на электричке от Курского или Белорусского вокзала до станции Купавна (цена билета ~150 руб), \n"
        "затем 20-30 мин на такси до Ареал (стоимость ~600-700 руб)\n\n"
        "🗓️ Расписание электричек: [туда](https://ticket.rzd.ru/searchresults/v/1/5cd18d837081a600437b02f2/5a323c29340c7441a0a556bb/) и [обратно](https://ticket.rzd.ru/searchresults/v/1/5cd18d837081a600437b02f2/5a323c29340c7441a0a556bb/) (пожалуйста, внимательно проверяйте станцию отправления и прибытия в Москве, расписание указано для двух вокзалов).\n\n"
        "🚌 На автобусе\n"
        "от ст. м. Партизанская (1 выход из метро) - автобус №322 и №444;\n"
        "от м. Новогиреево (6 выход из метро) - маршрутное такси №587к и №886к; \n\n"
        "🚏 до ост. Новая Купавна, перейти Горьковское шоссе,\n"
        "далее на такси 5-7 мин (стоимость ~ 250 руб) или пешком около 2,3 км по указателям (для спортивных участников).\n\n"
        "📝 Расписание автобусов: [туда](https://rasp.yandex.ru/search/bus/?fromId=c213&fromName=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0&toId=c33762&toName=%D0%9D%D0%BE%D0%B2%D0%B0%D1%8F+%D0%9A%D1%83%D0%BF%D0%B0%D0%B2%D0%BD%D0%B0&when=23+%D0%BC%D0%B0%D1%8F) / [обратно](https://rasp.yandex.ru/search/bus/?fromId=c33762&fromName=%D0%9D%D0%BE%D0%B2%D0%B0%D1%8F+%D0%9A%D1%83%D0%BF%D0%B0%D0%B2%D0%BD%D0%B0&toId=c213&toName=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0&when=25+%D0%BC%D0%B0%D1%8F) (пожалуйста, внимательно проверяйте даты отправления и прибытия, данные ссылки актуальны для пятницы 23 мая и воскресенья 25 мая соответственно).\n\n"
        "🚗 На машине\n"
        "время в пути ~ 1-1,5 часа: **бесплатная парковка** (примерно на 200 мест), находится перед въездом в отель.\n"
        "Парковка расположена со стороны **Горьковского шоссе**, поэтому рекомендуем выбирать маршрут через Горьковское шоссе, даже если навигатор прокладывает маршрут через Щелковское шоссе.\n"
        "📍 **Как доехать:**\n"
        "Отель находится по адресу: **Сиреневая ул., 21, микрорайон Родинки, д. Новая Купавна**.\n"
        "Метки на картах: [Гугл-карта](https://goo.gl/maps/7doSnWnGg4mb8QqG6), [Яндекс-карта](https://yandex.ru/maps/-/CCUWeOGxwD)\n"
        "Если в машине есть свободные места, обязательно укажи свой телеграм ниже в таблице, попутчики смогут с тобой связаться, начните знакомство еще до кэмпа!😉\n\n"
        "🛬 **Из аэропортов Москвы**\n\n"
        "❗️ Учитывайте, пожалуйста, что в пятницу вечером и субботу утром на данном направлении могут быть пробки из Москвы, а в воскресенье вечером - в Москву, что может вызвать задержки в пути❗️"
    )
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")],
        [InlineKeyboardButton("Маршрут до отеля", callback_data="route_to_hotel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(info_message, reply_markup=reply_markup, parse_mode="Markdown")

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
    """Подтверждение записи на автобус"""
    query = update.callback_query
    username = query.from_user.username
    
    passengers = passengers_sheet.get_all_records()
    passenger = next((p for p in passengers if p["Telegram_username"] == username), None)
    if not passenger:
        await query.edit_message_text(
            "К сожалению, вы не входите в списки участников трансфера, "
            "для проверки ситуации свяжитесь с администратором (@mdensov)."
        )
        return

    buses = buses_sheet.get_all_records()
    reservations = reservations_sheet.get_all_records()

    bus = next((b for b in buses if b["ID"] == bus_id), None)
    if not bus:
        await query.edit_message_text("Автобус не найден.")
        return

    # Проверяем, есть ли регистрация на этот bus и направление
    # Такое условие – если пользователь уже зарегистрирован на этот же автобус или на то же направление
    direction_value = bus.get("Direction", "")
    existing_res = [
        r for r in reservations
        if r["Passenger"] == str(passenger["ID"]) and r["Bus"] == str(bus_id) and r.get("Direction", "") == direction_value
    ]
    if existing_res:
        await query.edit_message_text("Вы уже зарегистрированы на этот автобус и направление.")
        return

    # Проверяем свободные места
    bus_reservations = [r for r in reservations if r["Bus"] == str(bus_id)]
    if len(bus_reservations) >= int(bus["Capacity"]):
        await query.edit_message_text("К сожалению, места на автобус закончились.")
        return

    # Находим максимальный ID
    existing_ids = [int(val) for val in reservations_sheet.col_values(1) if val.replace('.', '', 1).isdigit()]
    max_id = max(existing_ids) if existing_ids else 0

    # Сохраняем направление
    direction = bus.get("Direction", "")
    new_id = str(max_id + 1)

    # Создаем новую бронь
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

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == "__main__":
    main()
# В таблице `Reservations` необходимо добавить колонку `Direction`, чтобы хранить выбранное направление.

# В итоге, чтобы внедрить:
# 1. Добавьте колонку `Direction` в лист `Buses` (если еще не сделано).
# 2. В функции отображения автобусов по выбранному направлению — несколько новых вызовов и проверок.
# 3. Перед бронированием проверяйте, зарегистрирован ли пользователь уже на это направление (по колонке `Direction`).

# Основная идея: при выборе направления сохраняем его в данных брони, и перед бронированием проверяем, есть ли уже регистрация по тому же направлению.

# После этого у вас будет функционал выбора направления и проверка на дублироаение.
