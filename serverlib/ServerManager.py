"""
This class will manage servers for TF2Pug. It will allocate, set passwords,
change maps, etc.
"""

import logging

import Server

server_columns = (
        "id", 
        "ip", 
        "port", 
        "rcon_password",
        "password", 
        "pug_id",
        "log_port"
    )

class ServerManager(object):
    def __init__(self, db):
        self.db = db

        self._servers = []

    def allocate(self, pug):
        self.__load_servers()

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
            conn.rollback()

        finally:
            self._close_db_objects((conn, cursor))


    def flush_all(self):
        for server in self._servers:
            self._flush_server(server)

    def __hydrate_server(self, db_result):
        logging.debug("HYDRATING SERVER DB RESULT: %s", db_result)

        server = Server()
        server.id = db_result[0]
        server.ip = db_result[1]
        server.port = db_result[2]
        server.rcon_password = db_result[3]
        server.password = db_result[4]
        server.pug_id = db_result[5]
        server.log_port = db_result[6]

        return server

    def __load_servers(self):
        conn, cursor = self._get_db_objects()

        # clear the server list first
        del self._servers[:]

        try:
            cursor.execute("SELECT %s FROM servers" % (", ".join(server_columns)))

            results = cursor.fetchall()

            if not results:
                logging.error("THERE ARE NO CONFIGURED SERVERS")
                return

            for result in results:
                hydrated = self.__hydrate_server(result)

                self._servers.append(hydrated)

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
                self.db.putconn(conn)

    """
    Takes a tuple of (conn, cursor), closes the cursor and puts the conn back
    into the pool
    """
    def _close_db_objects(self, objects):
        if objects[1]:
            objects[1].close()

        if objects[0]:
            self.db.putconn(objects[0])
