import json
class BaseJsonInterface(object):
    """ 
    Takes a Pug object and converts it into a JSON object
    :param obj The pug object

    :return JSON A JSON (string) object
    """
    def dumps(self, obj):
        return json.dumps(obj)

    """
    Takes a JSON object and converts it to a Pug object

    :param data The JSON object string

    :return Pug A Pug object
    """
    def loads(self, data):
        return json.loads(data)

class BaseDatabaseInterface(object):
    """
    A base database interface class. This class is used to interface with your
    database of choice, and must implement all methods, which are used by the
    application.

    An implementation for PostgreSQL is provided.
    """
    def __init__(self, db):
        self.db = db

    def get_user_info(self, api_key = None):
        """
        Gets all user info from the auth table. If an api key is specified, 
        will only get data pertaining to that key. If no api key is specified, 
        will get all user info. Independent of game.

        :param api_key (optional) The API key to get user info for

        :return A list of tuples, with each tuple being a row in the table
        """
        raise NotImplementedError("This must be implemented")

    def get_player_stats(self, ids = None, async = False):
        """
        Gets stat info pertaining to the given list of 64bit SteamIDs. If no
        list is given, gets all stat data in the database.

        :param ids (optional) The list of 64bit IDs to get data for
        :param async (optional) Whether to return a `tornado.gen.YieldPoint` or
                                equivalent Future to run in a coroutine, or to 
                                perform the query synchronously

        :return A dictionary of stats with respect to each individual ID
        """
        raise NotImplementedError("This must be implemented")

    def get_top_players(self, stat, limit):
        """
        Gets the top `limit` players for the given stat column.

        :param stat The stat column to filter on
        :param limit The maximum number of players to get
        :param async (optional) Whether to return a `tornado.gen.YieldPoint` or
                                equivalent Future to run in a coroutine, or to 
                                perform the query synchronously

        :return A list of 64bit SteamIDs in descending order based on stat
        """
        raise NotImplementedError("Not implemented")

    def flush_player_stats(self, player_stats):
        """
        Updates stats from a pug. The dict given is used to update all values
        for the user. 

        :param player_stats A dict of all player stats, with the keys 64bit
                            SteamIDs
        """
        raise NotImplementedError("This must be implemented")

    def get_pugs(self, api_key, jsoninterface, include_finished = False):
        """
        Gets pug data pertaining to a specified API key, and returns it as a 
        list of JSON objects, which can be parsed through the JSON interface 
        provided by the caller to get pug objects. Pug management methods are
        independent of game, and simply take or return json objects.

        :param api_key The api key to get pugs for
        :param jsoninterface The JSON interface to be used to convert from JSON
        :param include_finished Whether or not to include games that are over
                                i.e in the "GAME_OVER" state

        :return List of Pug objects
        """
        raise NotImplementedError("This must be implemented")

    def flush_pug(self, api_key, jsoninterface, pug):
        """
        Flushes a JSONised pug to the database. This method is only used for
        non-new pugs, which already have an ID.

        :param api_key The API key the pug is under (not necessary?)
        :param jsoninterface The JSON interface to convert to JSON
        :param pug A Pug object
        """
        raise NotImplementedError("This must be implemented")

    def get_servers(self, group):
        """
        Gets all servers pertaining to the specified group. Multiple pug 
        managers, or clients, can be part of the same group. Returns a list of
        dictionaries, with each list item being a server table row.

        :param group The group to get servers for.

        :return List of dictionaries for each server
        """
        raise NotImplementedError("This must be implemented")
    
    def flush_server(self, server):
        """
        Flushes a server to the database

        :param server The server to flush
        """
        raise NotImplementedError("This must be implemented")

    def get_bans(self, cids = None, include_expired = False):
        """
        Gets player bans. If cid is specified, gets bans only for that player.

        :param cids (optional) A list of player 64bit SteamIDs
        :param include_expired (optional) Whether to get expired bans as well

        :return List of dicts
        """
        raise NotImplementedError("Getting bans is not implemented")

    def flush_ban(self, ban):
        """
        Flushes a ban object to the database

        :param ban A ban object
        """
        raise NotImplementedError("Flushing bans is not implemented")

class BaseLogInterface(object):
    """
    This interface parses log data from the game server, and calls the appropriate
    server and pug methods. Note that if you wish, you could implement stat parsing
    in this class, and pass the database interface in for db interactions
    """
    def __init__(self, server):
        self.server = server

    def parse(self, data):
        raise NotImplementedError("Must implement this method")

    def start_game(self, start_time = 5):
        #self.server.start_game(start_time)
        self.pug.begin_game()

    def restart_game(self):
        # just start the game again?
        self.start_game()

    def end_game(self):
        self.pug.end_game()

    def update_score(self, team, score):
        self.pug.update_score(team, score)

    def print_teams(self):
        if not self.pug.teams_done:
            return
            
        self.server.print_teams()

    def kick_player(self, sid, reason):
        self.server.kick_player(sid, reason)

    @property
    def pug(self):
        return self.server.pug
