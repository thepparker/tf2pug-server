# This is the PUG manager library for TF2Pug. It handles pug creation, user
# user management and server management.
#
# The methods provided in this class are used by the API server. The data
# returned for certain methods is in the form of a dict, which is converted to
# a JSON packet by the tornado request write method. These methods document
# the specific format of that packet.

import logging
import time

import Pug

from Exceptions import *

pug_columns = (
        "id",
        "size",
        "state",

        "map",
        "map_forced",
        "players",

        "player_votes",
        "map_votes",
        "map_vote_start",
        "map_vote_end",

        "server_id",

        "team_red",
        "team_blue"
    )


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
    def add_player(self, player_id, player_name, pug_id = None, size = 12):
        # first check if the player is already in a pug. If so, return that pug?
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
            # no pug id specified. add player to the first pug with space
            pug = self._get_pug_with_space(size)
            if pug:
                pug.add_player(player_id, player_name)

            else:
                # No pugs available with space. We need to make a new one!
                return self.create_pug(player_id, player_name, size = size)

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

    @return int The ID of the newly created pug, or -1 if not possible.
    """
    def create_pug(self, player_id, player_name, size = 12, pug_map = None):
        if self._player_in_pug(player_id):
            raise PlayerInPugException("Player %s (%s) is already in a pug" % (player_name, player_id))

        pug = Pug.Pug(-1, size, pug_map)
        
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
    Ends the given pug (i.e deletes it from the manager, maybe does some
    database shit at a later stage)

    @param pug The pug to end
    """
    def _end_pug(self, pug):
        # we need to delete this pug from the database

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


    def __hydrate_pug(self, data):
        logging.debug("HYDRATING PUG. DB DATA: %s", data)

        # data is a tuple in the form of pug_columns
        pug = Pug.Pug()

        pug.id = data[0]
        pug.size = data[1]
        pug.state = data[2]

        pug.map = data[3]
        pug.map_forced = data[4]
        pug._players = data[5]

        pug.player_votes = data[6]
        pug.map_votes = data[7]
        pug.map_vote_start = data[8]
        pug.map_vote_end = data[9]

        pug.server_id = data[10]
        if pug.server_id >= 0:
            pug.server = self.server_manager.get_server_by_id(pug.server_id)

            pug.server.pug = pug
            pug.server.pug_id = pug.id

        pug.team_red = data[11]
        pug.team_blue = data[12]

        return pug

    def __load_pugs(self):
        # clear the pug list
        del self._pugs[:]

        conn, cursor = self._get_db_objects()

        try:
            cursor.execute("SELECT %s FROM pugs WHERE state != %s", (", ".join(pug_columns), Pug.states["GAME_OVER"],))

            results = cursor.fetchall()

            if results:
                for data in results:
                    pug = self.__hydrate_pug(data)

                    self._pugs.append(pug)

        except:
            logging.exception("Exception while loading pugs")

        finally:
            self._close_db_objects((conn, cursor))


    def _flush_pug(self, pug, new = False):
        logging.debug("Flushing pug to database. ID: %d", pug.id)
        if new:
            # insert
            conn, cursor = self._get_db_objects()

            logging.debug("Pug is new. Inserting")
            try:
                cursor.execute("INSERTO INTO pugs (%s, api_key) VALUES (%s) RETURNING id", (
                            ", ".join(pug_columns[1:]), pug.id, pug.size, pug.state, 
                            pug.map, pug.map_forced, pug._players, pug.player_votes,
                            pug.map_votes, pug.map_vote_start, pug.map_vote_end, 
                            pug.server_id, pug.team_red, pug.team_blue, self.api_key
                        )
                    )

                return_data = cursor.fetchone()

                if return_data:
                    pug.id = return_data[0]
                    logging.debug("New pug has ID %d", pug.id)
                    
                    # update server with id
                    pug.server.pug_id = pug.id
                    self.server_manager._flush_server(pug.server)

                else:
                    logging.error("No ID was returned when inserting pug. wat da fuk?")
                    pug.id = int(round(time.time()))

                conn.commit()

            except:
                logging.exception("Exception occured flushing pug")

            finally:
                self._close_db_objects((conn, cursor))

        else:
            conn, cursor = self._get_db_objects()

            logging.debug("Pug is not new. Updating")
            try:
                cursor.execute("""UPDATE pugs SET size = %s, state = %s, map = %s, map_forced = %s, players = %s, 
                    player_votes = %s, map_votes = %s, map_vote_start = %s, map_vote_end = %s, server_id = %s,
                    team_red = %s, team_blue = %s WHERE pugs.id = %s""", (
                            pug.size, pug.state, 
                            pug.map, pug.map_forced, pug._players, pug.player_votes,
                            pug.map_votes, pug.map_vote_start, pug.map_vote_end, 
                            pug.server_id, pug.team_red, pug.team_blue
                        )
                    )

                conn.commit()

            except:
                logging.exception("Exception occured flushing pug")

            finally:
                self._close_db_objects((conn, cursor))

    def flush_all(self, pug):
        for pug in self._pugs:
            self._flush_pug(pug)


    """
    Retrieves a db connection and a cursor in a (conn, cursor) tuple from the
    db pool
    """
    def _get_db_objects(self):
        conn = None
        curs = None

        try:
            conn = self.db.getconn()
            curs = conn.cursor()

            return (conn, curs)
        
        except:
            logging.exception("Exception getting db objects")

            if curs:
                curs.close()

            if conn:
                self.db.putconn(conn)

    """
    Takes a tuple of (conn, cursor), closes the cursor and puts the conn back
    into the pool
    """
    def _close_db_objects(self, objects):
        if objects[1] and not objects[1].closed:
            objects[1].close()

        if objects[0]:
            conn.rollback() # perform a rollback just incase something fucked up happened
            self.db.putconn(objects[0])
