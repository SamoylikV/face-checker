import telebot
from telebot import types
from database import Database
from settings import DB_PARAMS, TOKEN, MAX_ITEMS_PER_PAGE


class UserState:
    def __init__(self, role='user'):
        self.sent_messages = []
        self.current_face_id_message = None
        self.face_id_to_message_id = {}
        self.current_page_message_id = None
        self.role = role


bot = telebot.TeleBot(TOKEN)
db = Database(DB_PARAMS)
user_states = {}


@bot.message_handler(commands=['start'])
def start(message):
    user_id, username, tf = extract_user_info(message)
    if not tf:
        if bot.get_me().id != user_id:
            role = db.get_user_role(user_id)
            if role is None:
                role = 'user'
                print(user_id)
                db.insert_user(user_id, username)
            if user_id not in user_states:
                user_states[user_id] = UserState(role)
            else:
                user_states[user_id].role = role
        else:
            if user_id not in user_states:
                user_states[user_id] = UserState()
    else:
        pass
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton('Посмотреть информацию', callback_data='view')
    markup.add(item1)
    if user_states[user_id].role == 'admin':
        item2 = types.InlineKeyboardButton('Админ панель', callback_data='admin_panel')
        markup.add(item2)
    sent_message = bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
    user_states[user_id].sent_messages.append(sent_message.message_id)


def handle_admin_panel(message):
    user_id = message.from_user.id
    current_state = user_states.setdefault(user_id, UserState())
    users = db.get_all_users()
    markup = types.InlineKeyboardMarkup()
    for user in users:
        user_id, username, role = user
        item = types.InlineKeyboardButton(username, callback_data=f'user_roles:{user_id}')
        markup.add(item)
    sent_message = bot.send_message(message.chat.id, "Выберите пользователя:", reply_markup=markup)
    current_state.sent_messages.append(sent_message.message_id)


def handle_user_roles(message, user_id):
    current_state = user_states.setdefault(user_id, UserState())
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton('Хостес', callback_data=f'change_role:{user_id}:user')
    item2 = types.InlineKeyboardButton('Админ', callback_data=f'change_role:{user_id}:admin')
    markup.add(item1, item2)
    sent_message = bot.send_message(message.chat.id, "Выберите роль:", reply_markup=markup)
    current_state.sent_messages.append(sent_message.message_id)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    current_state = user_states.setdefault(user_id, UserState())

    if call.data.startswith('page'):
        page = int(call.data.split(':')[1])
        if current_state.current_page_message_id:
            bot.delete_message(call.message.chat.id, current_state.current_page_message_id)
            current_state.current_page_message_id = None
        delete_previous_messages(call.message.chat.id, current_state)
        handle_view(call.message, page, current_state)
    elif call.data == 'view':
        handle_view(call.message, 1, current_state)
    elif call.data.startswith('change_name'):
        current_state.face_id = int(call.data.split(':')[1])
        if current_state.face_id not in current_state.face_id_to_message_id.keys():
            bot.send_message(call.message.chat.id, "Ошибка: неверный face_id.")
            return
        current_state.current_face_id_message = current_state.face_id_to_message_id[current_state.face_id]
        delete_previous_messages(call.message.chat.id, current_state)
        sent_message = bot.send_message(call.message.chat.id, f"Face ID: {current_state.face_id}. Введите новое имя.")
        bot.register_next_step_handler(sent_message, change_name, user_id, current_state.face_id)
        current_state.sent_messages.append(sent_message.message_id)
    elif call.data.startswith('change_image'):
        current_state.face_id = int(call.data.split(':')[1])
        if current_state.face_id not in current_state.face_id_to_message_id.keys():
            bot.send_message(call.message.chat.id, "Ошибка: неверный face_id.")
            return
        current_state.current_face_id_message = current_state.face_id_to_message_id[current_state.face_id]
        delete_previous_messages(call.message.chat.id, current_state)
        sent_message = bot.send_message(call.message.chat.id, "Отправьте новую картинку")
        bot.register_next_step_handler(sent_message, change_image, user_id, current_state.face_id)
        current_state.sent_messages.append(sent_message.message_id)
    elif call.data == 'menu':
        start(call.message)
    elif call.data == 'admin_panel':
        handle_admin_panel(call.message)
    elif call.data.startswith('user_roles'):
        user_id = int(call.data.split(':')[1])
        handle_user_roles(call.message, user_id)
    elif call.data.startswith('change_role'):
        user_id, role = call.data.split(':')[1:]
        db.change_user_role(user_id, role)
        bot.send_message(call.message.chat.id, f"Роль пользователя успешно изменена на {role}")
        start(call.message)


def handle_view(message, page, current_state):
    user_id = message.from_user.id
    face_dict = db.load_face_encodings_ordered_by_appearances()
    face_ids = list(face_dict.keys())
    start = (page - 1) * MAX_ITEMS_PER_PAGE
    end = start + MAX_ITEMS_PER_PAGE

    for face_id in face_ids[start:end]:
        encoding, name, appearances = face_dict[face_id]
        markup = types.InlineKeyboardMarkup()
        item1 = types.InlineKeyboardButton('Изменить имя', callback_data=f'change_name:{face_id}')
        item2 = types.InlineKeyboardButton('Изменить картинку', callback_data=f'change_image:{face_id}')
        markup.add(item1, item2)
        caption = f"{name if name else f'Face ID: {face_id}'}\nПоявлений: {appearances}"
        sent_message = bot.send_photo(message.chat.id, open(f"faces/face_{face_id}.jpg", 'rb'), caption=caption,
                                      reply_markup=markup)
        current_state.sent_messages.append(sent_message.message_id)
        current_state.face_id_to_message_id[face_id] = sent_message.message_id

    markup = types.InlineKeyboardMarkup(row_width=4)
    if page > 1:
        first_page_button = types.InlineKeyboardButton('<<', callback_data=f'page:1')
        prev_page_button = types.InlineKeyboardButton('<', callback_data=f'page:{page - 1}')
    if end < len(face_ids):
        next_page_button = types.InlineKeyboardButton('>', callback_data=f'page:{page + 1}')
        last_page_button = types.InlineKeyboardButton('>>',
                                                      callback_data=f'page:{(len(face_ids) - 1) // MAX_ITEMS_PER_PAGE + 1}')
    if page > 1 and end < len(face_ids):
        markup.add(first_page_button, prev_page_button, next_page_button, last_page_button)
    elif page > 1:
        markup.add(first_page_button, prev_page_button)
    elif end < len(face_ids):
        markup.add(next_page_button, last_page_button)
    menu_button = types.InlineKeyboardButton('Меню', callback_data='menu')
    markup.add(menu_button)
    sent_message = bot.send_message(message.chat.id,
                                    f"Страница {page} из {(len(face_ids) - 1) // MAX_ITEMS_PER_PAGE + 1}\nОбъектов на странице: {MAX_ITEMS_PER_PAGE}",
                                    reply_markup=markup)
    current_state.current_page_message_id = sent_message.message_id


def change_name(message, user_id, face_id):
    current_state = user_states.get(user_id, UserState())
    new_name = message.text
    db.update_face_name(face_id, new_name)
    delete_previous_messages(message.chat.id, current_state)
    bot.send_message(message.chat.id, "Имя успешно изменено")
    start(message)


def change_image(message, user_id, face_id):
    current_state = user_states.get(user_id, UserState())
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(f"faces/face_{face_id}.jpg", 'wb') as new_file:
        new_file.write(downloaded_file)
    db.update_face_image(face_id, f"faces/face_{face_id}.jpg")
    delete_previous_messages(message.chat.id, current_state)
    bot.send_message(message.chat.id, "Картинка успешно изменена")
    start(message)


def delete_previous_messages(chat_id, current_state):
    while current_state.sent_messages:
        message_id = current_state.sent_messages.pop()
        if message_id != current_state.current_face_id_message:
            bot.delete_message(chat_id, message_id)
    current_state.current_face_id_message = None


def delete_all_messages(chat_id, current_state):
    current_state.current_face_id_message = None
    while current_state.sent_messages:
        message_id = current_state.sent_messages.pop()
        if message_id != current_state.current_face_id_message:
            bot.delete_message(chat_id, message_id)


def extract_user_info(message):
    if isinstance(message, types.CallbackQuery):
        user_id = message.from_user.id
        username = message.from_user.username if hasattr(message.from_user, 'username') else None
        tf = True
    else:
        user_id = message.from_user.id
        username = message.from_user.username if hasattr(message.from_user, 'username') else None
        tf = False

    return user_id, username, tf


bot.polling(none_stop=True)
