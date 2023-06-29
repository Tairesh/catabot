import json
import urllib.request
from dataclasses import dataclass
from typing import Iterator, Optional, List

from changelog import published

CATADDA_GIT_API = "https://api.github.com/repos/CleverRaven/Cataclysm-DDA/"
RELEASES_API = f"{CATADDA_GIT_API}releases"
COMMITS_API = f"{CATADDA_GIT_API}commits"


@dataclass
class Release:
    id: int
    name: str
    url: str
    created_at: str
    description: str


def get_releases() -> Iterator[Release]:
    last_posted = published.get()

    releases = json.loads(urllib.request.urlopen(RELEASES_API).read())
    result = []
    for i, release in enumerate(releases):
        if release['id'] <= last_posted:
            break
        result.append(
            Release(release['id'], release['name'], release['html_url'], release['created_at'], release['body'])
        )

    return reversed(result)
