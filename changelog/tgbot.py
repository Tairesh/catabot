import html
import os
import re
import traceback
from typing import List
from datetime import datetime

from telebot import TeleBot

from changelog import published
from changelog.github import Release

ADMIN = 31445050
CHANGELOG_CHANNEL = -1001332994456
GITHUB_ISSUE_URL_TEMPLATE = "https://github.com/CleverRaven/Cataclysm-DDA/issues/{}"
r_hashtag = re.compile(r'#([\d]+)')
HARDCODED_STRINGS = {
    "## What's Changed": "<b>What's changed:</b>",
    "**Full Changelog**:": "<b>Full Changelog:</b>",
}


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
    created_at = datetime.strptime(release.created_at, '%Y-%m-%dT%H:%M:%SZ')
    message = f'<a href="{release.url}"><b>{release.name}</b></a> {created_at}\n\n'

    if release.description:
        message += html.escape(release.description)
    else:
        message += '<i>(no changes)</i>'

    for (string, sub) in HARDCODED_STRINGS.items():
        message = message.replace(string, sub)

    bundles += _message_to_bundles(message)
    return bundles


def send(release: Release):

    bundles = get_bundles(release)

    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'token.txt')) as f:
        token = f.read()
    bot = TeleBot(token)

    try:
        for bundle in bundles:
            bot.send_message(CHANGELOG_CHANNEL, bundle, parse_mode='HTML')
        published.save(release.id)
    except Exception:
        bot.send_message(ADMIN, traceback.format_exc())
