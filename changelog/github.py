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
    commit: str
    prev_commit: Optional[str] = None
    commit_messages: List[str] = None


def get_releases() -> Iterator[Release]:
    last_posted = published.get()

    releases = json.loads(urllib.request.urlopen(RELEASES_API).read())
    result = []
    for i, release in enumerate(releases):
        if release['id'] <= last_posted:
            break
        result.append(Release(release['id'], release['name'], release['html_url'], release['created_at'],
                              release['target_commitish'],
                              releases[i+1]['target_commitish'] if i < (len(releases)-1) else None))

    commits = json.loads(urllib.request.urlopen(COMMITS_API).read())
    for release in result:
        release.commit_messages = []
        started = False
        for commit in commits:
            if commit['sha'] == release.commit:
                started = True
            if commit['sha'] == release.prev_commit:
                break
            if started:
                release.commit_messages.append(commit['commit']['message'])

    return reversed(result)
