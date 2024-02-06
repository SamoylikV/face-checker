from shared import bot, db, user_states
from handlers import start, handle_admin_panel, handle_user_roles, handle_view, change_name, change_image

def start_bot():
    bot.polling(none_stop=True)