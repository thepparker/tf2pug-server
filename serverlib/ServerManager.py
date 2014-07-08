"""
This class will manage servers for TF2Pug. It will allocate, set passwords,
change maps, etc.
"""

import logging

import psycopg2.extras

from entities.Server import Server

server_columns = (
        "id", 
        "HOST(ip) as ip", 
        "port", 
        "rcon_password",
        "password", 
        "pug_id",
        "log_port"
    )

class ServerManager(object):
    def __init__(self, api_key, db):
        self.api_key = api_key
        self.db = db

        self._servers = []

        self.__load_servers()

    def allocate(self, pug):
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

        conn, cursor = self._get_db_objects()

        try:
            cursor.execute("UPDATE servers SET password = %s, pug_id = %s, log_port = %s WHERE servers.id = %s", 
                    (server.password, server.pug_id, server.log_port, server.id,)
                )

            conn.commit()

        except:
            logging.exception("Exception flushing server")
            conn.rollback()

        finally:
            self._close_db_objects((conn, cursor))


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

        return server

    def __load_servers(self):
        # clear the server list first
        del self._servers[:]

        self.db.get_servers(self.api_key)

        try:
            cursor.execute("SELECT %s FROM servers" % (", ".join(server_columns)))

            results = cursor.fetchall()

            if not results:
                logging.error("THERE ARE NO CONFIGURED SERVERS")
                return

            for result in results:
                server = self.__hydrate_server(result)

                self._servers.append(server)

        except:
            logging.exception("Exception loading servers")

        finally:
            self._close_db_objects((conn, cursor))

    """
    Retrieves a db connection and a cursor in a (conn, cursor) tuple from the
    db pool
    """
    def _get_db_objects(self):
        conn = None
        curs = None

        try:
            conn = self.db.getconn()
            curs = conn.cursor(cursor_factory = psycopg2.extras.DictCursor)

            return (conn, curs)
        
        except:
            logging.exception("Exception getting db objects")

            if curs:
                curs.close()

            if conn:
                self.db.putconn(conn)

    """
    Takes a tuple of (conn, cursor), closes the cursor and puts the conn back
    into the pool
    """
    def _close_db_objects(self, objects):
        if objects[1] and not objects[1].closed:
            objects[1].close()

        if objects[0]:
            self.db.putconn(objects[0])
