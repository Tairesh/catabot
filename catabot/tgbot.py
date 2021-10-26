import threading

from telebot import TeleBot
from telebot.apihelper import ApiException
from telebot.types import User

from catabot import constants
from catabot.commands.search import search, quality  # , btn_pressed
from catabot.commands.release import get_release
from catabot.commands.search2 import search2, btn_pressed


def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


class TelegramBot:

    def __init__(self, token, clean=False, debug=False):
        self.token: str = token
        self.clean: bool = clean
        self.debug: bool = debug

        self.bot: TeleBot = TeleBot(token, skip_pending=clean)
        self.me: User = self.bot.get_me()

        @self.bot.message_handler(['craft', 'c', 'item', 'i', 'disassemble', 'disasm', 'd', 'monster', 'mob', 'm'])
        def _search(message):
            search(self.bot, message)

        @self.bot.message_handler(['search'])
        def _search2(message):
            search2(self.bot, message)

        @self.bot.message_handler(['quality', 'q'])
        def _quality(message):
            quality(self.bot, message)

        @self.bot.callback_query_handler(func=lambda call: call.data)
        def _btn_pressed(call):
            if call.message and call.message.reply_to_message:
                if call.message.reply_to_message.from_user.id != call.from_user.id:
                    return
            btn_pressed(self.bot, call.message, call.data)

        @self.bot.message_handler(['release', 'get_release'])
        def _get_release(message):
            get_release(self.bot, message)

        @self.bot.message_handler(func=lambda m: m.from_user and m.from_user.id == 777000)
        def _unpin(message):
            try:
                self.bot.unpin_chat_message(message.chat.id, message.message_id)
            except ApiException:
                pass

    # Start the bot
    def bot_start_polling(self):
        for admin in constants.ADMINS:
            self.bot.send_message(admin, 'I was restarted')

    # Go in idle mode
    def bot_idle(self):
        if self.debug:
            self.bot.polling(True)
        else:
            self.bot.infinity_polling()
