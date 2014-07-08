# This is the PUG manager library for TF2Pug. It handles pug creation, user
# user management and server management.
#
# The methods provided in this class are used by the API server. The data
# returned for certain methods is in the form of a dict, which is converted to
# a JSON packet by the tornado request write method. These methods document
# the specific format of that packet.

import logging
import time
import collections

import settings
import Livelogs

from entities import Pug
from interfaces.TFPugJsonInterface import TFPugJsonInterface

from Exceptions import *

from pprint import pprint

class PugManager(object):
    def __init__(self, api_key, db, server_manager):
        self.api_key = api_key
        self.db = db

        # pugs are maintained as a list of Pug objects
        self._pugs = []

        self._id_counter = 0

        self.server_manager = server_manager

        self.__load_pugs()

    """
    Adds a player to a pug. 

    If a pug ID is specified, the player is added to that pug if possible. If 
    it is not possible, an exception is raised.

    If no pug ID is specified, the player is added to the first pug with space
    available. If no space is available, a new pug is created.

    @param player_id The ID of the player to add
    @param player_name The name of the player to add
    @param pug_id The ID of the pug to add the player to

    @return Pug The pug the player was added to or None
    """
    def add_player(self, player_id, player_name, pug_id):
        # first check if the player is already in a pug
        player_pug = self.get_player_pug(player_id)
        if player_pug is not None:
            raise PlayerInPugException("Player %s is in pug %d", (player_id, player_pug.id))

        pug = None

        # if we have a pug_id, check if that pug exists
        if pug_id:
            pug = self.get_pug_by_id(pug_id)

            if pug is None:
                raise InvalidPugException("Pug with id %d does not exist" % pug_id)

            elif pug.full:
                raise PugFullException("Pug %d is full" % pug.id )

            else:
                pug.add_player(player_id, player_name)

        else:
            #no pug id specified
            raise InvalidPugException("No pug id speficied")


        # we now have a valid pug and the player has been aded. check if it's
        # full
        if pug.full:
            # pug is full, so we should make it transition to map voting
            pug.begin_map_vote()

        # update the database with current pug details
        self._flush_pug(pug)

        return pug


    """
    This method removes the given player ID from any pug they may be in.

    If the player is not in a pug, an exception is raised. If the pug was
    ended because it is empty after removing the player, an exception is
    raised.

    @param player_id The player to remove

    @return Pug The pug the player was removed from.
    """
    def remove_player(self, player_id):
        pug = self.get_player_pug(player_id)

        if pug is None:
            raise PlayerNotInPugException("Player %s is not in a pug" % player_id)

        pug.remove_player(player_id)

        # if there's no more players in the pug, we need to end it
        if pug.player_count == 0:
            self._end_pug(pug)

            raise PugEmptyEndException("Pug %d is empty and was ended" % pug.id)
        else:
            return pug

    """
    This method is used to create a new pug. Size and map are optional. If the
    player is already in a pug, an exception is raised.

    @param player_id The ID of the player to add
    @param player_name The name of the player to add
    @param size The size of the pug (max number of players)
    @param map The map the pug will be on. If none, it means a vote will occur
               once the pug is full.

    @return Pug The newly created pug
    """
    def create_pug(self, player_id, player_name, size = 12, pug_map = None):
        # check if player is in a pug first
        if self._player_in_pug(player_id):
            raise PlayerInPugException("Player %s (%s) is already in a pug" % (player_name, player_id))

        # player not in a pug. so let's make a new one
        pug = Pug.Pug(size = size, pmap = pug_map)
        
        # see if we can get a server before doing anything else
        server = self.server_manager.allocate(pug)

        # If the server returned is None, there are no servers available.
        # Therefore, we raise an exception. Else, code continues and player
        # gets added/pug gets flushed
        if not server:
            raise NoAvailableServersException("No more servers are available")
            
        pug.add_player(player_id, player_name)

        self._pugs.append(pug)

        self._flush_pug(pug, new = True)

        # update server with id
        pug.server.pug_id = pug.id
        self.server_manager._flush_server(pug.server)

        return pug

    """
    This method is a public wrapper for _end_pug(). This serves to ensure that
    the pug object itself is always passed to _end_pug, rather than an ID. In
    otherwords, it's for method overloading (which we can otherwise only do by
    having optional parameters).

    @param pug_id The ID of the pug to end
    """
    def end_pug(self, pug_id):
        pug = self.get_pug_by_id(pug_id)

        if pug is None:
            raise NonExistantPugException("Pug with id %d does not exist", pug_id)

        self._end_pug(pug)

    """
    Ends the given pug. This means we set the state to game over, reset the
    assigned server, close the logging socket and flush the pug/server.

    @param pug The pug to end
    """
    def _end_pug(self, pug):
        pug.state = Pug.states["GAME_OVER"]

        # resetting the server automatically causes a server_manager flush
        # also closes the logging socket? maybe?
        self.server_manager.reset(pug.server)

        self._flush_pug(pug)

        # lastly, remove the pug from the list
        self._pugs.remove(pug)

    """
    Adds a vote for the given map by the specified player.

    Raises an exception if the player is not in a pug.

    @param player_id The ID of the player voting
    @param pmap The map being voted for

    @return Pug The pug that had a map vote placed
    """
    def vote_map(self, player_id, pmap):
        pug = self.get_player_pug(player_id)

        if pug is None:
            raise PlayerNotInPugException("Player %s is not in a pug" % player_id)

        if pug.state != Pug.states["MAP_VOTING"]:
            raise NoMapVoteException("Pug is not in map voting stage")

        if pmap not in pug.maps:
            raise InvalidMapException("Map is not available in this pug")

        pug.vote_map(player_id, pmap)

        # update the database with current pug details
        self._flush_pug(pug)

        return pug

    """
    Forces the pug's map to this the given map. Can only be used before voting
    has begun.
    """
    def force_map(self, pug_id, pmap):
        pug = self.get_pug_by_id(pug_id)

        if pug is None:
            raise NonExistantPugException("Pug with id %d does not exist" % pug_id)

        if pug.state > Pug.states["GATHERING_PLAYERS"]:
            raise ForceMapException("Too late to force the map")

        if pmap not in pug.maps:
            raise InvalidMapException("Map is not available in this pug")

        pug.force_map(pmap)

        # update the database with current pug details
        self._flush_pug(pug)

        return pug

    """
    Returns the list of pugs being managed by this manager
    """
    def get_pugs(self):
        return self._pugs

    """
    Determines if a player is in a pug.

    @param player_id The player to check for

    @return bool True if the player is in a pug, else False
    """
    def _player_in_pug(self, player_id):
        return self.get_player_pug(player_id) is not None

    """
    Gets the pug the given player is in (if any).

    @param player_id The player to check for

    @return Pug The pug the player is in, or none
    """
    def get_player_pug(self, player_id):
        for pug in self._pugs:
            if pug.has_player(player_id):
                return pug

        return None

    """
    Searches through the pug list for a pug matching the given id.

    @param pug_id The pug ID to search for

    @return Pug The pug matching the given ID, or None
    """
    def get_pug_by_id(self, pug_id):
        for pug in self._pugs:
            if pug.id == pug_id:
                return pug

        return None

    """
    Searches through the pug list and returns the first pug with space
    available.

    @param size (optional) The pug size to match against

    @return Pug The first PUG with space available, or None
    """
    def _get_pug_with_space(self, size = 12):
        for pug in self._pugs:
            if pug.size == size and not pug.full:
                return pug

        return None

    def map_vote_check(self, curr_ctime):
        for pug in self._pugs:
            if (pug.state == Pug.states["MAP_VOTING"]) and (curr_ctime > pug.map_vote_end):
                logging.debug("Map vote period is over for pug %d", pug.id)
                # END MAP VOTING FOR THIS PUG
                pug.end_map_vote()

                # shuffle teams
                pug.shuffle_teams(self._get_pug_stat_data(pug))

                self.__flush_med_stats(pug)

    def _get_pug_stat_data(self, pug):
        # need to get player stats from livelogs, and med stats from pug db
        stats = self.__get_pug_stats(pug)

        for cid in pug.player_list():
            # if the CID has no pug data, they need to be added
            if not (cid in stats):
                stats[cid]["games_since_med"] = 0
                stats[cid]["games_played"] = 0
                stats[cid]["rating"] = 1500

        return stats

    """
    Gets stat data for the given pug. The only stat data kept by the TF2Pug
    server are games since med, number of games played, and the player's elo.
    Everything else is done via Livelogs, or the client's chosen stat provider.

    @param Pug pug The pug to get stat data for

    @return dict The pug's stat data
    """
    def __get_pug_stats(self, pug):
        return self.db.get_tf_player_stats(pug.players_list)

    def __flush_med_stats(self, pug):
        conn, cursor = self._get_db_objects()

        medics = [ pug.medic_red, pug.medic_blue ]

        nonmedics = [ x for x in pug._players if x not in medics ]

        self.db.flush_tf_pug_med_stats(medics, nonmedics)

    """
    Calculates the new ELO of players after the game and updates it in the database

    @param pug The pug to update ELO for
    """
    def __update_ratings(self, pug):
        pass
        

    def __db_upsert(self, insert, update):
        conn, cursor = self._get_db_objects()

        try:
            cursor.execute("SELECT pgsql_upsert(%s, %s)", (insert, update,))
        except:
            logging.exception("Exception performing upsert")

        finally:
            self._close_db_objects((conn, cursor))

    def __hydrate_pug(self, data):
        logging.debug("HYDRATING PUG. DB DATA: %s", data)

        pug = Pug.Pug()

        pug.id = data["id"]
        pug.size = data["size"]
        pug.state = data["state"]

        pug.map = data["map"]
        pug.map_forced = data["map_forced"]
        
        pug.admin = long(data["admin"])
        # IDs are returned as strings, so we convert them back to longs
        # and re-add the players normally
        players = data["players"]
        for pid in players:
            pug._players[long(pid)] = players[pid]

        # do the same for player_votes and map_votes
        player_votes = data["player_votes"]
        for pid in player_votes:
            pug.player_votes[long(pid)] = player_votes[pid]

        map_votes = data["map_votes"]
        for mname in map_votes:
            pug.map_votes[mname] = int(map_votes[mname])

        pug.map_vote_start = data["map_vote_start"]
        pug.map_vote_end = data["map_vote_end"]

        pug.server_id = data["server_id"]
        if pug.server_id >= 0:
            pug.server = self.server_manager.get_server_by_id(pug.server_id)

            pug.server.pug = pug
            pug.server.pug_id = pug.id

        pug.team_red = data["team_red"]
        pug.team_blue = data["team_blue"]

        return pug

    def __load_pugs(self):
        # clear the pug list
        del self._pugs[:]
 
        self._pugs = self.db.get_pugs(self.api_key, TFPugJsonInterface().loads)
        
    def _flush_pug(self, pug, new = False):
        logging.debug("Flushing pug to database. ID: %d", pug.id)
        if new:
            jsoninterface = TFPugJsonInterface()

            result = self.db.flush_new_pug(self.api_key, jsoninterface, pug)

            if result:
                pug.id = result

        # if the pug isn't new, we're flushing it directly. if it is new, we're
        # flushing it again so that the ID is stored in the pug data as well
        self.db.flush_pug(self.api_key, jsoninterface, pug.id, pug)

    def flush_all(self):
        for pug in self._pugs:
            self._flush_pug(pug)
