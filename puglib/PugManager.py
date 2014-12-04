# This is the PUG manager library for TF2Pug. It handles pug creation, user
# management and server management.

import logging
import time

import settings
import rating

from entities import Pug
from entities.Pug import PlayerStats
from interfaces import get_json_interface
from Exceptions import *

class PugManager(object):
    """
    PugManager controls everything to do with pugs. From map vote start/end,
    adding players to appropriate pugs, maintaining a list of active pugs,
    etc.
    """
    def __init__(self, api_key, db, server_manager, ban_manager):
        self.game = "TF2"

        self._json_iface_cls = get_json_interface(self.game)

        self.api_key = api_key
        self.db = db

        # pugs are maintained as a list of Pug objects
        self._pugs = []

        self.server_manager = server_manager
        self.ban_manager = ban_manager

        self.__load_pugs()

    def add_player(self, player_id, player_name, pug_id):
        """
        Adds a player to a pug. 

        The player is added to the given pug id if possible. If not possible,
        an exception is raised.

        :param player_id The ID of the player to add
        :param player_name The name of the player to add
        :param pug_id The ID of the pug to add the player to

        :return Pug The pug the player was added to or None
        """
        pug = self.get_pug_by_id(pug_id)

        if pug is None:
            raise InvalidPugException("Pug with id %d does not exist" % pug_id)

        # Use internal method to avoid duplication. Exception will be raised by
        # `_add_player` if adding the player is not possible.
        self._add_player(pug, player_id, player_name)

        # update the database with current pug details
        self._flush_pug(pug)

        return pug

    def _add_player(self, pug, player_id, player_name):
        """
        Internal method for adding a player to the given pug object. Raises an
        exception when adding them is not possible. Use of this method avoids
        code duplication in `create_pug` and `add_player`. Note that this
        method does NOT flush the pug, so it must be done by the calling
        method after this succeeds.
        """
        # let's see if the user is banned/already in a pug
        if self._player_banned(player_id):
            raise PlayerBannedException("Player %s is banned" % player_id)

        if self.get_player_pug(player_id) is not None:
            raise PlayerInPugException("Player %s is already in pug" % player_id)

        if pug.full:
            raise PugFullException("Pug %d is full" % pug.id )

        else:
            # have potential pug. we need to check if the player is within the
            # rating restriction. meaning, we need to get the player stats here

            stats = self._get_player_stats(player_id)
            player_rating = stats[player_id]["rating"]

            if pug.player_restricted(player_rating):
                raise PlayerRestrictedException("Player too good (or bad)")

            else:
                pug.add_player(player_id, player_name, stats[player_id])

        # We now have a valid pug and the player has been aded. check if it's
        # full, and proceed to map voting. Only do this if the current state is
        # gathering players (i.e. map vote has not already been done). This
        # check is performed in case the pug actually requires a replacement,
        # in which case, map voting has already taken place.
        if pug.full and pug.state == Pug.states["GATHERING_PLAYERS"]:
            pug.begin_map_vote()

    def remove_player(self, player_id):
        """
        This method removes the given player ID from any pug they may be in.

        If the player is not in a pug, an exception is raised. If the pug was
        ended because it is empty after removing the player, an exception is
        raised.

        :param player_id The player to remove

        :return Pug The pug the player was removed from.
        """
        pug = self.get_player_pug(player_id)

        if pug is None:
            raise PlayerNotInPugException("Player %s is not in a pug" % player_id)

        if pug.state == Pug.states["MAP_VOTING"]:
            raise PlayerLeaveTooLateException("Player cannot leave this late")

        pug.remove_player(player_id)

        # if there's no more players in the pug, we need to end it
        if pug.player_count == 0:
            self._end_pug(pug)

            raise PugEmptyEndException("Pug %d is empty and was ended" % pug.id)
        else:
            return pug

    def create_pug(self, player_id, player_name, size = 12, pug_map = None,
                   custom_id = None, restriction = None):
        """
        This method is used to create a new pug. Size and map are optional. If 
        the player is already in a pug, is banned, or does not meet the
        restriction themselves, an exception is raised.

        :param player_id The ID of the player to add
        :param player_name The name of the player to add
        :param size The size of the pug (max number of players)
        :param map The map the pug will be on. If none, it means a vote will 
                   occur once the pug is full.
        :param custom_id A custom ID to assign to the pug. Useful for clients
                         to distinguish pugs if necessary.
        :param restriction A rating restriction to enforce. If a positive
                           number is given, players must have >= that rating.
                           If a negative number is given, players must have
                           < that rating.

        :return Pug The newly created pug
        """

        if pug_map is not None and (not Pug.Pug.map_available(pug_map)):
            raise InvalidMapException("Invalid map specified")

        pug = Pug.Pug(size = size, pmap = pug_map, custom_id = custom_id,
                      restriction = restriction)

        # try to add the player to the newly created pug. if the player is
        # banned, restricted, or in another pug, _add_player will raise an
        # exception. The pug is not flushed to the database by _add_player.
        self._add_player(pug, player_id, player_name)

        # if we've reached here, player was successfully added to the pug.
        # check if we can get a server or not. if not, raise an exception and
        # escape before we add the pug to the internal list and flush it.
        server = self.server_manager.allocate(pug)

        # If the server returned is None, there are no servers available.
        # Therefore, we raise an exception. Else, code continues and player
        # gets added/pug gets flushed
        if server is None:
            raise NoAvailableServersException("No more servers are available")
            
        self._pugs.append(pug)

        self._flush_pug(pug)

        # prepare the server for pug (empty it, set pw, update pug id, etc)
        self.server_manager.prepare(server)

        return pug

    def end_pug(self, pug_id):
        """
        This method is a public wrapper for _end_pug(). This serves to ensure 
        that the pug object itself is always passed to _end_pug, rather than
        an ID. 

        :param pug_id The ID of the pug to end
        """
        pug = self.get_pug_by_id(pug_id)

        if pug is None:
            raise InvalidPugException("Pug with id %d does not exist", pug_id)

        self._end_pug(pug)

    def _end_pug(self, pug):
        """
        Ends the given pug. This means we set the state to game over, reset the
        assigned server, close the logging socket and flush the pug/server.

        :param pug The pug to end
        """
        # resetting the server automatically causes a server_manager flush.
        # also closes the logging socket
        self.server_manager.reset(pug.server)

        # set to game over so we never load this pug again if forced end
        pug.state = Pug.states["GAME_OVER"]

        # flush updated pug
        self._flush_pug(pug)

        # lastly, remove the pug from the list
        if pug in self._pugs:
            self._pugs.remove(pug)

    def vote_map(self, player_id, pmap):
        """
        Adds a vote for the given map by the specified player.

        Raises an exception if the player is not in a pug, the pug is not in
        map voting state, or the map is invalid.

        :param player_id The ID of the player voting
        :param pmap The map being voted for

        :return Pug The pug that had a map vote placed
        """
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

    def force_map(self, pug_id, pmap):
        """
        Forces the pug's map to this the given map. Can only be used before 
        voting has begun.
        """
        pug = self.get_pug_by_id(pug_id)

        if pug is None:
            raise InvalidPugException("Pug with id %d does not exist" % pug_id)

        if pug.state > Pug.states["GATHERING_PLAYERS"]:
            raise ForceMapException("Too late to force the map")

        if not Pug.Pug.map_available(pmap):
            raise InvalidMapException("Map is not available in this pug")

        pug.force_map(pmap)

        # update the database with current pug details
        self._flush_pug(pug)

        return pug

    def get_pugs(self):
        """
        Returns the list of pugs being managed by this manager
        """
        return self._pugs

    def _player_in_pug(self, player_id):
        """
        Determines if a player is in a pug.

        :param player_id The player to check for

        :return bool True if the player is in a pug, else False
        """
        return self.get_player_pug(player_id) is not None

    def _player_banned(self, player_id):
        """
        Checks if the given player is banned from this service.

        :param player_id The player to check

        :return bool True if the player is banned, else False
        """
        ban = self.ban_manager.get_player_ban(player_id)
        
        if ban is not None:
            return True

        return False

    def get_player_pug(self, player_id):
        """
        Gets the pug the given player is in (if any).

        :param player_id The player to check for

        :return Pug The pug the player is in, or none
        """
        for pug in self._pugs:
            if pug.has_player(player_id):
                return pug

        return None

    def get_pug_by_id(self, pug_id):
        """
        Searches through the pug list for a pug matching the given id.

        :param pug_id The pug ID to search for

        :return Pug The pug matching the given ID, or None
        """
        for pug in self._pugs:
            if pug.id == pug_id:
                return pug

        return None

    def _get_pug_with_space(self, size = 12):
        """
        Searches through the pug list and returns the first pug with space
        available.

        :param size (optional) The pug size to match against

        :return Pug The first PUG with space available, or None
        """
        for pug in self._pugs:
            if pug.size == size and not pug.full:
                return pug

        return None

    def status_check(self, ctime = 0):
        """
        Performs various status checks on all pugs managed by this manager.
        These includes things such as ending map votes, shuffling teams,
        ending pugs at game over, etc.

        :param ctime The current epoch time (used for checking map vote end)
        """
        for pug in self._pugs[:]:
            if (pug.state == Pug.states["MAP_VOTING"]) and (ctime > pug.map_vote_end):
                logging.debug("Map vote period is over for pug %d", pug.id)
                # END MAP VOTING FOR THIS PUG
                pug.end_map_vote()

                # Make the teams and then change the map to the voted map
                pug.shuffle_teams()
                pug.server.change_map()
                pug.setup_connect_timer()

                self._flush_pug(pug)

            elif (pug.state == Pug.states["MAPVOTE_COMPLETED"]):
                # means the map was forced and begin_map_vote just set
                # the state to mapvote_completed (i.e teams were not shuffled)
                # so we need to shuffle teams and change map

                pug.shuffle_teams()
                pug.server.change_map()
                pug.setup_connect_timer()

                self._flush_pug(pug)

            elif (pug.state == Pug.states["GAME_OVER"]):
                # game is over! we need to update player rating based on the
                # results, flush the pug one final time, and then remove pug
                # from the internal list
                if not pug.stats_done:
                    self._update_ratings(pug)
                
                    pug.update_end_stats()
                    self.__flush_pug_stats(pug)

                # 10 second grace period for clients to update with the end
                # stats and for players in the server to get the end of game
                # panel and statistics in-game.
                if ctime - pug.game_over_time > 10:
                    self._end_pug(pug)

            elif (pug.state == Pug.states["GATHERING_PLAYERS"] and
                    ctime > pug.start_time + 1200):
                # Pug has been looking for players for longer than 20 minutes,
                # so we force end
                
                self._end_pug(pug)

            elif (pug.state == Pug.states["REPLACEMENT_REQUIRED"]):
                """
                A replacement is required. If the game has not started yet
                (i.e. has not gone live -> state is not GAME_STARTED) and 5
                minutes has passed without a replacement joining, we end the
                pug. Similarly, if the game is live, less than 15 minutes
                has been played, and if no replacement is found in 5 minutes,
                end the pug. 
                """
                #logging.debug("Pug is in replacement state. Game started: %s, "
                #              "Replacement timed out: %s, replace timeout: %d, curr time: %d",
                #              pug.game_started, pug.replacement_timed_out, 
                #              pug.replacement_timeout, ctime)

                if not pug.game_started and pug.replacement_timed_out:
                    # Game not live, replace timed out. End the pug.
                    self._end_pug(pug)

                elif (pug.game_started and 
                      ctime < pug.game_start_time + 900 and
                      pug.replacement_timed_out):

                    # Game is live, less than 15 minutes has elapsed and
                    # replacement has timed out. End the pug.

                    self._end_pug(pug)

            if pug.has_disconnects:
                # Check pugs for disconnects. If a player has been disconnected
                # for longer than a certain time, they are removed.
                pug.check_disconnects()
                # If ALL players were removed from the pug after 
                # `check_disconnects()`, there's likely something wrong with
                # the server. End the pug straight away.
                if pug.player_count == 0:
                    self._end_pug(pug)

    def _get_multi_player_stats(self, players):
        """
        Gets a list of player's stats

        :param players A list of 64bit SteamIDs

        :return dict A dict containing stats with CIDs as keys
        """
        # need to get player stats from livelogs, and med stats from pug db
        stats = self.db.get_player_stats(players)

        logging.debug("Player stats: %s", stats)

        for cid in stats:
            # initialize a new PlayerStats object with the player's set stats
            stats[cid] = PlayerStats(stats[cid])

        for cid in players:
            # if the CID has no pug data, they need to be added
            if not (cid in stats):
                # create new player stats object for this player
                stats[cid] = PlayerStats()

        return stats

    def _get_player_stats(self, player_id):
        """
        Get an individual player's stat data

        :param player_id The player's 64bit SteamID

        :return dict A dict of the player's stats with CID as key
        """
        stats = self.db.get_player_stats([ player_id ])
        if stats and player_id in stats:
            # player has existing stats. pass them through the player stats
            # object, which will initialize any new stats
            stats[player_id] = PlayerStats(stats[player_id])
            return stats

        else:
            # return new, empty, playerstats object
            return {
                player_id: PlayerStats()
            }

    def __flush_pug_stats(self, pug):
        self.db.flush_player_stats(pug.end_stats)

    """
    
    """
    def _update_ratings(self, pug):
        """
        Calculates the new rating of players after the game and updates it in
        the pug object.

        We use an Elo implementation to calculate a player's new
        rating based on the actual and expected outcome of the game.
        For the basic elo algorithm, please see the following:
        https://en.wikipedia.org/wiki/Elo_rating_system#Mathematical_details

        Because of the fact that we have teams, we cannot use a simple 1v1
        method of taking/giving points. To use Elo with teams, we use a 
        'duels' method. That is, each player is considered to have dueled
        each player on the other team, and the points gained (or lost) is
        the average of the sum.
        For example, player 1 on team 1 has 1700 rating. Team 1 won. If we
        were to calculate the points he'd gain, we'd calculate the gain for
        each player of the opposition, sum it, and then divide it by the
        number of players (average it).


        There are also other algorithms that could be used, such as TrueSkill,
        or Glicko, which both have their ups and downs. For TrueSkill, I feel 
        that the player's rating can vary greatly after a match. Sometimes
        increasing after a win, sometimes decreasing depending on the team
        ratings. The amount that the scores change by can vary significantly
        too, such as an increase of ~60 for a player with 1700 rating when 
        winning against a team with players all of lower rating. That being
        said, it is probably more suitable to a team game than a hacked elo
        based system. There is a python library available for TrueSkill.

        Glicko, like Elo, is designed for chess. Therefore, to use it, it would
        be necessary to hack it together for a team-based game, such as using
        the duels method. The algorithm is a bit more complex, but not too
        difficult to implement. It utilises a guassian distribution, and
        uncertainty factors into the rating. There is also a python library
        available for Glicko2

        If a duel-based Elo system does not work out, implementing TrueSkill
        or Glicko will not be too hard.

        :param pug The pug to update ratings for
        """
        team1, team2 = pug.teams.keys()

        # we need to construct 2 lists of Rating, one for each team. These will
        # be passed to the rating calculator
        ratings = {
            team1: [],
            team2: []
        }

        # rank in order of winning team. i.e [0, 1] = team 1 > team 2
        # [1, 0] = team 1 < team 2
        # we'll always put it in order of team 1 - team 2
        ranking = []

        for team in pug.teams:
            ratings[team] = [ rating.Rating(pug.player_stats[x]["rating"]) for x in pug.teams[team] ]

        team1_game_score = pug.game_scores[team1]
        team2_game_score = pug.game_scores[team2]

        if team1_game_score > team2_game_score:
            ranking = [0, 1]

        elif team1_game_score < team2_game_score:
            ranking = [1, 0]
            
        else:
            ranking = [0, 0]

        new_ratings = rating.calculate_rating([ratings[team1], ratings[team2]], ranking)

        # new_ratings is a list in the form [team1_new, team2_new], where each
        # teamX_new is a tuple of player ratings in the same order they were
        # passed in (as Rating objects)
        team1_rating, team2_rating = new_ratings

        # map player rating to player id, store as list of tuples which can be
        # easily inserted into the db
        mapper = lambda cid, r: (cid, float(r))
        ratings_tupled = map(mapper, pug.teams[team1], team1_rating) + map(mapper, pug.teams[team2], team2_rating)
        logging.debug("Players with new ratings: %s", ratings_tupled)

        # update player stats dict with new ratings in preparation for flush
        for cid, new_rating in ratings_tupled:
            pug.set_player_rating(cid, new_rating)

    def __load_pugs(self):
        """
        Load all pugs owned by this manager from the database.
        """
        # clear the pug list
        del self._pugs[:]
        logging.debug("Attempting to load pugs under API key %s", self.api_key)
 
        pugs = self.db.get_pugs(self.api_key, self._json_iface_cls())

        logging.debug("Pugs loaded: %s", pugs)

        for pug in pugs:
            logging.debug("Loaded pug id %d. Server id: %d", pug.id, pug.server_id)
            # if the pug is > 2 hours old, it should be ended (i.e something
            # went wrong)
            pug.server = self.server_manager.get_server_by_id(pug.server_id)
            # pug.server will be None if pug.server_id not found in server 
            # manager. if pug.server_id > 0 and pug.server is None, this
            # pug needs to be killed
            if ((pug.server_id is not None and pug.server is None)
              or (time.time() - pug.start_time) > 7200):
                self._end_pug(pug)

            elif pug.server is not None:
                pug.server.pug = pug # make sure to give the server the pug again!

                self._pugs.append(pug)
        
    def _flush_pug(self, pug):
        """
        Flush the given pug to the database

        :param pug The pug to flush
        """
        logging.debug("Flushing pug to database. ID: %s", pug.id)
        jsoninterface = self._json_iface_cls()

        self.db.flush_pug(self.api_key, jsoninterface, pug)

    def flush_all(self):
        """
        Flush all active pugs in this manager
        """
        for pug in self._pugs:
            self._flush_pug(pug)
