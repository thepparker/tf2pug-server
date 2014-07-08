"""
This class will manage servers for TF2Pug. It will allocate, set passwords,
change maps, etc.
"""

import logging

import psycopg2.extras

from entities.Server import Server

class ServerManager(object):
    def __init__(self, group, db):
        self.group = group
        self.db = db

        self._servers = []

        self.__load_servers()

    def allocate(self, pug):
        self.__load_servers() # reload servers, in case any new ones were added

        for server in self._servers:
            if not server.in_use:
                server.reserve(pug)

                self._flush_server(server)

                return server

        # if we've reached here, there are no servers available
        return None

    def reset(self, server):
        server.reset()

        self._flush_server(server)

    def get_server_by_id(self, sid):
        for server in self._servers:
            if server.id == sid:
                return server

        return None

    def _flush_server(self, server):
        # write server details to database
        self.db.flush_server(server)


    def flush_all(self):
        for server in self._servers:
            self._flush_server(server)

    def __hydrate_server(self, data):
        logging.debug("HYDRATING SERVER. DB RESULT: %s", data)

        server = Server()
        server.id = data["id"]
        server.ip = data["ip"]
        server.port = data["port"]
        server.rcon_password = data["rcon_password"]
        server.password = data["password"]
        server.pug_id = data["pug_id"]
        server.log_port = data["log_port"]
        server.group = data["server_group"]

        return server

    def __load_servers(self):
        # clear the server list first?
        del self._servers[:]

        results = self.db.get_servers(self.group)

        if not results:
            logging.error("THERE ARE NO CONFIGURED SERVERS FOR GROUP %d!", self.group)
            return

        for result in results:
            server = self.__hydrate_server(result)

            self._servers.append(server)
