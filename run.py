import sys
import os
import multiprocessing

sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from bot.bot import start_bot
from main import start_main

if __name__ == "__main__":
    bot_process = multiprocessing.Process(target=start_bot)
    main_process = multiprocessing.Process(target=start_main)

    bot_process.start()
    main_process.start()

    bot_process.join()
    main_process.join()