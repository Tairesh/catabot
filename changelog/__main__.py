from .github import get_releases
from .tgbot import send


for release in get_releases():
    send(release)
