# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config(object):
    # set app configs
    SECRET_KEY = os.getenv('SECRET_KEY')
    CHECK_ACCESS_URL = os.getenv('CHECK_ACCESS_URL')
    FOTOS_LIMIT_PER_PAGE = os.getenv('ADDRESS_LIMIT_PER_PAGE')
    LOG_FILENAME = os.getenv('LOG_FILENAME')
    LOG_LEVEL = os.getenv('LOG_LEVEL')
    FERNET_KEY = os.getenv('FERNET_KEY')
    PAGE_LIMIT = os.getenv('PAGE_LIMIT')
    MONGO_URI = os.getenv('MONGO_URI')

class TestConfig(Config):
    PAGE_LIMIT = "2"
    LOG_LEVEL = "DEBUG"
    MONGO_TEST_URI = os.getenv('MONGO_TEST_URI')
