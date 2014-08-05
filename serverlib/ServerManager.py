"""
This class will manage servers for TF2Pug. It will allocate, set passwords,
change maps, etc.
"""

import logging

import psycopg2.extras

from entities.Server import Server

class ServerManager(object):
    def __init__(self, group, db):
        self.game = "TF2"
        self.group = group
        self.db = db

        self._late_loaded = True

        self._servers = []

        self.__load_servers()

    def allocate(self, pug):
        self.__load_servers() # reload servers, in case any new ones were added

        for server in self._servers:
            if not server.in_use:
                server.reserve(pug)

                return server

        # if we've reached here, there are no servers available
        return None

    def prepare(self, server):
        server.prepare()

        self._flush_server(server)

    def reset(self, server):
        if server is None:
            return
            
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

        server = Server(self.game)
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
        results = self.db.get_servers(self.group)

        if not results:
            logging.error("THERE ARE NO CONFIGURED SERVERS FOR GROUP %d!", self.group)
            return

        new_servers = [ self.__hydrate_server(x) for x in results ]
        new_list = []

        for new_server in new_servers:
            existing_server = self.get_server_by_id(new_server.id)
            if existing_server is not None:
                # this server exists in the server list already, so we just
                # update some params
                existing_server.ip = new_server.ip
                existing_server.port = new_server.port
                existing_server.rcon_password = new_server.rcon_password

                new_list.append(existing_server)
            
            else:
                # this is a new server coming into this manager. late loading
                # is ONLY DONE WHEN THIS DAEMON STARTS!
                new_list.append(new_server)


        # we now have a list of all the servers belonging to this manager's
        # server group. if a server was removed from the group in the db,
        # it will be reflected here as well. likewise if a new server was
        # added
        self._servers = new_list

    def late_load(self):
        if not self._late_loaded:
            return
        
        for server in self._servers:
            server.late_loaded()

        self._late_loaded = False
