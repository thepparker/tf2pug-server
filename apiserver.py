#!/usr/bin/env python

import settings
import logging

import tornado.web
import tornado.ioloop

import psycopg2
import psycopg2.pool

from puglib import PugManager
from handlers import ResponseHandler, WebHandler
from serverlib import ServerManager

from tornado.options import define, options, parse_command_line

# allow command line overriding of these options
define("ip", default = settings.listen_ip, help = "The IP to listen on", type = str)
define("port", default = settings.listen_port, help = "The port to listen on", type = int)

# Raised when a user attempts to authorise with an invalid key
class InvalidKeyException(Exception):
    pass

class Application(tornado.web.Application):
    def __init__(self, db):
        handlers = [
            # pug creation and management
            (r"/ITF2Pug/List/", WebHandler.PugListHandler),
            (r"/ITF2Pug/Status/", WebHandler.PugStatusHandler),
            (r"/ITF2Pug/Create/", WebHandler.PugCreateHandler),
            (r"/ITF2Pug/End/", WebHandler.PugEndHandler),

            # pug player adding/removing/listing
            (r"/ITF2Pug/Player/Add/", WebHandler.PugAddHandler),
            (r"/ITF2Pug/Player/Remove/", WebHandler.PugRemoveHandler),
            (r"/ITF2Pug/Player/List/", WebHandler.PugPlayerListHandler),

            # map voting/other shit
            (r"/ITF2Pug/Map/Vote/", WebHandler.PugMapVoteHandler),
            (r"/ITF2Pug/Map/Force/", WebHandler.PugForceMapHandler),

        ]

        settings = {
            "debug": True,
        }

        self.db = db
        
        self.response_handler = ResponseHandler.ResponseHandler()

        self._pug_managers = {}

        self.server_manager = ServerManager.ServerManager(self.db)

        tornado.web.Application.__init__(self, handlers, **settings)

    def valid_api_key(self, key):
        logging.debug("Getting user details for API key %s", key)

        valid = False

        conn = None
        cursor = None

        try:
            conn = self.db.getconn()

            cursor = conn.cursor()
            cursor.execute("SELECT name FROM api_keys WHERE key = %s", (key,))

            results = cursor.fetchone()
            logging.debug("Results: %s", results)

            if results is None:
                raise InvalidKeyException("Invalid API key %s" % (key))
            else:
                valid = True

        except:
            logging.exception("Exception when validating API key")

        finally:
            if cursor:
                cursor.close()
            if conn:
                self.db.putconn(conn)

            return valid

    def get_manager(self, key):
        if key in self._pug_managers:
            return self._pug_managers[key]
        else:
            new_manager = PugManager.PugManager(key, self.db, self.server_manager)

            self._pug_managers[key] = new_manager

            return new_manager

    def close(self):
        # flush the managers to the database
        logging.info("Flushing pug managers")
        for manager in self._pug_managers:
            manager.flush_all()


        logging.info("Flushing server manager")
        self.server_manager.flush_all()

        logging.info("Managers successfully flushed")

if __name__ == "__main__":
    parse_command_line()

    dsn = "dbname=%s user=%s password=%s host=%s port=%s" % (
                settings.db_name, settings.db_user, settings.db_pass, 
                settings.db_host, settings.db_port
            )

    db = psycopg2.pool.SimpleConnectionPool(minconn = 1, maxconn = 1, dsn = dsn)

    api_server = Application(db)

    api_server.listen(options.port, options.ip)

    logging.info("TF2Pug API Server listening on %s:%d", options.ip, options.port)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except:
        logging.info("Shutting the server down...")

        api_server.close()
        db.close()
        tornado.ioloop.IOLoop.instance().stop()
        
        sys.exit(0)

