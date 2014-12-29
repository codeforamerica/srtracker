# Copyright (C) 2012-2013, Code for America
# This is open source software, released under a standard 3-clause
# BSD-style license; see the file LICENSE for details.

import datetime
import requests

CACHE_TIMEOUT = datetime.timedelta(seconds=60 * 10)

services_list = None
last_services_update = datetime.datetime(1, 1, 1)

def services(open311_url, open311_api_key=None):
    global services_list, last_services_update

    if not services_list or datetime.datetime.utcnow() - last_services_update > CACHE_TIMEOUT:
        url = '%s/services.json' % open311_url
        params = open311_api_key and {'api_key': open311_api_key} or None
        r = requests.get(url, params=params)
        last_services_update = datetime.datetime.utcnow()
        if r.status_code == 200:
            services_list = r.json or []
        else:
            services_list = []

    return services_list
