import shutil
from os import path
import json
from urllib import request
from typing import Optional

from . import DATA_VERSION_FILE, ALL_DATA_FILE, LAST_VERSION_URL, ALL_DATA_URL


def current_data_version() -> Optional[str]:
    if path.isfile(DATA_VERSION_FILE):
        with open(DATA_VERSION_FILE, 'r') as f:
            return f.read()
    return None


def last_version() -> str:
    data = json.loads(request.urlopen(LAST_VERSION_URL).read())
    return data['latest_build']


def download_data(version):
    if version != current_data_version():
        print(f"downloading {version}...")
        with open(ALL_DATA_FILE, 'wb') as data_file, \
                open(DATA_VERSION_FILE, 'w') as version_file, \
                request.urlopen(ALL_DATA_URL.format(version)) as response:
            shutil.copyfileobj(response, data_file)
            version_file.write(version)


if __name__ == "__main__":
    download_data(last_version())