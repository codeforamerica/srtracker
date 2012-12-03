import os
import app
import unittest
import json
from mock import patch, Mock
import requests

FIXTURE_BASE_PATH = 'tests/fixtures'

class SRTrackerTestCase(unittest.TestCase):
    
    def setUp(self):
        # TODO: create a custom test configuration - see below :P
        app.configure()
        # Turn off debug to avoid erroneous messages in test output
        # app.app.debug = False
        app.app.config['TESTING'] = True
        self.app = app.app.test_client()
        
    def tearDown(self):
        pass
    
    def mock_request(self, fixture_path):
        with open(os.path.join(FIXTURE_BASE_PATH, fixture_path)) as fixture:
            content = fixture.read()
            data = json.loads(content)
        return Mock(status_code=200, text=content, json=data)
    
    @patch('requests.get')
    def test_home_page_works(self, get):
        get.return_value = self.mock_request('requests.json')
        
        request = self.app.get('/')
        assert request.status_code == 200
        assert 'Find out the status of your 311 service request' in request.data
    
    @patch('requests.get')
    def test_home_page_no_srs(self, get):
        get.return_value = self.mock_request('requests_empty.json')
        
        request = self.app.get('/')
        assert request.status_code == 200
        assert 'Find out the status of your 311 service request' in request.data
        self.assertNotIn('Recent Service Requests', request.data, 'Recent service requests list should not be shown at all if there aren\'t any requests.')
    
    # TODO: Issue #46 (https://github.com/codeforamerica/srtracker/issues/46)
    # Requests will raise if the API is unreachable
    @unittest.skip('This bug has not been addressed yet. Stop skipping the test when #46 is being worked on.')
    @patch('requests.get', Mock(side_effect=requests.exceptions.ConnectionError('API Unreachable')))
    def test_home_page_no_api(self):
        request = self.app.get('/')
        
        assert request.status_code == 200
        assert 'Find out the status of your 311 service request' in request.data
        self.assertNotIn('Recent Service Requests', request.data, 'Recent service requests should not be shown when Open311 API is not available.')


if __name__ == '__main__':
    unittest.main()
