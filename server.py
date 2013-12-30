#!/usr/bin/env python


import logging
import tornado.web
import tornado.ioloop
import puglib

from tornado.options import define, options, parse_command_line

define("port", default = 51515, help = "take a guess motherfucker", type = int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            # pug creation and player adding/removing
            (r"/ITF2Pug/List/", PugListHandler),
            (r"/ITF2Pug/Add/", PugAddHandler),
            (r"/ITF2Pug/Remove/", PugRemoveHandler),
            (r"/ITF2Pug/Create/", PugCreateHandler),
            (r"/ITF2Pug/End/", PugEndHandler),

            # pug player listings
            ("r/ITF2Pug/Player/List", PugPlayerListHandler),
        ]

        settings = {
            debug = True,
        }

        self.db = None

        self.pug_manager = puglib.PugManager.PugManager(self.db)

        tornado.web.Application.__init__(self, handlers, **settings)

    def valid_api_key(self, key):
        return True

# The base handler class sets up properties and useful methods
class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)

        self.validate_api_key()

    @property
    def manager(self):
        return self.application.pug_manager

    @property
    def request_key(self):
        return self.get_argument("key", None, False)

    @property
    def player(self):
        return self.get_argument("steamid", None, False)

    @property
    def player_name(self):
        return self.get_argument("name", None, False)

    def validate_api_key(self):
        if not self.application.validate_api_key(self.request_key):
            raise tornado.web.HTTPError(403)

# returns a list of pugs and their status
class PugListHandler(BaseHandler):
    # A simple GET is required for a pug listing
    def get(self):
        self.write(self.manager.get_pug_listing())

# adds a player to a pug
class PugAddHandler(BaseHandler):
    # To add a player to a PUG, there must be a PUT
    #
    # Parameters are as follows:
    # @steamid The SteamID to add
    # @name The name of the player being added
    # @pugid (optional) The pug ID to add the player to. If no ID is specified,
    #                   the player is added to the first pug with space.
    # @size (optional) The size of the pug to add the player to. eg, size=12
    #                  to only add to 6v6 pugs.
    def put(self):


        if not self.player or not self.player_name:
            raise HTTPError(500)

        pug_id = self.get_argument("pugid", None, False)
        size = self.get_argument("size", 12, False)

        # the add_player method returns the id of the pug the player was
        # added to
        added_id = self.manager.add_player(self.player, self.player_name, pug_id = pug_id, size = size)

        # send the updated status of this pug (i.e which players are in it now)
        self.write(self.manager.get_pug_status(added_id))

# removes a player from a pug
class PugRemoveHandler(BaseHandler):
    # To remove a player from a PUG, a DELETE is required
    #
    # The only required parameter is the player's steamid
    # @steamid The SteamID to remove
    def delete(self):

        if not self.player:
            raise HTTPError(500)

        removed_id = self.manager.remove_player(self.player)

        # send the updated status of this pug
        self.write(self.manager.get_pug_status(removed_id))

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
        if not self.player or not self.player_name:
            raise HTTPError(500)

        pug_map = self.get_argument("map", None, False)
        size = self.get_argument("size", 12, False)

        new_id = self.manager.create_pug(self.player, self.player_name,
                                         size, pug_map)

        # send the status of the new pug
        self.write(self.manager.get_pug_status(new_id))

class PugEndHandler(BaseHandler):
    # To end a pug, a DELETE is required
    #
    # The only parameter required is the pug id
    # @pugid The ID of the pug to end
    def delete(self):
        pug_id = self.get_argument("pugid", None, False)
        if not pug_id:
            raise HTTPError(500)

        self.manager.end_pug(pug_id)

        self.write({ "result": 0 })

if __name__ == "__main__":
    parse_command_line()

    api_server = Application()
    api_server.listen(options.port)

    tornado.ioloop.IOLoop.instance().start()


