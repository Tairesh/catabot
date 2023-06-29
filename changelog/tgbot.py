import html
import os
import re
import traceback
from typing import List

from telebot import TeleBot

from changelog import published
from changelog.github import Release

ADMIN = 31445050
GITHUB_ISSUE_URL_TEMPLATE = "https://github.com/CleverRaven/Cataclysm-DDA/issues/{}"
r_hashtag = re.compile(r'#([\d]+)')


def _prepare(text: str) -> str:
    text = html.escape(text.replace('\n\n', '\n'))

    def _hashtag(match):
        number = match.group(1)
        url = GITHUB_ISSUE_URL_TEMPLATE.format(number)
        return f'<a href="{url}">#{number}</a>'

    text = r_hashtag.sub(_hashtag, text)
    return text


def _message_to_bundles(message: str) -> List[str]:
    if len(message) > 4000:
        bundles = []
        rows = message.split('\n')
        cm = ''
        for row in rows:
            if len(cm) + len(row) < 4000:
                cm += row + '\n'
            else:
                bundles.append(cm)
                cm = row + '\n'
        if len(cm):
            bundles.append(cm)
        return bundles
    else:
        return [message]


def get_bundles(release: Release) -> List[str]:
    bundles = []
    message = f'<a href="{release.url}"><b>{release.name}</b></a> {release.created_at}\n\n'

    if release.description:
        message += release.description
    else:
        message += '<i>(no changes)</i>'

    bundles += _message_to_bundles(message)
    return bundles


def send(release: Release):

    bundles = get_bundles(release)

    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'token.txt')) as f:
        token = f.read()
    bot = TeleBot(token)

    try:
        for bundle in bundles:
            bot.send_message(-1001332994456, bundle, parse_mode='HTML')
        published.save(release.id)
    except Exception:
        bot.send_message(ADMIN, traceback.format_exc())
