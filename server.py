#!/usr/bin/env python


import logging
import tornado.web
import tornado.ioloop

from puglib import PugManager
from handlers import ResponseHandler

from tornado.web import HTTPError

from tornado.options import define, options, parse_command_line

define("ip", default = "0.0.0.0", help = "The IP to listen on", type = str)
define("port", default = 51515, help = "take a guess motherfucker", type = int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            # pug creation and management
            (r"/ITF2Pug/List/", PugListHandler),
            (r"/ITF2Pug/Status/", PugStatusHandler),
            (r"/ITF2Pug/Create/", PugCreateHandler),
            (r"/ITF2Pug/End/", PugEndHandler),

            # pug player adding/removing/listing
            (r"/ITF2Pug/Player/Add/", PugAddHandler),
            (r"/ITF2Pug/Player/Remove/", PugRemoveHandler),
            (r"/ITF2Pug/Player/List/", PugPlayerListHandler),

            # map voting
            (r"/ITF2Pug/Vote/Add/", PugMapVoteHandler),

        ]

        settings = {
            "debug": True,
        }

        self.db = None
        self.response_handler = ResponseHandler.ResponseHandler()

        self.pug_manager = PugManager.PugManager(self.db)

        tornado.web.Application.__init__(self, handlers, **settings)

    def valid_api_key(self, key):
        return key == "123abc"

# The base handler class sets up properties and useful methods
class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)

    @property
    def manager(self):
        return self.application.pug_manager

    @property
    def request_key(self):
        return self.get_argument("key", None, False)

    @property
    def player_id(self):
        sid = self.get_argument("steamid", None, False)

        if sid is not None:
            try:
                sid = long(sid)

                return sid

            except ValueError:
                raise HTTPError(400)


        return sid

    @property
    def player_name(self):
        return self.get_argument("name", None, False)

    @property
    def pugid(self):
        pugid = self.get_argument("pugid", None, False)
        
        if pugid is not None:
            try:
                pugid = int(pugid)

                return pugid

            except ValueError:
                raise HTTPError(400)

        return pugid

    @property
    def response_handler(self):
        return self.application.response_handler

    def validate_api_key(self):
        if not self.application.valid_api_key(self.request_key):
            raise HTTPError(401)

# returns a list of pugs and their status
class PugListHandler(BaseHandler):
    # A simple GET is required for a pug listing
    def get(self):
        self.validate_api_key()

        self.write(self.response_handler.pug_listing(self.manager.get_pugs()))

class PugStatusHandler(BaseHandler):
    # A GET which retrieves the status of the given pug id
    # Parameters:
    # @pugid The ID to get status for
    def get(self):
        self.validate_api_key()

        self.write(self.response_handler.pug_status(self.manager.get_pug_by_id(self.pugid)))

# adds a player to a pug
class PugAddHandler(BaseHandler):
    # To add a player to a PUG, there must be a PUT
    #
    # Parameters are as follows:
    # @steamid The SteamID to add
    # @name The name of the player being added
    # @pugid (optional) The pug ID to add the player to.
    # @size (optional) The size of the pug to add the player to. eg, size=12
    #                  to only add to 6v6 pugs.
    def post(self):
        self.validate_api_key()

        if self.player_id is None or self.player_name is None:
            raise HTTPError(400)

        pug_id = self.pugid
        size = self.get_argument("size", 12, False)

        # the add_player method returns the pug the player was added to
        try:
            pug = self.manager.add_player(self.player_id, self.player_name, pug_id = pug_id, size = size)
            # send the updated status of this pug (i.e which players are in it now)

            self.write(self.response_handler.player_added(pug))

        except PugManager.PlayerInPugException:
            self.write(self.response_handler.player_in_pug(self.manager.get_player_pug(self.player_id)))

        except PugManager.InvalidPugException:
            self.write(self.response_handler.invalid_pug())

        except PugManager.PugFullException:
            self.write(self.response_handler.pug_full(self.manager.get_pug_by_id(pug_id)))

        except:
            logging.exception("Unknown exception occurred when adding player to a pug")

# removes a player from a pug
class PugRemoveHandler(BaseHandler):
    # To remove a player from a PUG, a DELETE is required
    #
    # The only required parameter is the player's steamid
    # @steamid The SteamID to remove
    def post(self):
        self.validate_api_key()

        if not self.player_id:
            raise HTTPError(400)

        try:
            pug = self.manager.remove_player(self.player_id)

            self.write(self.response_handler.player_removed(pug))

        except PugManager.PlayerNotInPugException:
            # player not in the given pug, simple response
            self.write(self.response_handler.player_not_in_pug())

        except PugManager.PugEmptyEndException:
            self.write(self.response_handler.empty_pug_ended())

        except:
            logging.exception("Unknown exception when removing player from a pug")

# Creates a new pug. Only called to explicitly create a new pug. Normally pugs
# are automatically created behind the scenes by the pug manager when a pug
# fills and more players want to join.
class PugCreateHandler(BaseHandler):
    # To create a new pug, a POST is required
    #
    # There are a number of parameters that can be specified for creating a
    # pug. The parameters are as follows, and are required unless marked
    # optional:
    #
    # @steamid The SteamID of the player creating the pug
    # @name The name of the player creating the pug
    # @map (optional) The map the pug is locked to
    # @size (optional) The size of the pug (i.e the number of players that can
    #                  join). Defaults to 12, but can be any supported size*.
    #                  * See the PugManager class for supported sizes.
    def post(self):
        self.validate_api_key()

        if not self.player_id or not self.player_name:
            raise HTTPError(400)

        pug_map = self.get_argument("map", None, False)
        size = self.get_argument("size", 12, False)

        try:
            pug = self.manager.create_pug(self.player_id, self.player_name,
                                          size, pug_map)

            # send the status of the new pug
            self.write(self.response_handler.pug_created(pug))

        except PugManager.PlayerInPugException:
            self.write(self.response_handler.player_in_pug(self.manager.get_player_pug(self.player_id)))

class PugEndHandler(BaseHandler):
    # To end a pug, a DELETE is required
    #
    # The only parameter required is the pug id
    # @pugid The ID of the pug to end
    def delete(self):
        self.validate_api_key()

        pug_id = self.pugid
        if not pug_id:
            raise HTTPError(400)

        try:
            self.manager.end_pug(pug_id)

            self.write(self.response_handler.pug_ended(pug_id))

        except PugManager.NonExistantPugException:
            self.write(self.response_handler.invalid_pug())

# Gets a the list of players for the given pugid
class PugPlayerListHandler(BaseHandler):
    # A GET is required to get the player list
    #
    # The only required parameter is the pug id
    # @pugid The pug ID to get a player list for
    def get(self):
        self.validate_api_key()

        pug_id = self.pugid
        if pug_id is None:
            raise HTTPError(400)

        self.write(self.response_handler.player_list(self.manager.get_pug_by_id(pug_id)))

class PugMapVoteHandler(BaseHandler):
    # A POST is used to set a player's map vote
    #
    # Required parameters are player id and the map being voted for.
    #
    # @steamid The player's ID who is voting
    # @map The map name being voted for
    def post(self):
        self.validate_api_key()

        pmap = self.get_argument("map", None, False)
        if self.player_id is None or pmap is None:
            raise HTTPError(400)

        pug = self.manager.vote_map(self.player_id, pmap) 

        self.write(self.manager.get_vote_status(pug))


if __name__ == "__main__":
    parse_command_line()

    api_server = Application()
    api_server.listen(options.port, options.ip)

    logging.info("TF2Pug API Server listening on %s:%d", options.ip, options.port)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt. Exiting")


