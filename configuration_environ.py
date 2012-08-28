from os import environ
from util import bool_from_env

# SR TRACKER
DEBUG              = bool_from_env('DEBUG')
SECRET_KEY         = environ.get('SECRET_KEY')
PASSWORD_PROTECTED = bool_from_env('PASSWORD_PROTECTED')
PASSWORD           = environ.get('PASSWORD', '')

# SHARED
OPEN311_SERVER     = environ.get('OPEN311_SERVER')
OPEN311_API_KEY    = environ.get('OPEN311_API_KEY')

# UPDATER
OPEN311_PAGE_SIZE  = 1000
DB_STRING          = environ.get('DATABASE_URL')
THREADED_UPDATES   = False
EMAIL_HOST         = environ.get('EMAIL_HOST')
EMAIL_PORT         = environ.get('EMAIL_PORT', 465)
EMAIL_USER         = environ.get('EMAIL_USER')
EMAIL_PASS         = environ.get('EMAIL_PASS')
EMAIL_FROM         = environ.get('EMAIL_FROM')
EMAIL_SSL          = environ.get('EMAIL_SSL', True)
EMAIL_MAX_THREADS  = environ.get('EMAIL_MAX_THREADS', 5)

SR_DETAILS_URL     = environ.get('SR_DETAILS_URL', 'http://chicagosrtracker/requests/{sr_id}')
SR_TRACKER_IMG     = environ.get('SR_TRACKER_IMG', 'http://chicagosrtracker/static/img/')
SR_UNSUBSCRIBE_URL = environ.get('SR_UNSUBSCRIBE_URL', 'http://chicagosrtracker/unsubscribe/{key}')
