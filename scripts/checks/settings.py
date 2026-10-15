import os

from stockmanager.settings import *  # noqa: F401,F403

# run.py points this at a throwaway database; never the real db.sqlite3
DATABASES["default"]["NAME"] = os.environ["CHECKS_DB"]  # noqa: F405
ALLOWED_HOSTS = ["*"]
DEBUG = False
