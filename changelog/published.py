import os


LAST_PUBLISHED_VERSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "changelog_posted.txt")


def get() -> int:
    """
    Get last published release ID
    :return: last published release ID
    """
    if os.path.isfile(LAST_PUBLISHED_VERSION_FILE):
        with open(LAST_PUBLISHED_VERSION_FILE, 'r') as f:
            return int(f.read().strip())
    else:
        return 0


def save(version: int):
    """
    Save last published release ID
    :param version: last published release ID
    :return:
    """
    with open(LAST_PUBLISHED_VERSION_FILE, 'w') as f:
        f.write(str(version))
