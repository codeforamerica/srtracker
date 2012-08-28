import os

def bool_from_string(value):
    return value in (True, 'True', 'true', 'T', 't', '1')

def bool_from_env(envvar, default=False):
    return bool_from_string(os.environ.get(envvar, default))
