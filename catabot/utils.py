from telebot import TeleBot
from telebot.apihelper import ApiException
from telebot.types import Message


def get_command(message: Message):
    return message.text.split(' ')[0].split('@')[0].lower()


def get_atmention(message: Message):
    if '@' in message.text:
        command = message.text.split(' ')[0].split('@')
        return command[1] if len(command) > 1 else None
    return None


def get_keyword(message: Message, with_reply=True) -> str:
    keyword = message.text[len(message.text.split(' ')[0]) + 1::].replace(',', '').strip()
    if with_reply and not keyword and message.reply_to_message:
        rm = message.reply_to_message
        keyword = rm.caption if rm.caption else rm.text
    return keyword


def chunks(s, n):
    """Produce `n`-character chunks from `s`."""
    for start in range(0, len(s), n):
        yield s[start:start + n]


def escape(html):
    """Returns the given HTML with ampersands, quotes and carets encoded."""
    return html\
        .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')


def delete_message(bot: TeleBot, message: Message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except ApiException:
        pass
