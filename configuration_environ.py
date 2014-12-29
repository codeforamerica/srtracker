# Copyright (C) 2012-2013, Code for America
# This is open source software, released under a standard 3-clause
# BSD-style license; see the file LICENSE for details.

from os import environ
from util import bool_from_env

# SR TRACKER
DEBUG              = bool_from_env('DEBUG')
SECRET_KEY         = environ.get('SECRET_KEY')
PASSWORD_PROTECTED = bool_from_env('PASSWORD_PROTECTED')
PASSWORD           = environ.get('PASSWORD', '')
MAX_RECENT_SRS     = int(environ.get('MAX_RECENT_SRS', 50))
SRS_PAGE_SIZE      = int(environ.get('SRS_PAGE_SIZE', 0))
RECENT_SRS_TIME    = int(environ.get('RECENT_SRS_TIME', 7 * 24 * 60 * 60))  # (in seconds)
if 'SR_FIELD_BLACKLIST' in environ:
	SR_FIELD_BLACKLIST = map(lambda item: item.strip(), environ['SR_FIELD_BLACKLIST'].split(','))
DOCUMENTATION_LINK  = environ.get('DOCUMENTATION_LINK')
GOOGLE_ANALYTICS_ACCOUNT = environ.get('GOOGLE_ANALYTICS_ACCOUNT')

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

SRTRACKER_URL      = environ.get('SRTRACKER_URL', 'http://chicagosrtracker/')
