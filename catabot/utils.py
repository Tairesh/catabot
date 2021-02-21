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
