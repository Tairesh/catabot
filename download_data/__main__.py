import shutil
from urllib import request

from . import ALL_DATA_FILE, ALL_DATA_URL


def download_data():
    with open(ALL_DATA_FILE, 'wb') as data_file, \
            request.urlopen(ALL_DATA_URL) as response:
        shutil.copyfileobj(response, data_file)


if __name__ == "__main__":
    download_data()
