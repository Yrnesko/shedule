import telebot
from telebot import types
import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from datetime import datetime, timedelta


DAYS_MAPPING = {
    'Monday': 'Понедельник',
    'Tuesday': 'Вторник',
    'Wednesday': 'Среда',
    'Thursday': 'Четверг',
    'Friday': 'Пятница',
    'Saturday': 'Суббота',
    'Sunday': 'Воскресенье'
}

tz = pytz.timezone('Etc/GMT+5')  # Пример для Московского времени
scheduler = BackgroundScheduler(timezone=tz)
TOKEN = '6593032799:AAFRrLjBjVRlGIzj3NLVinaYNsovw0eO-WA'
bot = telebot.TeleBot(TOKEN)

# Подключение к базе данных MySQL
db = mysql.connector.connect(
    host="sql11.freemysqlhosting.net",
    user="sql11653703",
    password="7r5jhb3Knu",
    database="sql11653703",
    charset = 'utf8mb4'
)
cursor = db.cursor()

def format_time(td):
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours:02}:{minutes:02}"

def main_menu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_button = types.KeyboardButton('Меню')
    keyboard.add(menu_button)
    return keyboard

@bot.message_handler(commands=['start'])
def handle_start(message):
    welcome_text = "Привет! Это бот расписание, выберете что то из меню : "
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda message: message.text == "Меню")
def handle_menu(message):
    send_main_menu(message)


@bot.message_handler(func=lambda message: message.text == "Меню")
def send_main_menu(message):
    markup = types.InlineKeyboardMarkup()

    # Добавляем инлайн-кнопки
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Выбрать день недели", callback_data="days"))
    markup.add(types.InlineKeyboardButton("Личный кабинет", callback_data="personal_area"))
    markup.add(types.InlineKeyboardButton("Расписание на сегодня", callback_data="today_schedule"))
    markup.add(types.InlineKeyboardButton("Расписание на завтра", callback_data="tomorrow_schedule"))
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "days")
def send_days_of_week(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    markup = types.InlineKeyboardMarkup()
    cursor.execute("SELECT DISTINCT day_of_week FROM schedule")
    days = cursor.fetchall()
    for day in days:
        day_btn = types.InlineKeyboardButton(text=day[0], callback_data=day[0])
        markup.add(day_btn)
    bot.send_message(call.message.chat.id, "Выберите день недели:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "personal_area")
def personal_area(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    # Проверяем, есть ли пользователь в базе данных
    cursor.execute("SELECT user_id, is_subscribed FROM users WHERE user_id = %s", (call.message.from_user.id,))
    user = cursor.fetchone()

    # Если пользователя нет в базе, добавляем его
    if not user:
        cursor.execute("INSERT INTO users (user_id, chat_id, is_subscribed) VALUES (%s, %s, FALSE)",
                       (call.message.from_user.id, call.message.chat.id))
        db.commit()
        is_subscribed = False
    else:
        is_subscribed = user[1]

    # Отправьте пользователю меню с опциями
        # Составляем текст сообщения для личного кабинета
        personal_info = "Личный кабинет:\n"

        # Добавляем информацию о статусе подписки
        if is_subscribed:
            personal_info += "Вы подписаны на рассылку. Чтобы отписаться, нажмите кнопку"
        else:
            personal_info += "Вы не подписаны на рассылку. Чтобы подписаться, нажмите кнопку"
    markup = types.InlineKeyboardMarkup()
    if is_subscribed:
        markup.add(types.InlineKeyboardButton("Отписаться от рассылки", callback_data="unsubscribe"))
    else:
        markup.add(types.InlineKeyboardButton("Подписаться на рассылку", callback_data="subscribe"))


    markup.add(types.InlineKeyboardButton("Вернуться в меню", callback_data="return_to_menu"))
    bot.send_message(call.message.chat.id, personal_info, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "return_to_menu")
def return_to_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)  # Удалить сообщение личного кабинета
    send_main_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == "subscribe")
def subscribe_user(call):
    # Обновляем статус подписки пользователя в базе данных
    cursor.execute("UPDATE users SET is_subscribed = TRUE WHERE user_id = %s", (call.message.from_user.id,))
    db.commit()

    bot.answer_callback_query(call.id, "Вы успешно подписались на рассылку!")

    # Здесь обновляем сообщение личного кабинета с новой кнопкой
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Отписаться от рассылки", callback_data="unsubscribe"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Личный кабинет:\nВы подписаны на рассылку. Чтобы отписаться, нажмите кнопку",
                          reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "unsubscribe")
def unsubscribe_user(call):
    # Обновляем статус подписки пользователя в базе данных
    cursor.execute("UPDATE users SET is_subscribed = FALSE WHERE user_id = %s", (call.message.from_user.id,))
    db.commit()

    bot.answer_callback_query(call.id, "Вы успешно отписались от рассылки!")

    # Обновляем сообщение личного кабинета с новой кнопкой
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Подписаться на рассылку", callback_data="subscribe"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Личный кабинет:\nВы не подписаны на рассылку. Чтобы подписаться, нажмите кнопку", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "today_schedule")
def show_today_schedule(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    today_english = datetime.now().strftime('%A')
    today_russian = DAYS_MAPPING[today_english]
    cursor.execute("SELECT lesson_number, lesson_start_time, lesson_end_time, lesson_name, room_number FROM schedule WHERE day_of_week=%s ORDER BY lesson_number", (today_russian,))
    lessons = cursor.fetchall()
    if not lessons:
        bot.send_message(call.message.chat.id, "Сегодня уроков нет!")
        return

    response = "Расписание на сегодня:\n"
    for lesson in lessons:
        response += f"{lesson[0]}. {lesson[3]} (Время: {format_time(lesson[1])} - {format_time(lesson[2])}, Кабинет: {lesson[4]})\n"

    bot.send_message(call.message.chat.id, response)
    bot.send_message(call.message.chat.id, " ", reply_markup=main_menu_keyboard())


@bot.callback_query_handler(func=lambda call: call.data == "tomorrow_schedule")
def show_tomorrow_schedule(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    tomorrow_english = (datetime.now() + timedelta(days=1)).strftime('%A')
    tomorrow_russian = DAYS_MAPPING[tomorrow_english]
    cursor.execute("SELECT lesson_number, lesson_start_time, lesson_end_time, lesson_name, room_number FROM schedule WHERE day_of_week=%s ORDER BY lesson_number", (tomorrow_russian,))
    lessons = cursor.fetchall()
    if not lessons:
        bot.send_message(call.message.chat.id, "Завтра уроков нет ❤️‍🔥")
        return

    response = "Расписание на завтра:\n"
    for lesson in lessons:
        response += f"{lesson[0]}. {lesson[3]}  || Время: {format_time(lesson[1])} - {format_time(lesson[2])} ||  Кабинет: {lesson[4]} \n"

    bot.send_message(call.message.chat.id, response)
    bot.send_message(call.message.chat.id, " ", reply_markup=main_menu_keyboard())


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    day_selected = call.data
    cursor.execute(
        "SELECT lesson_number, lesson_start_time, lesson_end_time, lesson_name, room_number FROM schedule WHERE day_of_week=%s ORDER BY lesson_number",
        (day_selected,)
    )
    lessons = cursor.fetchall()
    if lessons:
        response = f"Расписание на {day_selected}:\n\n"
        for lesson in lessons:
            response += f"{lesson[0]}. {lesson[3]} || Время: {format_time(lesson[1])} - {format_time(lesson[2])} || Кабинет: {lesson[4]}\n"

        # Удаление изображения с кнопками
        bot.delete_message(call.message.chat.id, call.message.message_id)

        # Отправка нового сообщения с расписанием
        bot.send_message(call.message.chat.id, text=response)
    else:
        bot.send_message(call.message.chat.id,
                         "Извините, я не распознал этот день. Нажмите на 'Меню' для повторного выбора.")
    bot.send_message(call.message.chat.id, " ", reply_markup=main_menu_keyboard())



def send_broadcast():
    # Получаем день недели для завтрашнего дня
    tomorrow = datetime.now() + timedelta(days=1)
    day_of_week = tomorrow.strftime('%A').lower()  # переведем в нижний регистр, чтобы соответствовать записям в БД

    # Запрашиваем расписание для этого дня
    cursor.execute(
        "SELECT lesson_number, lesson_start_time, lesson_end_time, lesson_name, room_number FROM schedule WHERE day_of_week=%s ORDER BY lesson_number",
        (day_of_week,))
    lessons = cursor.fetchall()

    response = f"Расписание на {day_of_week.capitalize()}:\n"
    for lesson in lessons:
        response += f"{lesson[0]}. {lesson[3]} || Время: {lesson[1].strftime('%H:%M')} - {lesson[2].strftime('%H:%M')} ||  Кабинет: {lesson[4]}\n"

    # Теперь отправьте это расписание всем подписанным пользователям:
    cursor.execute("SELECT chat_id FROM users WHERE is_subscribed = TRUE")
    subscribers = cursor.fetchall()

    for subscriber in subscribers:
        bot.send_message(subscriber[0], response)


scheduler = BackgroundScheduler()
# Отправляйте расписание каждый день в 18:00. Вы можете изменить это время на любое другое.
scheduler.add_job(send_broadcast, 'cron', hour=18, minute=0)
scheduler.start()

@bot.message_handler(content_types=['text'])
def handle_text(message):
    bot.send_message(message.chat.id, " бот не расспознает это сообщение ❤️ ", reply_markup=main_menu_keyboard())




bot.polling(none_stop=True)