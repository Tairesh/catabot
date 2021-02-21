import urllib.request
import urllib.error
from urllib.parse import quote

from bs4 import BeautifulSoup
from telebot import TeleBot
from telebot.apihelper import ApiException
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from catabot import utils

CATADDA_SEARCH = "https://cdda-trunk.chezzo.com/search?q={}"
CATADDA_LINK_START = "https://cdda-trunk.chezzo.com/"

NUMBERS_EMOJI = {
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
    10: "🔟",
}


def _get_search_results(keyword, action):
    results = []
    page = urllib.request.urlopen(CATADDA_SEARCH.format(quote(keyword))).read()
    soup = BeautifulSoup(page, features="html.parser")
    if action == 'monster':
        ul = soup.find('ul', {"class": "list-unstyled"})
        if ul:
            lis = ul.findAll('li')
            for li in lis:
                a = li.find('a')
                results.append((a.text, a["href"]))
    else:
        divs = soup.findAll('div', {"class": "row"})
        for div in divs:
            links = div.findAll('a')
            if len(links):
                text = f'<a href="{links[0]["href"]}"><b>{links[0].text}</b></a>'
                link = links[0]["href"]
                if action == 'craft':
                    link += "/craft"
                if action == 'disassemble':
                    link += "/disassemble"
                if len(links) > 1:
                    for ll in links[1:]:
                        text += f' <a href="{ll["href"]}">[{ll.text}]</a>'

                results.append((text, link))
    return results


def _parse_link(bot: TeleBot, message: Message, url: str):
    try:
        page = urllib.request.urlopen(url).read()
    except urllib.error.HTTPError as e:
        text = "I can't load item page: {}".format(e)
        bot.reply_to(message, text)
        return

    try:
        soup = BeautifulSoup(page, features="html.parser")
        div = soup.find('div', {"class": "row"}).find('div', {"class": "col-md-6"})
        title = soup.find('h4') if '/monsters/' in url else soup.find('h1')

        name = title.text
        desc = div.text.replace('\n\n\n', '\n\n').replace('\n\n\n', '\n\n').replace('>', '\n  >')
        text = f"<b>{name}</b><code>{desc}</code>"
        bot.reply_to(message, text, parse_mode='html')
    except Exception:
        bot.send_sticker(message.chat.id, 'CAADAgADyAADOtDfARL0PAOfBWJWFgQ', message.message_id)


def _get_page_view(results, keyword, action, maxpage, page=1):
    markup = InlineKeyboardMarkup(row_width=5)
    desc = f"Search results for {action} {keyword}\n"
    btns = []
    for i, (text, link) in enumerate(results):
        btn = InlineKeyboardButton(text=NUMBERS_EMOJI[i + 1], callback_data="cdda:" + link.replace(CATADDA_LINK_START, ''))
        btns.append(btn)
        desc += NUMBERS_EMOJI[i + 1] + ' ' + text + '\n'
    desc += f"(page {page} of {maxpage+1})"
    markup.add(*btns)
    btm_row = []
    if page > 1:
        btm_row.append(InlineKeyboardButton(text="⬅️ Prev.", callback_data=f"cdda_page{page - 1}_{action}:{keyword}"))
    btm_row.append(InlineKeyboardButton(text="❌ Cancel", callback_data="cdda_cancel"))
    if page <= maxpage:
        btm_row.append(InlineKeyboardButton(text="➡ Next️️", callback_data=f"cdda_page{page + 1}_{action}:{keyword}"))
    markup.add(*btm_row)
    return desc, markup


def search(bot: TeleBot, message: Message):
    bot.send_chat_action(message.chat.id, 'typing')
    keyword = utils.get_keyword(message)
    command = utils.get_command(message).lower()
    action = 'view'

    if command in {'/c', '/craft'}:
        action = 'craft'
    if command in {'/disassemble', '/d', '/disasm'}:
        action = 'disassemble'
    if command in {'/m', '/mob', '/monster'}:
        action = 'monster'
        example = 'your mom'
    else:
        example = 'glazed tenderloins'

    if not keyword:
        bot.reply_to(message, f"Usage example:\n<code>{command} {example}</code>", parse_mode='html')
        return

    tmp_message = bot.reply_to(message, "Loading search results...")

    try:
        results = _get_search_results(keyword, action)

        count = len(results)
        if count == 0:
            bot.send_sticker(message.chat.id, 'CAADAgADxgADOtDfAeLvpRcG6I1bFgQ', message.message_id)
        elif count == 1:
            _parse_link(bot, message, results[0][1])
        else:
            desc, markup = _get_page_view(results[0:10:], keyword, action, maxpage=int(count/10))
            bot.reply_to(message, desc, reply_markup=markup, parse_mode='HTML')

    except urllib.error.HTTPError as e:
        bot.reply_to(message, "I can't load search page: {}".format(e))

    try:
        bot.delete_message(message.chat.id, tmp_message.message_id)
    except ApiException:
        pass


def btn_pressed(bot: TeleBot, message: Message, data: str):
    bot.send_chat_action(message.chat.id, 'typing')
    if data.startswith('cdda:'):
        data = data[5::]
        url = CATADDA_LINK_START + data
        _parse_link(bot, message.reply_to_message, url)
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except ApiException:
            pass
    elif data == 'cdda_cancel':
        bot.edit_message_text(message.text.split('\n')[0] + '\n(canceled)', message.chat.id, message.message_id)
    elif data.startswith('cdda_page'):
        page, actkey = data[9::].split('_')
        action, keyword = actkey.split(':')
        page = int(page)
        if page < 1:
            return
        results = _get_search_results(keyword, action)
        count = len(results)
        results = results[(page-1)*10:page*10:]
        if len(results) == 0:
            return
        desc, markup = _get_page_view(results, keyword, action, maxpage=int(count/10), page=page)
        try:
            bot.edit_message_text(desc, message.chat.id, message.message_id, reply_markup=markup, parse_mode='HTML')
        except ApiException:
            pass
