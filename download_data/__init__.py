from os import path

ROOT_DIR = path.dirname(path.dirname(__file__))
DATA_VERSION_FILE = path.join(ROOT_DIR, "data_version.txt")
ALL_DATA_FILE = path.join(ROOT_DIR, "data.json")
ALL_DATA_URL = "https://raw.githubusercontent.com/nornagon/cdda-data/main/data/latest/all.json"
