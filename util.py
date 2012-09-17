# Copyright (C) 2012, Code for America
# This is open source software, released under a standard 3-clause
# BSD-style license; see the file LICENSE for details.

import os

def bool_from_string(value):
    return value in (True, 'True', 'true', 'T', 't', '1')

def bool_from_env(envvar, default=False):
    return bool_from_string(os.environ.get(envvar, default))
