"""
A base database interface class. This class is used to interface with your
database of choice, and must implement all methods, which are used by the
application.

An implementation for PostgreSQL is provided
"""

class BaseDatabaseInterface(object):
    def __init__(self, db):
        self.db = db

    """
    Gets all user info from the auth table. If an api key is specified, will
    only get data pertaining to that key. If no api key is specified, will get
    all user info.

    @param api_key (optional) The API key to get user info for

    @return Undecided on format
    """
    def get_user_info(self, api_key = None):
        raise NotImplementedError("This must be implemented")

    """
    Required by the pug manager. Gets info pertaining to the given list of
    64bit SteamIDs. Such info includes games since playing medic, total number
    of games played, and the player rating.

    @param ids The list of IDs to get data for

    @return A dictionary of stats with respect to each individual ID
    """
    def get_pug_stats(self, ids):
        raise NotImplementedError("This must be implemented")

    """
    Updates medic stats from a pug. The list of medics given is the medics
    playing medic for the pug, non medics is the list of players in the pug who
    are not medics

    @param medics List of 64bit SteamIDs who are playing medic
    @param nonmedics List of 64bit SteamIDS who are not playing medic
    """
    def flush_med_stats(self, medics, nonmedics):
        raise NotImplementedError("This must be implemented")

    """
    Gets pug data pertaining to a specified API key, and returns it as a list
    of JSON objects, which can be parsed through the JSON interface by the
    caller to get pug objects.

    @param api_key The api key to get pugs for
    @param include_finished Whether or not to include games that are finished
                            i.e in the "GAME_OVER" state

    @return List of JSON objects
    """
    def get_pugs(self, api_key, include_finished = False):
        raise NotImplementedError("This must be implemented")

    """
    Flushes a JSONised pug to the database. Maintains the pug index in another
    table. This method is only used for non-new pugs.

    @param api_key The API key the pug is under (not necessary?)
    @param id The ID of the pug
    @param pug_json A pug object converted to JSON
    """
    def flush_pug(self, api_key, id, pug_json):
        raise NotImplementedError("This must be implemented")

    """
    Flushes a new pug to the database, returning the ID

    @param api_key The API key the pug is under
    @param pug_json A Pug object converted to JSON

    @return ID The ID of the new pug
    """
    def flush_new_pug(self, api_key, pug_json):
        raise NotImplementedError("This must be implemented")

    """
    Gets all servers pertaining to the specified API key. Returns a list of
    dictionaries, which each list item being a server table row.

    @param api_key The API key to get servers for

    @return List of dictionaries for each server
    """
    def get_servers(self, api_key):
        raise NotImplementedError("This must be implemented")

    """
    Flushes a server to the database

    @param api_key The API key (Not necessary?)
    @param server The server to flush
    """
    def flush_server(self, api_key, server):
        raise NotImplementedError("This must be implemented")
