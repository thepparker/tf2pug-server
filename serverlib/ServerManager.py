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
        for server in self._servers:
            if not server.in_use:
                server.setup(pug)

                self.flush_server(server)

                return server

        # if we've reached here, there are no servers available
        return None

    def reset(self, server):
        pass

    def get_servers(self):
        return self._servers

    def update_from_db(self):
        pass

    def flush_server(self, server):
        # write server details to database

        self.db.execute("UPDATE servers SET rcon_password = %s, password = %s, pug_id = %d, log_port = %d WHERE servers.id = %d", 
                (server.rcon_password, server.password, server.pug_id, server.log_port, server.id,)
            )

    def flush_all(self):
        for server in self._servers:
            self.flush_server(server)

    def hydrate_server(self, db_result):
        pass
