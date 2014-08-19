#!/usr/bin/env python

import logging
import sys
import time

import settings

import tornado.web
import tornado.ioloop

import psycopg2
import psycopg2.pool

from puglib import PugManager, bans
from handlers import ResponseHandler, WebHandler
from serverlib import ServerManager

from interfaces import get_db_interface

from tornado.options import define, options, parse_command_line
from tornado.ioloop import PeriodicCallback

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

            # player banning
            (r"/ITF2Pug/Ban/Add/", WebHandler.BanAddHandler),
            (r"/ITF2Pug/Ban/Remove/", WebHandler.BanRemoveHandler),
            (r"/ITF2Pug/Ban/List/", WebHandler.BanListHandler),

            # stats
            (r"/ITF2Pug/Stat/", WebHandler.StatHandler),
        ]

        settings = {
            "debug": True,
        }

        self.db = db
        
        self.response_handler = ResponseHandler.ResponseHandler()
        # pug managers are currently per API key
        self._pug_managers = {}
        # server managers are per server group. each server group can have
        # multiple pug managers attached to it
        self._server_managers = {}

        self.ban_manager = bans.BanManager(db)

        """ Auth cache is in the following form:
        { "key":
            { 
                "valid": true/false,
                "name": name,
                "pug_group": pug_group,
                "server_group": server_group,
                "cache_time": when this item was cached
            }
        }

        """
        self._auth_cache = {}


        # check pug status every 2 seconds. this status includes map vote,
        # ending, etc.
        self._pug_status_timer = PeriodicCallback(self._pug_status_check, 2000)
        self._pug_status_timer.start()

        # check ban expirations. timer is in MS, and we want to check every
        # 10 minutes. so, 10 (min) * 60 (seconds in 1 minute) * 1000 (ms in 1s)
        self._ban_expiration_timer = PeriodicCallback(
                                        self.ban_manager.check_bans,
                                        600000)
        self._ban_expiration_timer.start()

        # loading the pug managers will also load all server managers
        self.__load_pug_managers()

        self.__late_load_servers()

        tornado.web.Application.__init__(self, handlers, **settings)

    def valid_api_key(self, key):
        if key is None:
            return False
            
        if key in self._auth_cache:
            logging.debug("Key %s is in auth cache", key)

            valid = self._auth_cache[key]["valid"] 
            cache_time = self._auth_cache[key]["cache_time"]

            # check if the cache has expired
            # if it has expired, we remove the key from the cache and recache
            if (time.time() - cache_time) > 120:
                logging.debug("Cache for key has expired")
                del self._auth_cache[key]

            else:
                # cache has not expired
                logging.debug("Key is in cache and has not expired. Valid: %s", valid)
                return valid

        user_info = self.db.get_user_info(key)

        logging.debug("User details for key %s: %s", key, user_info)
        if user_info is None:
            self.__cache_client_data(key, user_info)
            raise InvalidKeyException("Invalid API key %s" % (key))
        
        else:
            # cache and return true
            # user_info is currently [(0,1,2)], so we just get the tuple out
            self.__cache_client_data(key, user_info[0])

            return True

    def __cache_client_data(self, key, user_info):
        if user_info is None:
            self._auth_cache[key] = {
                "valid": False,
                "cache_time": time.time(),
            }
        else:
            # user_info = [(name, pug_group, server_group)]
            self._auth_cache[key] = {
                "valid": True,
                "name": user_info[0],
                "pug_group": user_info[1],
                "server_group": user_info[2],
                "cache_time": time.time(),
            }

    def get_server_manager(self, group):
        if group in self._server_managers:
            return self._server_managers[group]

        else:
            logging.debug("Getting server manager for group %d", group)

            new_manager = ServerManager.ServerManager(group, self.db)

            self._server_managers[group] = new_manager

            return new_manager

    def get_pug_manager(self, key):
        if key in self._pug_managers:
            return self._pug_managers[key]

        else:
            # NOTE: If this is being called, the data will ALWAYS be in the cache
            logging.debug("Getting new pug manager for key %s", key)

            client_group = self._auth_cache[key]["server_group"]

            new_manager = PugManager.PugManager(key, self.db, 
                            self.get_server_manager(client_group),
                            self.ban_manager)

            self._pug_managers[key] = new_manager

            return new_manager

    def _pug_status_check(self):
        curr_ctime = time.time()

        for manager in self._pug_managers.values():
            manager.status_check(curr_ctime)

    def __load_pug_managers(self):
        logging.info("Loading pug managers for all users")

        results = self.db.get_user_info() # gets all user info from api keys table

        logging.debug("User info in database: %s", results)

        if results:
            for key_tuple in results:
                # key_tuple in the form (name, pug_group, server_group, key)
                key = key_tuple[3]

                self.__cache_client_data(key, key_tuple[0:3])

                self.get_pug_manager(key_tuple[3])

    def __late_load_servers(self):
        """
        Run a late load for all servers, so listeners are re-established. We
        perform this after loading the pugs and servers themselves so that
        all references (Server <-> Pug) have already been re-established.
        """

        for manager in self._server_managers.values():
            manager.late_load()

    def close(self):
        self._pug_status_timer.stop()

        # flush the managers to the database
        logging.info("Flushing pug managers")
        for manager in self._pug_managers.values():
            manager.flush_all()


        logging.info("Flushing server managers")
        for manager in self._server_managers.values():
            manager.flush_all()

        logging.info("Managers successfully flushed")

if __name__ == "__main__":
    parse_command_line()

    dsn = "dbname=%s user=%s password=%s host=%s port=%s" % (
                settings.db_name, settings.db_user, settings.db_pass, 
                settings.db_host, settings.db_port
            )

    db = psycopg2.pool.SimpleConnectionPool(minconn = 1, maxconn = 1, 
        dsn = dsn)

    dbinterface_cls = get_db_interface("PGSQL")

    dbinterface = dbinterface_cls(db)

    api_server = Application(dbinterface)

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

