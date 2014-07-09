"""
This interface parses log data from the game server, and calls the appropriate
server and pug methods
"""

class BaseLogInterface(object):
    def __init__(self, server):
        self.server = server

    def parse(self, data):
        pass
