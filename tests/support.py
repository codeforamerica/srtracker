import os
import json
import functools
import re
from mock import patch, Mock
import requests

FIXTURE_BASE_PATH = 'tests/fixtures'

def patch_url(match_url, fixture_path):
    '''Patch requests to return the content of the file at `fixture_path`
    for URLs matching `match_url`'''
    
    def decorate(func):
        if hasattr(func, '_mocked_urls'):
            func._mocked_urls.append((match_url, fixture_path))
            return func
        else:
            def url_content(url, *args, **kwargs):
                for url_pattern in patched._mocked_urls:
                    if re.match(url_pattern[0], url):
                        return mock_request(url_pattern[1])
                return Mock(status_code=404, text='', json=None)
            
            @functools.wraps(func)
            @patch('requests.get', Mock(side_effect=url_content))
            def patched(self):
                func(self, requests.get)
            patched._mocked_urls = [(match_url, fixture_path)]
            return patched
    
    return decorate

def patch_get(fixture_path):
    'Patch requests to return the content of the file at `fixture_path`'
    return patch_url('.', fixture_path)

def mock_request(fixture_path):
    'Create a mock HTTP response using the file at `fixture_path`'
    with open(os.path.join(FIXTURE_BASE_PATH, fixture_path)) as fixture:
        content = fixture.read()
        data = json.loads(content)
    return Mock(status_code=200, text=content, json=data)