import json
import logging
import math
from collections import defaultdict
from typing import List, Union

from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from catabot import utils
from catabot.commands.search import NUMBERS_EMOJI
from download_data import ALL_DATA_FILE, DATA_VERSION_FILE


raw_data = {
    'version': None,
    'item': {},
    'uncraft': {},
    'recipe': {},
}


def _update_data():
    version = open(DATA_VERSION_FILE, 'r').read()
    if raw_data['version'] != version:
        # typs = set()
        for row in json.load(open(ALL_DATA_FILE, 'r'))['data']:
            typ = _mapped_type(row['type'])
            if typ == 'item':
                if 'id' in row:
                    row_id = row['id']
                elif 'abstract' in row:
                    row_id = row['abstract']
                else:
                    logging.warning('no id and no abstract: {}', row)
                    continue
                raw_data['item'][row_id] = row
            elif typ == 'recipe':
                if 'result' in row and 'category' in row and row['category'] != 'CC_BUILDING':
                    raw_data['recipe'][row['result']] = row
            elif typ == 'uncraft':
                if 'result' in row:
                    raw_data['uncraft'][row['result']] = row
            # else:
            #     typs.add(typ)
        # print(typs)
        for row in raw_data['item'].values():
            if 'copy-from' in row:
                _add_copy_from(row)
        for row in raw_data['recipe'].values():
            if 'reversible' in row and row['reversible']:
                raw_data['uncraft'][row['result']] = row
        raw_data['version'] = version


def _add_copy_from(row: dict):
    if 'copy-from' in row:
        fr = raw_data['item'][row['copy-from']]
        row.pop('copy-from')
        for key in fr:
            if key not in row and key != 'abstract':
                row[key] = fr[key]
        _add_copy_from(row)


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


def _search_results(keyword: str) -> dict:
    results_by_type = defaultdict(list)
    for typ in {'item', }:
        for row in raw_data[typ].values():
            if 'id' in row and _match_row(row, keyword):
                results_by_type[typ].append(row)
    return results_by_type


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


def _parse_volume(vol: Union[str, int]) -> int:
    if not vol:
        return 0
    if isinstance(vol, int):
        return vol * 250
    try:
        if vol.lower().endswith("ml"):
            return int(vol[:-2].strip())
        if vol.lower().endswith("l"):
            return int(vol[:-1].strip()) * 1000
    except ValueError:
        logging.warning("invalid volume: {}", vol)
    return 0


def _parse_mass(weight: Union[str, int]) -> float:
    if not weight:
        return 0
    if isinstance(weight, int):
        return weight
    try:
        if weight.lower().endswith("mg"):
            return int(weight[:-2].strip()) / 1000
        if weight.lower().endswith("kg"):
            return int(weight[:-2].strip()) * 1000
        if weight.lower().endswith("g"):
            return int(weight[:-1].strip())
    except ValueError:
        logging.warning("invalid weight: {}", weight)
    return 0


def _mpa(row: dict) -> int:
    return math.floor(65 + math.floor(_parse_volume(row['volume']) / 62.5) + math.floor(_parse_mass(row['weight']) / 60.0))


def _item_length(row: dict) -> str:
    if 'longest_side' in row:
        return row['longest_side']
    return f"{round(_parse_volume(row['volume']) ** (1.0/3.0))} cm"


def _compute_to_hit(to_hit: Union[int, dict]) -> int:
    if isinstance(to_hit, int):
        return to_hit
    return -2 + {'bad': -1, 'none': 0, 'solid': 1, 'weapon': 2}[to_hit['grip']] + \
        {'hand': 0, 'short': 1, 'long': 2}[to_hit['length']] + \
        {'point': -2, 'line': -1, 'any': 0, 'every': 1}[to_hit['surface']] + \
        {'clumsy': -2, 'uneven': -1, 'neutral': 0, 'good': 1}[to_hit['balance']]


def _view_item(row_id: str, raw=False) -> (str, InlineKeyboardMarkup):
    # this is basically a poor copy of https://github.com/nornagon/cdda-guide/blob/main/src/types/Item.svelte
    data = raw_data['item'][row_id]
    if raw:
        text = f"<code>{str(data)}</code>"
    else:
        text = f"<a href=\"https://nornagon.github.io/cdda-guide/#/item/{row_id}\">{utils.escape(_name(data))}</a>\n" \
               f"<i>{data['description']}</i>\n\n" \
               f"Materials: {', '.join(data['material']) if 'material' in data else 'None'}\n" \
               f"Volume: {data['volume']}\n" \
               f"Weight: {data['weight']}\n" \
               f"Length: {_item_length(data)}\n" \
               f"Flags: {', '.join(data['flags']) if 'flags' in data and len(data['flags']) > 0 else 'None'}\n"
        # TODO: flags' descriptions
        # TODO: ammo
        # TODO: magazine_compatible
        # TODO: faults
        if 'qualities' in data:
            # TODO: qualities' names
            text += f"Qualities: {str(data['qualities'])}\n"
        # TODO: vehicle parts
        # TODO: ascii_picture

        # TODO: if data['type'] == 'BOOK'
        # TODO: if data['type'] in {'ARMOR', 'TOOL_ARMOR'}
        # TODO: if data['type'] in {'TOOL', 'TOOL_ARMOR'}
        # TODO: if data['type'] == 'ENGINE'
        # TODO: if data['type'] == 'COMESTIBLE'
        # TODO: if data['type'] == 'WHEEL'
        # TODO: if 'seed_data' in data

        if 'bashing' in data or 'cutting' in data or data['type'] in {"GUN", "AMMO"}:
            text += f"Bash: {data['bashing'] if 'bashing' in data else 0} | "
            if 'SPEAR' in data['flags'] or 'STAB' in data['flags']:
                text += "Pierce: "
            else:
                text += "Cut: "
            text += str(data['cutting'] if 'cutting' in data else 0)
            text += f" | To Hit: {_compute_to_hit(data['to_hit']) if 'to_hit' in data else 0}"
            text += f" | Moves Per Attack: {_mpa(data)}"
            if 'techniques' in data:
                text += f" | Techniques: {str(data['techniques'])}"

        # TODO: pockets

    markup = InlineKeyboardMarkup()
    row = [
        InlineKeyboardButton("👀 Description", callback_data=f"cdda:view:{row_id}")
        if raw else
        InlineKeyboardButton('🔣 Raw JSON', callback_data=f"cdda:item_raw:{row_id}")
    ]
    if row_id in raw_data['recipe']:
        row.append(InlineKeyboardButton("🛠 Craft", callback_data=f"cdda:craft:{row_id}"))
    if row_id in raw_data['uncraft']:
        row.append(InlineKeyboardButton("🛠 Deconstruct", callback_data=f"cdda:uncraft:{row_id}"))
    markup.add(*row)
    return text, markup


def _action_view(action: str, row_id: str) -> (str, InlineKeyboardMarkup):
    if action == 'view':
        return _view_item(row_id)
    elif action == 'item_raw':
        return _view_item(row_id, True)
    # TODO: craft and uncraft views
    # TODO: monster view

    typ = 'item'
    if action == 'monster':
        typ = 'monster'
    elif action == 'craft':
        typ = 'recipe'
    elif action == 'uncraft':
        typ = 'uncraft'

    markup = InlineKeyboardMarkup()
    if action == 'view':
        if row_id in raw_data['recipe']:
            markup.add(InlineKeyboardButton("🛠 Craft", callback_data=f"cdda:craft:{row_id}"))
        if row_id in raw_data['uncraft']:
            markup.add(InlineKeyboardButton("🛠 Deconstruct", callback_data=f"cdda:uncraft:{row_id}"))
    elif action == 'craft':
        markup.add(InlineKeyboardButton("👀 Description", callback_data=f"cdda:view:{row_id}"))
        if row_id in raw_data['uncraft']:
            markup.add(InlineKeyboardButton("🛠 Deconstruct", callback_data=f"cdda:uncraft:{row_id}"))
    elif action == 'uncraft':
        markup.add(InlineKeyboardButton("👀 Description", callback_data=f"cdda:view:{row_id}"))
        if row_id in raw_data['recipe']:
            markup.add(InlineKeyboardButton("🛠 Craft", callback_data=f"cdda:craft:{row_id}"))

    data = raw_data[typ][row_id]
    return f"<code>{str(data)}</code>", markup


def search2(bot: TeleBot, message: Message):
    bot.send_chat_action(message.chat.id, 'typing')
    _update_data()
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
        action = 'uncraft'
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
    if data.startswith('cdda:'):
        bot.send_chat_action(message.chat.id, 'typing')
        _update_data()
        utils.delete_message(bot, message)
        action, row_id = data[5::].split(':')
        text, markup = _action_view(action, row_id)
        bot.reply_to(message.reply_to_message, text, reply_markup=markup, parse_mode='HTML')
    elif data == 'cdda_cancel':
        bot.edit_message_text(message.text.split('\n')[0] + '\n(canceled)', message.chat.id, message.message_id)
    elif data.startswith('cdda_page'):
        _update_data()
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
