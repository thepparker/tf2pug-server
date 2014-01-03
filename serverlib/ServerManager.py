"""
This class will manage servers for TF2Pug. It will allocate, set passwords,
change maps, etc.
"""

import Server

class ServerManager(object):
    def __init__(self, db):
        self.db = db

        self._servers = []

    def allocate(self, pug):
        pass

    def reset(self, server):
        pass

    def get_servers(self):
        return self._servers

    def update_from_db(self):
        pass

    def flush_server(self, server):
        pass

    def flush_all(self):
        pass

    def hydrate_server(self, db_result):
        pass
