import json
from collections import defaultdict
from typing import Optional, List

from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from catabot import utils
from catabot.commands.search import NUMBERS_EMOJI
from download_data import ALL_DATA_FILE


def _name(row: dict) -> str:
    if 'name' in row:
        if isinstance(row['name'], str):
            return row['name']
        elif 'str' in row['name']:
            return row['name']['str']
        elif 'str_sp' in row['name']:
            return row['name']['str_sp']
    if 'id' in row:
        return row['id']
    return ''


def _names(row: dict) -> List[str]:
    names = []
    if 'name' in row:
        if isinstance(row['name'], str):
            names.append(row['name'])
        elif 'str' in row['name']:
            names.append(row['name']['str'])
        elif 'str_sp' in row['name']:
            names.append(row['name']['str_sp'])
    if 'id' in row:
        names.append(row['id'])
    return names


def _match_row(row: dict, keyword: str) -> bool:
    return any(keyword in n for n in _names(row))


def _mapped_type(typ: str) -> str:
    if typ in {"AMMO", "GUN", "ARMOR", "PET_ARMOR", "TOOL", "TOOLMOD", "TOOL_ARMOR", "BOOK",
               "COMESTIBLE", "ENGINE", "WHEEL", "GUNMOD", "MAGAZINE", "BATTERY", "GENERIC", "BIONIC_ITEM"}:
        return "item"
    elif typ == "city_building":
        return "overmap_special"
    else:
        return typ.lower()


def _all_data() -> list:
    return json.load(open(ALL_DATA_FILE, 'r'))['data']


def _search_results(keyword: str) -> dict:
    results_by_type = defaultdict(list)
    for row in _all_data():
        if 'type' in row and _match_row(row, keyword):
            results_by_type[_mapped_type(row['type'])].append(row)
    return results_by_type


def _result_by_id(typ: str, row_id: str) -> Optional[dict]:
    result = None
    for row in _all_data():
        if 'id' in row and row['id'] == row_id and 'type' in row and _mapped_type(row['type']) == typ:
            result = row
            break
    # TODO: implement recursive copy-from
    return result


def _page_view(results: list, keyword: str, action: str, page: int = 1) -> (str, InlineKeyboardMarkup):
    maxpage = int(len(results) / 10)
    results = results[(page - 1) * 10: page * 10:]

    text = f"Search results for {action} {keyword}:\n\n"
    btns = []

    for i, row in enumerate(results):
        btns.append(InlineKeyboardButton(
            text=NUMBERS_EMOJI[i + 1],
            callback_data=f"cdda:{action}:{row['id']}"
        ))
        text += f"{NUMBERS_EMOJI[i + 1]} {utils.escape(_name(row))} (<code>{row['id']}</code>)\n"
    text += f"\n(page {page} of {maxpage+1})"
    markup = InlineKeyboardMarkup(row_width=5)
    markup.add(*btns)
    btm_row = []
    if page > 1:
        btm_row.append(InlineKeyboardButton(text="⬅️ Prev.", callback_data=f"cdda_page{page - 1}_{action}:{keyword}"))
    btm_row.append(InlineKeyboardButton(text="❌ Cancel", callback_data="cdda_cancel"))
    if page <= maxpage:
        btm_row.append(InlineKeyboardButton(text="➡ Next️️", callback_data=f"cdda_page{page + 1}_{action}:{keyword}"))
    markup.add(*btm_row)
    return text, markup


def _action_view(action: str, row_id: str) -> (str, InlineKeyboardMarkup):
    typ = 'item'
    if action == 'monster':
        typ = 'monster'

    if action == 'view':
        data = _result_by_id(typ, row_id)
        return f"<code>{str(data)}</code>", InlineKeyboardMarkup()


def search2(bot: TeleBot, message: Message):
    bot.send_chat_action(message.chat.id, 'typing')
    keyword = utils.get_keyword(message)
    command = utils.get_command(message).lower()
    if not keyword:
        bot.reply_to(message, f"Usage example:\n<code>{command} glazed tenderloins</code>", parse_mode='html')
        return

    action = 'view'
    typ = 'item'
    # TODO: use match
    if command in {'/c', '/craft'}:
        action = 'craft'
    elif command in {'/disassemble', '/d', '/disasm'}:
        action = 'disassemble'
    elif command in {'/m', '/mob', '/monster'}:
        action = 'monster'
        typ = 'monster'

    tmp_message = bot.reply_to(message, "Loading search results...")

    results = _search_results(keyword)
    if len(results[typ]) == 0:
        bot.send_sticker(message.chat.id, 'CAADAgADxgADOtDfAeLvpRcG6I1bFgQ', message.message_id)
    elif len(results[typ]) == 1:
        text, markup = _action_view(action, results[typ][0]['id'])
        bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')
    else:
        text, markup = _page_view(results[typ], keyword, action)
        bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')

    utils.delete_message(bot, tmp_message)


def btn_pressed(bot: TeleBot, message: Message, data: str):
    bot.send_chat_action(message.chat.id, 'typing')
    if data.startswith('cdda:'):
        utils.delete_message(bot, message)
        action, row_id = data[5::].split(':')
        text, markup = _action_view(action, row_id)
        bot.reply_to(message.reply_to_message, text, reply_markup=markup, parse_mode='HTML')
    elif data == 'cdda_cancel':
        bot.edit_message_text(message.text.split('\n')[0] + '\n(canceled)', message.chat.id, message.message_id)
    elif data.startswith('cdda_page'):
        page, actkey = data[9::].split('_')
        action, keyword = actkey.split(':')
        page = int(page)
        if page < 1:
            return
        results = _search_results(keyword)
        typ = 'item'
        if action == 'monster':
            typ = 'monster'
        text, markup = _page_view(results[typ], keyword, action, page=page)
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup, parse_mode='HTML')
