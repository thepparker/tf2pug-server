import logging
import json
import time
import hmac
import hashlib
import sys

import tornado.web

from tornado.web import HTTPError

from puglib import Exceptions as PugManagerExceptions, bans
from serverlib import Rcon, Exceptions as ServerManagerExceptions

def compare_digest(a, b):
    if int(''.join([ str(x) for x in sys.version_info[:3] ])) < 277:
        return a == b

    else:
        return hmac.compare_digest(a, b)

# The base handler class sets up properties and useful methods
class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)

        self._player_id = None
        self._player_name = None
        self._pugid = None

        self._request_key = None
        self._request_token = None
        self._request_time = None

    @property
    def manager(self):
        return self.application.get_pug_manager(self.current_user.private_key)

    @property
    def request_key(self):
        if not self._request_key:
            self._request_key = self.get_argument("key")

        return self._request_key

    @property
    def request_token(self):
        if not self._request_token:
            self._request_token = self.get_argument("auth_token")

        return self._request_token

    @property
    def request_time(self):
        if not self._request_time:
            try:
                self._request_time = int(self.get_argument("auth_time"))

            except:
                logging.exception("Exception casting request time")
                raise HTTPError(400)

        return self._request_time

    @property
    def player_id(self):
        if not self._player_id:
            sid = self.get_argument("steamid")

            logging.debug("STEAMID: %s" % sid)
            try:
                self._player_id = long(sid)

            except:
                logging.exception("error casting steamid")
                raise HTTPError(400)

        return self._player_id

    @property
    def player_name(self):
        if not self._player_name:
            self._player_name = self.get_argument("name")

        return self._player_name

    @property
    def pugid(self):
        if not self._pugid:
            pugid = self.get_argument("pugid")
            
            logging.debug("PUG ID: %s" % pugid)

            try:
                self._pugid = long(pugid)

            except:
                logging.exception("error casting pug id")
                raise HTTPError(400)

        return self._pugid


    @property
    def size(self):
        size = self.get_argument("size", 12)
        logging.debug("SIZE: %s" % size)
        try:
            size = int(size)

            return size

        except:
            logging.exception("error casting size")
            raise HTTPError(400)

    @property
    def response_handler(self):
        return self.application.response_handler

    def get_current_user(self):
        return self.application.get_user_info(self.request_key)

    def validate_request(self):
        """
        Validates whether the request is allowed or not based on the supplied
        authentication parameters. We use a simple hash-based approach to
        authentication. The user uses a secret key, known only by them and us,
        to hash a string, creating the auth_token. We then perform the same
        hashing on our side. If the tokens match, the user is authenticated.

        The hashed string is a HMAC digest of the following encoding:
        $PUBLIC_KEY + $TIMESTAMP

        The hashing algorithm used is SHA256. The HMAC key is the user's
        private key.
        """

        logging.debug("Validating request. Time: %s, public key: %s",
                      self.request_time, self.request_key)

        # the first thing we should do is check the timestamp to prevent replay
        # attacks. we also check if a user matching the public key even exists
        if (time.time() - self.request_time > 10) or self.current_user is None:
            logging.info("Request from %s is outdated, or no user info found",
                         self.request_key)

            raise HTTPError(401)

        # have user details. now we can compute what the request_token SHOULD
        # be
        to_encrypt = self.request_key + str(self.request_time)
        logging.debug("Encrypting %s with private key %s", 
                      to_encrypt, self.current_user.private_key)

        h = hmac.new(self.current_user.private_key, to_encrypt, hashlib.sha256)

        token = h.hexdigest()
        if compare_digest(token, self.request_token):
            # user is authenticated
            logging.info("Request from %s (%s) successfully authenticated", 
                         self.current_user.name, self.current_user.public_key)

        else:
            logging.debug("Digests did not match. User digest: %s - OURS: %s",
                          self.request_token, token)
            raise HTTPError(401)

# returns a list of pugs and their status
class PugListHandler(BaseHandler):
    # A simple GET is required for a pug listing
    def get(self):
        self.validate_request()

        self.write(self.response_handler.pug_listing(self.manager.get_pugs()))

class PugStatusHandler(BaseHandler):
    # A GET which retrieves the status of the given pug id
    # Parameters:
    # @pugid The ID to get status for
    def get(self):
        self.validate_request()

        # the response handler will automatically handle invalid pug ids by
        # sending an invalidpug response code
        self.write(self.response_handler.pug_status(self.manager.get_pug_by_id(self.pugid)))

# adds a player to a pug
class PugAddHandler(BaseHandler):
    # To add a player to a PUG, there must be a POST
    #
    # Parameters are as follows:
    # @steamid The SteamID to add
    # @name The name of the player being added
    # @pugid The pug ID to add the player to
    def post(self):
        self.validate_request()

        pug_id = self.pugid

        # the add_player method returns the pug the player was added to
        try:
            pug = self.manager.add_player(self.player_id, self.player_name, pug_id)
            # send the updated status of this pug (i.e which players are in it now)

            self.write(self.response_handler.player_added(pug))

        except PugManagerExceptions.PlayerBannedException:
            ban = self.application.ban_manager.get_player_ban(self.player_id)
            self.write(self.response_handler.player_banned(ban.reason))

        except PugManagerExceptions.PlayerRestrictedException:
            self.write(self.response_handler.player_restricted())

        except PugManagerExceptions.PlayerInPugException:
            self.write(self.response_handler.player_in_pug())

        except PugManagerExceptions.InvalidPugException:
            self.write(self.response_handler.invalid_pug())

        except PugManagerExceptions.PugFullException:
            self.write(self.response_handler.pug_full())

        except:
            logging.exception("Unknown exception occurred when adding player to a pug")
            raise HTTPError(500)

# removes a player from a pug
class PugRemoveHandler(BaseHandler):
    # To remove a player from a PUG, a POST is required
    #
    # The only required parameter is the player's steamid
    # @steamid The SteamID to remove
    def post(self):
        self.validate_request()

        try:
            pug = self.manager.remove_player(self.player_id)

            self.write(self.response_handler.player_removed(pug))

        except PugManagerExceptions.PlayerNotInPugException:
            # player not in a pug
            self.write(self.response_handler.player_not_in_pug())

        except PugManagerExceptions.PugEmptyEndException:
            self.write(self.response_handler.empty_pug_ended())

        except:
            logging.exception("Unknown exception when removing player from a pug")
            raise HTTPError(500)

# Creates a new pug. Only called to explicitly create a new pug. Normally pugs
# are automatically created behind the scenes by the pug manager when a pug
# fills and more players want to join.
class PugCreateHandler(BaseHandler):
    """
    To create a new pug, a POST is required.

    There are a number of parameters that can be specified for creating a
    pug. The parameters are as follows, and are required unless marked
    optional:
    
    @steamid The SteamID of the player creating the pug
    @name The name of the player creating the pug

    @map (optional) The map the pug is locked to

    @size (optional) The size of the pug (i.e the number of players that can
                     join). Defaults to 12, but can be any supported size*.
                     * See the PugManager class for supported sizes.

    @custom_id (optional) An optional ID which the client can use to identify
                          pugs

    @restriction (optional) An optional int to restrict the rating of players
                            who can join the pug. +100 means >= 100 rating,
                            -100 means < 100 rating.
    """
    def post(self):
        self.validate_request()

        pug_map = self.get_argument("map", None)
        size = self.size
        custom_id = self.get_argument("custom_id", None)
        restriction = self.get_argument("restriction", None)

        try:
            pug = self.manager.create_pug(self.player_id, self.player_name,
                                          size = size, pug_map = pug_map, 
                                          custom_id = custom_id, 
                                          restriction = restriction)

            # send the status of the new pug
            self.write(self.response_handler.pug_created(pug))

        except PugManagerExceptions.PlayerInPugException:
            self.write(self.response_handler.player_in_pug())

        except PugManagerExceptions.InvalidMapException:
            self.write(self.response_handler.invalid_map())

        except PugManagerExceptions.NoAvailableServersException:
            self.write(self.response_handler.no_available_servers())

        except Rcon.RconConnectionError:
            self.write(self.response_handler.server_connection_error())

        except:
            logging.exception("Unknown exception occurred during pug creation")
            raise HTTPError(500)

class PugEndHandler(BaseHandler):
    # To end a pug, a POST is required
    #
    # The only parameter required is the pug id
    # @pugid The ID of the pug to end
    # @steamid The user trying to end the pug?
    def post(self):
        self.validate_request()

        pug_id = self.pugid

        try:
            self.manager.end_pug(pug_id)

            self.write(self.response_handler.pug_ended(pug_id))

        except PugManagerExceptions.InvalidPugException:
            self.write(self.response_handler.invalid_pug())

        except:
            logging.exception("Unknown exception when ending a pug")
            raise HTTPError(500)

# Gets a the list of players for the given pugid
class PugPlayerListHandler(BaseHandler):
    # A GET is required to get the player list
    #
    # The only required parameter is the pug id
    # @pugid The pug ID to get a player list for
    def get(self):
        self.validate_request()

        pug_id = self.pugid

        self.write(self.response_handler.player_list(self.manager.get_pug_by_id(pug_id)))

class PugMapVoteHandler(BaseHandler):
    # A POST is used to set a player's map vote
    #
    # Required parameters are player id and the map being voted for.
    #
    # @steamid The player's ID who is voting
    # @map The map name being voted for
    def post(self):
        self.validate_request()

        pmap = self.get_argument("map")

        try:
            pug = self.manager.vote_map(self.player_id, pmap)

            self.write(self.response_handler.pug_vote_added(self.player_id, 
                                                            pug))

        except PugManagerExceptions.PlayerNotInPugException:
            self.write(self.response_handler.player_not_in_pug())

        except PugManagerExceptions.NoMapVoteException:
            self.write(self.response_handler.pug_no_map_vote())

        except PugManagerExceptions.InvalidMapException:
            self.write(self.response_handler.invalid_map())

        except:
            logging.exception("Unknown exception occured during map vote")
            raise HTTPError(500)

class PugForceMapHandler(BaseHandler):
    # A POST is used to force the map
    #
    # Required parameters are the pug id and the map to force it to
    #
    # @pugid The ID of the pug
    # @map The name of the map
    def post(self):
        self.validate_request()

        fmap = self.get_argument("map", None, False)
        pug_id = self.pugid

        try:
            pug = self.manager.force_map(pug_id, fmap)

            self.write(self.response_handler.pug_map_forced(pug))
        
        except PugManagerExceptions.InvalidPugException:
            self.write(self.response_handler.invalid_pug())

        except PugManagerExceptions.ForceMapException:
            self.write(self.response_handler.pug_map_not_forced())

        except PugManagerExceptions.InvalidMapException:
            self.write(self.response_handler.invalid_map())

        except:
            logging.exception("Exception occured when forcing map")
            raise HTTPError(500)

class BanAddHandler(BaseHandler):
    """
    A POST request

    Attempts to add a ban to the database with the given JSON packet.

    :param data This should be the only argument (aside from key). It should be
                a JSON encoded string with the format dicated in bans.md
    """
    def post(self):
        self.validate_request()

        # Note: tornado will raise its own exception if using get_argument
        # without a default, so if we get data, we know it's something
        data = self.get_argument("data")
        try:
            data = json.loads(data)
        except:
            raise HTTPError(400)

        try:
            ban = self.application.ban_manager.add_ban(data)
            self.write(self.response_handler.ban_added(ban))

        except (bans.BanAddException, AssertionError):
            self.write(self.response_handler.invalid_ban_data())

        except:
            logging.exception("Exception occurred adding ban")
            raise HTTPError(500)

class BanRemoveHandler(BaseHandler):
    """
    A POST request

    Attempt to remove a ban for the specified player id

    :param steamid The 64bit SteamID to remove the ban for
    """
    def post(self):
        self.validate_request()

        try:
            self.application.ban_manager.remove_ban(self.player_id)

            self.write(self.response_handler.ban_removed())

        except bans.NoBanFoundException:
            self.write(self.response_handler.no_ban_found())

        except:
            logging.exception("Exception occurred deleting ban")
            raise HTTPError(500)

class BanListHandler(BaseHandler):
    """
    A GET request to get a list of bans in the ban manager

    :param ids (optional) A JSON encoded list of 64bit steamids. Note that
                          this is a list of banned players, not a list of
                          banners.

    :param expired (optional) Whether or not to include expired bans. 
                              A bool (1/0 or 'true'/'false').
    """
    def get(self):
        self.validate_request()

        cids = self.get_argument("ids", None)
        expired = self.get_argument("expired", False)
        try:
            if cids is not None:
                cids = json.loads(cids)

            def string2bool(v):
                if v.lower() == "false" or v == "0":
                    return False
                elif v.lower() == "true" or v == "1":
                    return True
                else:
                    return bool(v)

            expired = string2bool(expired)

        except:
            raise HTTPError(400)


        try:
            if cids is None:
                self.write(self.response_handler.ban_list(
                        self.application.db.get_bans(include_expired = expired)
                    ))
            else:
                self.write(self.response_handler.ban_list(
                        self.application.db.get_bans(cids = cids, 
                                                     include_expired = expired)
                    ))

        except:
            logging.exception("Exception getting ban list")
            raise HTTPError(500)



class StatHandler(BaseHandler):
    """
    A GET request to retrieve stats for an individual player, specific
    players, or all players.

    :param ids (optional) A JSON encoded LIST of ids to get stats for
    """
    def get(self, slug):
        #self.validate_request()

        routes = ("All", "Select", "Top")
        if slug not in routes:
            raise HTTPError(404)

        cids = self.get_argument("ids", None)
        if slug == "All":
            self.write(self.response_handler.player_stats(
                        self.application.db.get_player_stats()
                    ))

        elif slug == "Select" and cids is not None:
            try:
                cids = json.loads(cids)
            except:
                raise HTTPError(400)

            # we have cids to get stats for
            self.write(self.response_handler.player_stats(
                        self.application.db.get_player_stats(cids)
                    ))

        elif slug == "Top":
            stat = self.get_argument("stat", "rating")
            limit = self.get_argument("limit", 50)
            
            try:
                limit = int(limit)
            except:
                raise HTTPError(400)

            self.write(self.response_handler.top_player_stats(
                        self.application.db.get_top_stats(
                            stat = stat, limit = limit)
                    ))
