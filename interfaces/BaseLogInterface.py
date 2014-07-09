"""
This interface parses log data from the game server, and calls the appropriate
server and pug methods. The socket should already be established.
"""

class BaseLogInterface(object):
    def __init__(self):
        pass

    def parse(self, data):
        pass
