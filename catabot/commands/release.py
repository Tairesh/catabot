import json
import urllib.request

from telebot import TeleBot
from telebot.apihelper import ApiException
from telebot.types import Message

from catabot import utils

CATADDA_GIT_API = "https://api.github.com/repos/CleverRaven/Cataclysm-DDA/releases"

LINUX = 'linux'
LINUX_NAMES = {'lin', 'linux'}
WINDOWS = 'windows'
WINDOWS_NAMES = {'win', 'window', 'windows'}
OSX = 'osx'
OSX_NAMES = {'osx', 'os x', 'apple', 'macos'}
ANDROID = 'android'
ANDROID_NAMES = {'android', 'phone', 'android64', 'android 64', 'android 64bit', 'android 64 bit'}
ANDROID32 = 'android32'
ANDROID32_NAMES = {'android32', 'android 32', 'android 32bit', 'android 32 bit'}
ALL_PLATFORM_NAMES = LINUX_NAMES | WINDOWS_NAMES | OSX_NAMES | ANDROID_NAMES | ANDROID32_NAMES

MODE_ALL = 'all'
MODE_VERSION = 'version'
MODE_PLATFORM = 'platform'
MODE_STABLE = 'stable'
MODE_LAST = 'last'
MODE_INVALID = 'invalid'


def get_release(bot: TeleBot, message: Message):
    bot.send_chat_action(message.chat.id, 'typing')
    keyword = utils.get_keyword(message).lower().strip()

    mode = MODE_ALL
    version = None
    if keyword:
        if keyword in ALL_PLATFORM_NAMES:
            mode = MODE_PLATFORM
            if keyword in LINUX_NAMES:
                version = LINUX
            elif keyword in WINDOWS_NAMES:
                version = WINDOWS
            elif keyword in OSX_NAMES:
                version = OSX
            elif keyword in ANDROID_NAMES:
                version = ANDROID
            elif keyword in ANDROID32_NAMES:
                version = ANDROID32
        elif keyword.isnumeric():
            mode = MODE_VERSION
            version = int(keyword)
            if version < 10000:
                mode = MODE_INVALID
        elif keyword == 'stable':
            mode = MODE_STABLE
        elif keyword in {'last', 'latest'}:
            mode = MODE_LAST
        elif keyword:
            mode = MODE_INVALID

    def _last_release() -> int:
        return int(json.loads(urllib.request.urlopen(CATADDA_GIT_API).read())[0]['name'].split('#').pop())

    def _links_from_assets(assets) -> dict:
        links = {
            LINUX: None,
            WINDOWS: None,
            OSX: None,
            ANDROID: None,
        }

        for asset in assets:
            if asset['label'] == 'Linux_x64 Tiles':
                links[LINUX] = asset['browser_download_url']
            elif asset['label'] == 'OSX Tiles':
                links[OSX] = asset['browser_download_url']
            elif asset['label'] == 'Windows_x64 Tiles':
                links[WINDOWS] = asset['browser_download_url']
            elif asset['label'].startswith('Android') and '64' in asset['label']:
                links[ANDROID] = asset['browser_download_url']
            elif asset['label'].startswith('Android') and '32' in asset['label']:
                links[ANDROID32] = asset['browser_download_url']
        return links

    def _send_links(name, links):
        text = "<b>Release " + name + ':</b>\n'
        for platform, link in links.items():
            text += platform + ': '
            if link:
                file = link.split('/').pop()
                text += f'<a href="{link}">{file}</a>\n'
            else:
                text += 'not compiled\n'
        bot.reply_to(message, text, parse_mode='html')

    if mode == MODE_INVALID:
        cmd = utils.get_command(message)
        bot.reply_to(message, "Usage example:\n"
                              f"`{cmd}` — last experimental build for all platforms\n"
                              f"`{cmd} latest` — latest experimental build (probably not succeeded)\n"
                              f"`{cmd} windows|linux|osx|android` — last (successful) build for selected platform\n"
                              f"`{cmd} stable` — last stable build\n"
                              f"`{cmd} 11483` — get build by number", parse_mode='Markdown')
        return
    elif mode == MODE_VERSION:
        delta = _last_release() - version
        page = int(delta / 100) + 1
        data = json.loads(urllib.request.urlopen(CATADDA_GIT_API + f'?page={page}&per_page=100').read())

        for release in data:
            if release['name'].endswith(keyword):
                _send_links(release['name'], _links_from_assets(release['assets']))
                return
    elif mode == MODE_STABLE:
        release = json.loads(urllib.request.urlopen(CATADDA_GIT_API + '/latest').read())
        _send_links(release['name'], _links_from_assets(release['assets']))
        return
    else:
        page = 1
        tmp_message = None
        while page < 100:
            data = json.loads(urllib.request.urlopen(CATADDA_GIT_API + f'?page={page}&per_page=100').read())
            for release in data:
                links = _links_from_assets(release['assets'])
                if (mode == MODE_PLATFORM and version in links and links[version]) \
                        or (mode == MODE_ALL and all(links.values())) \
                        or mode == MODE_LAST:
                    _send_links(release['name'], {version: links[version]} if mode == MODE_PLATFORM else links)
                    if tmp_message:
                        try:
                            bot.delete_message(tmp_message.chat.id, tmp_message.message_id)
                        except ApiException:
                            pass
                    return
            if page == 1:
                tmp_message = bot.reply_to(message, "🤔 I did not find a suitable version on the first page,"
                                                    " please wait a little.")
            page += 1

    bot.send_sticker(message.chat.id, 'CAADAgADxgADOtDfAeLvpRcG6I1bFgQ', message.message_id)
