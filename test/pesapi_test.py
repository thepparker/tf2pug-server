import sys
sys.path.append('..')

import unittest
import threading
import socket
import logging

import settings

from pprint import pprint

from interfaces import pesapi

from tornado import ioloop

class APITestCase(unittest.TestCase):
    def setUp(self):
        self.api = pesapi.PESAPIInterface(settings.pes_api_base_url,
                                          settings.pes_api_userid,
                                          settings.pes_api_privatekey)

    def tearDown(self):
        pass

class CreateMatchTestCase(APITestCase):
    pass

class CreateReportTestCase(APITestCase):
    def test_report(self):
        offender = 1234L
        victim = 12345L

        reason = "CHEATING"
        match_id = 1

        self.api.create_report(offender, victim, reason, match_id, 
            callback = lambda d: pprint(d))

def test_suites():
    classes = [ CreateMatchTestCase, CreateReportTestCase ]

    return [ unittest.TestLoader().loadTestsFromTestCase(x) for x in classes ]

if __name__ == "__main__":
    unittest.TestSuite(test_suites())

    # get a tornado ioloop instance running in another thread so we can
    # actually test this shiz
    t = threading.Thread(target = unittest.main)
    t.start()
    
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        quit()
