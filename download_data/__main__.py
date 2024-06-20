import shutil
from os import path
from urllib import request
from typing import Optional

from . import DATA_VERSION_FILE, ALL_DATA_FILE, ALL_DATA_URL


def current_data_version() -> Optional[str]:
    if path.isfile(DATA_VERSION_FILE):
        with open(DATA_VERSION_FILE, 'r') as f:
            return f.read()
    return None


def download_data():
    with open(ALL_DATA_FILE, 'wb') as data_file, \
            request.urlopen(ALL_DATA_URL) as response:
        shutil.copyfileobj(response, data_file)


if __name__ == "__main__":
    download_data()
