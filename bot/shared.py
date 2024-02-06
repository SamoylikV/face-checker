import telebot
from database import Database
from settings import DB_PARAMS, TOKEN, MAX_ITEMS_PER_PAGE

bot = telebot.TeleBot(TOKEN)
db = Database(DB_PARAMS)
user_states = {}