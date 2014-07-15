"""
A base database interface class. This class is used to interface with your
database of choice, and must implement all methods, which are used by the
application.

An implementation for PostgreSQL is provided in PSQLDatabaseInterface.py
"""

class BaseDatabaseInterface(object):
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
    Gets TF2 stat info pertaining to the given list of 64bit SteamIDs. 
    Such info includes games since playing medic, total number of games played,
    and the player rating.

    @param ids The list of 64bit IDs to get data for

    @return A dictionary of stats with respect to each individual ID
    """
    def get_tf_player_stats(self, ids):
        raise NotImplementedError("This must be implemented")

    """
    Updates medic stats from a pug. The list of medics given is the medics
    playing medic for the pug, non medics is the list of players in the pug who
    are not medics.

    @param medics List of 64bit SteamIDs who are playing medic
    @param nonmedics List of 64bit SteamIDS who are not playing medic
    """
    def flush_tf_pug_med_stats(self, medics, nonmedics):
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
    @param pid The ID of the pug
    @param pug A Pug object
    """
    def flush_pug(self, api_key, jsoninterface, pid, pug):
        raise NotImplementedError("This must be implemented")

    """
    Flushes a new pug to the database, returning the ID. Maintains the index
    table.

    @param api_key The API key the pug is under
    @param jsoninterface The JSON interface to convert to JSON
    @param pug A Pug object

    @return ID The ID of the new pug
    """
    def flush_new_pug(self, api_key, jsoninterface, pug):
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
