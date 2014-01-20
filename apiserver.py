#!/usr/bin/env python

import logging
import sys
import time

import settings

import tornado.web
import tornado.ioloop

import psycopg2
import psycopg2.pool

from puglib import PugManager, Pug
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

        self._auth_cache = {}

        # perform the mapvote timer check every 2 seconds
        self._map_vote_timer = tornado.ioloop.PeriodicCallback(self._map_vote_check, 2000)
        self._map_vote_timer.start()

        self.__load_pug_managers()

        tornado.web.Application.__init__(self, handlers, **settings)

    def valid_api_key(self, key):
        if key in self._auth_cache:
            logging.debug("Key %s is in auth cache", key)

            valid, cache_time = self._auth_cache[key]

            # check if the cache has expired
            # if it has expired, we remove the key from the cache and recache
            if (time.time() - cache_time) > 120:
                logging.debug("Cache for key has expired")
                del self._auth_cache[key]

            else:
                # cache has not expired
                logging.debug("Key is in cache and has not expired. Valid: %s", valid)
                return valid

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
            if cursor and not cursor.closed:
                cursor.close()

            if conn:
                self.db.putconn(conn)

            # add to cache 
            self._auth_cache[key] = (valid, time.time())

            return valid

    def get_manager(self, key):
        if key in self._pug_managers:
            return self._pug_managers[key]

        else:
            logging.debug("Getting new pug manager for key %s", key)
            
            new_manager = PugManager.PugManager(key, self.db, self.server_manager)

            self._pug_managers[key] = new_manager

            return new_manager

    def _map_vote_check(self):
        curr_ctime = time.time()

        for manager in self._pug_managers.values():
            for pug in manager.get_pugs():
                if pug.state == Pug.states["MAP_VOTING"] and curr_ctime > pug.map_vote_end:
                    logging.debug("Map vote period is over for pug %d", pug.id)
                    # END MAP VOTING FOR THIS PUG
                    pug.end_map_vote()

    def __load_pug_managers(self):
        logging.info("Loading pug managers for all users")
        conn = None
        cursor = None
        results = None

        try:
            conn = self.db.getconn()
            cursor = conn.cursor()

            cursor.execute("SELECT key FROM api_keys")
            results = cursor.fetchall()

        except:
            logging.exception("Exception getting retrieving all API keys")

        finally:
            if cursor and not cursor.closed:
                cursor.close()

            if conn:
                self.db.putconn(conn)

        logging.debug("API keys in database: %s", results)

        if results:
            for key_tuple in results:
                self.get_manager(key_tuple[0])

    def close(self):
        self._map_vote_timer.stop()

        # flush the managers to the database
        logging.info("Flushing pug managers")
        for manager in self._pug_managers.values():
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

    db = psycopg2.pool.SimpleConnectionPool(minconn = 1, maxconn = 1, 
        dsn = dsn)

    api_server = Application(db)

    api_server.listen(options.port, options.ip)

    logging.info("TF2Pug API Server listening on %s:%d", options.ip, options.port)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except:
        logging.info("Shutting the server down...")

        api_server.close()
        db.closeall()
        tornado.ioloop.IOLoop.instance().stop()
        
        sys.exit(0)

