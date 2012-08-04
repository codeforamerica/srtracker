from os import environ

OPEN311_SERVER = environ.get('OPEN311_SERVER')
OPEN311_API_KEY = environ.get('OPEN311_API_KEY')
OPEN311_PAGE_SIZE = 1000
DB_STRING = environ.get('DATABASE_URL')
EMAIL_HOST = environ.get('EMAIL_HOST')
EMAIL_PORT = environ.get('EMAIL_PORT')
EMAIL_USER = environ.get('EMAIL_USER')
EMAIL_PASS = environ.get('EMAIL_PASS')
EMAIL_FROM = environ.get('EMAIL_FROM')
EMAIL_SSL = environ.get('EMAIL_SSL')
