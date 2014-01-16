"""
This class will manage servers for TF2Pug. It will allocate, set passwords,
change maps, etc.
"""

import logging

import Server

class ServerManager(object):
    def __init__(self, db):
        self.db = db

        self._servers = []

        self.__load_servers()

    def allocate(self, pug):
        for server in self._servers:
            if not server.in_use:
                server.setup(pug)

                self._flush_server(server)

                return server

        # if we've reached here, there are no servers available
        return None

    def reset(self, server):
        pass

    def get_servers(self):
        return self._servers

    def update_from_db(self):
        pass

    def _flush_server(self, server):
        # write server details to database

        conn, cursor = self._get_db_objects()

        try:
            cursor.execute("UPDATE servers SET rcon_password = %s, password = %s, pug_id = %d, log_port = %d WHERE servers.id = %d", 
                    (server.rcon_password, server.password, server.pug_id, server.log_port, server.id,)
                )

            conn.commit()

        except:
            logging.exception("Exception flushing server")

        finally:
            self._close_db_objects((conn, cursor))


    def flush_all(self):
        for server in self._servers:
            self._flush_server(server)

    def __hydrate_server(self, db_result):
        server = Server()
        server.id = db_result[0]
        server.ip = db_result[1]

    def __load_servers(self):
        conn, cursor = self._get_db_objects()

        try:
            cursor.execute("SELECT id, ip, port, rcon_password, password, pug_id, log_port FROM servers")

            results = cursor.fetchall()

            if not results:
                logging.error("THERE ARE NO CONFIGURED SERVERS")
                return

            for result in results:
                self.__hydrate_server(result)

        except:
            logging.exception("Exception loading servers")

        finally:
            self._close_db_objects((conn, cursor))


    def _get_db_objects(self):
        conn = None
        curs = None

        try:
            conn = self.db.getconn()
            curs = db.cursor()

            return (conn, cursor)
        
        except:
            logging.exception("Exception getting db objects")

            if curs:
                curs.close()

            if conn:
                self.db.putconn()

    """
    Takes a tuple of (conn, cursor), closes the cursor and puts the conn back
    into the pool
    """
    def _close_db_objects(self, objects):
        if objects[1]:
            objects[1].close()

        if objects[0]:
            self.db.putconn(objects[0])
