import json
import urllib.request
from enum import Enum, auto

from telebot import TeleBot
from telebot.apihelper import ApiException
from telebot.types import Message

from catabot import utils

CATADDA_GIT_API = "https://api.github.com/repos/CleverRaven/Cataclysm-DDA/releases"
CATATAIRESH_GIT_API = "https://api.github.com/repos/Tairesh/Cataclysm-DDA/releases"
CATABN_GIT_API = "https://api.github.com/repos/cataclysmbnteam/Cataclysm-BN/releases"

LINUX = 'linux'
LINUX_NAMES = {'lin', 'linux'}
LINUX_ASSET_NAMES = {'linux-with-graphics-and-sounds', 'linux-tiles-x64'}
WINDOWS = 'windows'
WINDOWS_NAMES = {'win', 'windows'}
WINDOWS_ASSET_NAMES = {'windows-with-graphics-and-sounds-x64', 'windows-tiles-x64-msvc'}
WINDOWS32 = 'windows x32'
WINDOWS32_NAMES = {'windows32', 'win32', 'windows 32', 'win 32'}
WINDOWS32_ASSET_NAMES = {'windows-with-graphics-and-sounds-x32', 'windows-tiles-x32-msvc'}
OSX = 'osx'
OSX_NAMES = {'osx', 'os x', 'apple', 'macos'}
OSX_ASSET_NAMES = {'osx-with-graphics-universal'}
ANDROID = 'android'
ANDROID_NAMES = {'android', 'phone', 'android64', 'android 64', 'android 64bit', 'android 64 bit'}
ANDROID_ASSET_NAMES = {'android-x64'}
ANDROID32 = 'android x32'
ANDROID32_NAMES = {'android32', 'android 32', 'android 32bit', 'android 32 bit'}
ANDROID32_ASSET_NAMES = {'android-x32'}
ALL_PLATFORM_NAMES = LINUX_NAMES | WINDOWS_NAMES | WINDOWS32_NAMES | OSX_NAMES | ANDROID_NAMES | ANDROID32_NAMES


class Mode(Enum):
    ALL = auto()
    VERSION = auto()
    PLATFORM = auto()
    STABLE = auto()
    LAST = auto()
    INVALID = auto()


def get_release(bot: TeleBot, message: Message):
    bot.send_chat_action(message.chat.id, 'typing')
    keyword = utils.get_keyword(message, False).lower().strip()

    mode = Mode.LAST
    fork = None
    version = None
    if keyword:
        if keyword in ALL_PLATFORM_NAMES:
            mode = Mode.PLATFORM
            if keyword in LINUX_NAMES:
                version = LINUX
            elif keyword in WINDOWS_NAMES:
                version = WINDOWS
            elif keyword in WINDOWS32_NAMES:
                version = WINDOWS32
            elif keyword in OSX_NAMES:
                version = OSX
            elif keyword in ANDROID_NAMES:
                version = ANDROID
            elif keyword in ANDROID32_NAMES:
                version = ANDROID32
        elif keyword.isnumeric():
            mode = Mode.VERSION
            version = int(keyword)
            if version < 10000:
                mode = Mode.INVALID
        elif keyword == 'all':
            mode = Mode.ALL
        elif keyword == 'stable':
            mode = Mode.STABLE
        elif keyword in {'last', 'latest'}:
            mode = Mode.LAST
        elif keyword in {'bn', 'bright nights'}:
            fork = 'bn'
            mode = Mode.LAST
        elif keyword == 'tairesh':
            fork = 'tairesh'
            mode = Mode.LAST
        elif keyword:
            mode = Mode.INVALID

    if fork == 'bn':
        api = CATABN_GIT_API
    elif fork == 'tairesh':
        api = CATATAIRESH_GIT_API
    else:
        api = CATADDA_GIT_API

    def _last_release() -> int:
        return int(json.loads(urllib.request.urlopen(api).read())[0]['name'].split('#').pop())

    def _links_from_assets(assets) -> dict:
        links = {
            LINUX: None,
            WINDOWS: None,
            OSX: None,
            ANDROID: None,
        }

        asset_names_by_platform = {
            LINUX: LINUX_ASSET_NAMES,
            OSX: OSX_ASSET_NAMES,
            WINDOWS: WINDOWS_ASSET_NAMES,
            WINDOWS32: WINDOWS32_ASSET_NAMES,
            ANDROID: ANDROID_ASSET_NAMES,
            ANDROID32: ANDROID32_ASSET_NAMES,
        }

        for platform in asset_names_by_platform:
            for asset in assets:
                for s in asset_names_by_platform[platform]:
                    if s in asset['name']:
                        links[platform] = asset['browser_download_url']
                        break
        return links

    def _send_links(name, links):
        text = name + ':\n\n'
        for platform, link in links.items():
            text += platform + ': '
            if link:
                file = link.split('/').pop()
                text += f'<a href="{link}">{file}</a>\n'
            else:
                text += 'not compiled\n'
        bot.reply_to(message, text, parse_mode='html')

    def _release_name(release):
        name = release['name'] if release['name'] else release['tag_name']
        date = release['published_at'].replace('T', ' ').replace('Z', '')
        return f"Release <b>{name}</b> <i>{date}</i>"

    if mode == Mode.INVALID:
        cmd = utils.get_command(message)
        bot.reply_to(message, "Usage example:\n"
                              f"`{cmd}` — latest experimental release\n"
                              f"`{cmd} all` — last experimental release, builded for all platforms\n"
                              f"`{cmd} windows|linux|osx|android` — last (successful) release, builded for selected platform\n"
                              f"`{cmd} stable` — last stable release\n"
                              f"`{cmd} bn` — Cataclysm: Bright Nights last release", parse_mode='Markdown')
        return
    elif mode == Mode.VERSION:
        delta = _last_release() - version
        page = int(delta / 100) + 1
        data = json.loads(urllib.request.urlopen(api + f'?page={page}&per_page=100').read())

        for release in data:
            if release['name'].endswith(keyword):
                _send_links(_release_name(release), _links_from_assets(release['assets']))
                return
    elif mode == Mode.STABLE:
        release = json.loads(urllib.request.urlopen(api + '/latest').read())
        _send_links(_release_name(release), _links_from_assets(release['assets']))
        return
    else:
        page = 1
        tmp_message = None
        while page < 10:
            data = json.loads(urllib.request.urlopen(api + f'?page={page}&per_page=100').read())
            for release in data:
                links = _links_from_assets(release['assets'])
                if (mode == Mode.PLATFORM and version in links and links[version]) \
                        or (mode == Mode.ALL and all(links.values())) \
                        or mode == Mode.LAST:
                    _send_links(_release_name(release), {version: links[version]} if mode == Mode.PLATFORM else links)
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

    if tmp_message:
        try:
            bot.delete_message(tmp_message.chat.id, tmp_message.message_id)
        except ApiException:
            pass
    bot.send_sticker(message.chat.id, 'CAADAgADxgADOtDfAeLvpRcG6I1bFgQ', message.message_id)
