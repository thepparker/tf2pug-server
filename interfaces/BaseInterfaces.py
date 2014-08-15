import json
class BaseJsonInterface(object):
    """ 
    Takes a Pug object and converts it into a JSON object
    @param obj The pug object

    @return JSON A JSON (string) object
    """
    def dumps(self, obj):
        return json.dumps(obj)

    """
    Takes a JSON object and converts it to a Pug object

    @param data The JSON object string

    @return Pug A Pug object
    """
    def loads(self, data):
        return json.loads(data)

class BaseDatabaseInterface(object):
    """
    A base database interface class. This class is used to interface with your
    database of choice, and must implement all methods, which are used by the
    application.

    An implementation for PostgreSQL is provided
    """
    def __init__(self, db):
        self.db = db

    """
    Gets all user info from the auth table. If an api key is specified, will
    only get data pertaining to that key. If no api key is specified, will get
    all user info. Independent of game.

    @param api_key (optional) The API key to get user info for

    @return A list of tuples, with each tuple being a row in the api_keys table
    """
    def get_user_info(self, api_key = None):
        raise NotImplementedError("This must be implemented")

    """
    Gets stat info pertaining to the given list of 64bit SteamIDs. 

    @param ids The list of 64bit IDs to get data for

    @return A dictionary of stats with respect to each individual ID
    """
    def get_player_stats(self, ids):
        raise NotImplementedError("This must be implemented")

    """
    Updates stats from a pug. The dict given is used to update all values
    for the user. 

    @param player_stats A dict of all player stats, with the keys 64bit
                        SteamIDs
    """
    def flush_player_stats(self, player_stats):
        raise NotImplementedError("This must be implemented")

    """
    Updates player ratings.
    """
    def flush_updated_ratings(self, ratings_tuple):
        raise NotImplementedError("This must be implemented")

    """
    Gets pug data pertaining to a specified API key, and returns it as a list
    of JSON objects, which can be parsed through the JSON interface by the
    caller to get pug objects. Pug management methods are independent of game,
    and simply take or return json objects.

    @param api_key The api key to get pugs for
    @param jsoninterface The JSON interface to be used to convert from JSON
    @param include_finished Whether or not to include games that are finished
                            i.e in the "GAME_OVER" state

    @return List of Pug objects
    """
    def get_pugs(self, api_key, jsoninterface, include_finished = False):
        raise NotImplementedError("This must be implemented")

    """
    Flushes a JSONised pug to the database. This method is only used for 
    non-new pugs, which already have an ID.

    @param api_key The API key the pug is under (not necessary?)
    @param jsoninterface The JSON interface to convert to JSON
    @param pug A Pug object
    """
    def flush_pug(self, api_key, jsoninterface, pug):
        raise NotImplementedError("This must be implemented")

    """
    Gets all servers pertaining to the specified group. Multiple pug managers, 
    or clients, can be part of the same group. Returns a list of dictionaries, 
    which each list item being a server table row.

    @param group The group to get servers for.

    @return List of dictionaries for each server
    """
    def get_servers(self, group):
        raise NotImplementedError("This must be implemented")

    """
    Flushes a server to the database

    @param server The server to flush
    """
    def flush_server(self, server):
        raise NotImplementedError("This must be implemented")

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

    def start_game(self, start_time = 20):
        self.server.start_game(start_time)
        self.pug.begin_game()

    def restart_game(self):
        # just start the game again?
        self.start_game()

    def end_game(self):
        self.pug.end_game()

        self.server.reset()

    def update_score(self, team, score):
        self.pug.update_score(team, score)

    def print_teams(self):
        self.server.print_teams()

    def kick_player(self, sid, reason):
        self.server.kick_player(sid, reason)

    @property
    def pug(self):
        return self.server.pug
