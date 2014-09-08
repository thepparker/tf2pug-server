#!/usr/bin/env python

import logging
import sys
import time

import settings

import tornado.web
import tornado.ioloop

import psycopg2
import psycopg2.pool

import momoko

from puglib import PugManager, bans
from handlers import ResponseHandler, WebHandler
from serverlib import ServerManager

from interfaces import get_db_interface

from tornado.options import define, options, parse_command_line
from tornado.ioloop import PeriodicCallback

# allow command line overriding of these options
define("ip", default = settings.listen_ip, help = "The IP to listen on", type = str)
define("port", default = settings.listen_port, help = "The port to listen on", type = int)

class APIUser(object):
    def __init__(self, name, pug_group, server_group, private_key, public_key):
        self.name = name
        self.pug_group = pug_group
        self.server_group = server_group
        self.private_key = private_key
        self.public_key = public_key

        self.cache_time = time.time()

class UserContainer(object):
    def __init__(self):
        self.users = []

    def __contains__(self, user):
        if not isinstance(user, APIUser):
            raise TypeError("Invalid user type")

        for u in self.users:
            if u == user:
                return True

    def add_user(self, user_info):
        #user_info = (name, pug_group, server_group, private_key, public_key)
        u = APIUser(user_info[0], user_info[1], user_info[2], user_info[3],
                    user_info[4])

        self.users.append(u)

        return u

    def get_user_by_pub_key(self, key):
        self._clear_cache()

        for u in self.users:
            if u.public_key == key:
                return u

        return None

    def get_user_by_priv_key(self, key):
        self._clear_cache()

        for u in self.users:
            if u.private_key == key:
                return u

        return None

    def _clear_cache(self):
        # remove all items older than 120 seconds. we do this before every
        # fetch

        self.users[:] = [ x for x in self.users if time.time() < x.cache_time + 120 ]


class Application(tornado.web.Application):
    def __init__(self, db):
        # init tornado specific settings first
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
            (r"/ITF2Pug/Stat/(.*)/", WebHandler.StatHandler),
        ]

        settings = {
            "debug": True,
        }

        tornado.web.Application.__init__(self, handlers, **settings)

        # -----------------
        self.db = db
        
        self.response_handler = ResponseHandler.ResponseHandler()
        
        # pug managers are stored per private key (will eventually be 
        # pug_group)
        self._pug_managers = {}

        # server managers are per server group. each server group can have
        # multiple pug managers attached to it
        self._server_managers = {}

        self.ban_manager = bans.BanManager(db) 

        self._auth_cache = UserContainer()

        # check pug status every 2 seconds. this status includes map vote,
        # ending, etc.
        self._pug_status_timer = PeriodicCallback(self._pug_status_check, 2000)
        self._pug_status_timer.start()

        # check ban expirations. timer is in MS, and we want to check every
        # 10 minutes. so, 10 (min) * 60 (seconds in 1 minute) * 1000 (ms in 1s)
        self._ban_expiration_timer = PeriodicCallback(
                                        self.ban_manager.check_bans,
                                        1000)
        self._ban_expiration_timer.start()

        # loading the pug managers will also load all server managers
        self.__load_pug_managers()

        self.__late_load_servers()

    def get_server_manager(self, server_group):
        if server_group in self._server_managers:
            return self._server_managers[server_group]

        else:
            logging.debug("Getting server manager for group %d", server_group)

            new_manager = ServerManager.ServerManager(server_group, self.db)

            self._server_managers[server_group] = new_manager

            return new_manager

    def get_pug_manager(self, private_key):
        if private_key in self._pug_managers:
            return self._pug_managers[private_key]

        else:
            # NOTE: If this is being called, the data will ALWAYS be in the cache
            logging.debug("Getting new pug manager for private key %s", 
                          private_key)

            user = self._auth_cache.get_user_by_priv_key(private_key)

            new_manager = PugManager.PugManager(private_key, self.db, 
                            self.get_server_manager(user.server_group),
                            self.ban_manager)

            self._pug_managers[private_key] = new_manager

            return new_manager

    def _pug_status_check(self):
        curr_ctime = time.time()

        for manager in self._pug_managers.values():
            manager.status_check(curr_ctime)

    def get_user_info(self, public_key):
        user = self._auth_cache.get_user_by_pub_key(public_key)

        if user is None:
            logging.info("User with public key %s is not cached. Refreshing", 
                         public_key)
            user_info = self.db.get_user_info(public_key)

            if user_info:
                logging.info("Successfully obtained user %s info for %s", 
                             user_info, public_key)
                return self._auth_cache.add_user(user_info[0])
            
            else:
                return None

        else:
            return user

    def __load_pug_managers(self):
        logging.info("Loading pug managers for all users")

        results = self.db.get_user_info() # gets all user info from api keys table

        logging.debug("User info in database: %s", results)

        if results:
            for key_tuple in results:
                user = self._auth_cache.add_user(key_tuple)
                self.get_pug_manager(user.private_key)

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

    # a synchronous pool for database queries that should be performed 
    # synchronously
    db = psycopg2.pool.SimpleConnectionPool(minconn = 1, maxconn = 1, 
        dsn = dsn)

    # asynchronous connection pool for async queries. momoko utilizes gen to
    # perform queries asynchronously using tornado
    async_db = momoko.Pool(dsn = dsn, size = 1, max_size = 2, 
        raise_connect_errors = False)

    dbinterface_cls = get_db_interface("PGSQL")

    dbinterface = dbinterface_cls(db, async_db)

    for statcol in settings.indexed_stats:
        dbinterface.add_stat_index(statcol)

    api_server = Application(dbinterface)

    api_server.listen(options.port, options.ip)

    logging.info("TF2Pug API Server listening on %s:%d", options.ip, options.port)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except:
        logging.info("Shutting the server down...")

        api_server.close()
        db.closeall()
        async_db.close()

        tornado.ioloop.IOLoop.instance().stop()
        
        sys.exit(0)

