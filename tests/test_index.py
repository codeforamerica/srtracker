import app
import unittest
from mock import patch, Mock
import requests
from support import patch_get, patch_url

class SRTrackerTestCase(unittest.TestCase):
    
    def setUp(self):
        # TODO: create a custom test configuration - see below :P
        app.configure()
        # Turn off debug to avoid erroneous messages in test output
        # app.app.debug = False
        app.app.config['TESTING'] = True
        app.app.config['OPEN311_SERVER'] = 'open311:/'
        self.app = app.app.test_client()
        
    def tearDown(self):
        pass
    
    @patch_get('requests.json')
    def test_home_page_works(self, get):
        request = self.app.get('/')
        assert request.status_code == 200
        assert 'Find out the status of your 311 service request' in request.data
    
    @patch_get('requests_empty.json')
    def test_home_page_no_srs(self, get):
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
