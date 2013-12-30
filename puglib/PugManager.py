# This is the PUG manager library for TF2Pug. It handles pug creation, user
# user management and server management.
#
# The methods provided in this class are used by the API server. The data
# returned for certain methods is in the form of a dict, which is converted to
# a JSON packet by the tornado request write method. These methods document
# the specific format of that packet.

import logging
import time

from Pug import Pug
from ResponseHandler import ResponseHandler

class PugManager(object):
    def __init__(self, db):
        self.db = db

        # pugs are maintained as a list of Pug objects
        self._pugs = []

        self.responder = ResponseHandler()

    """
    This method is used to add players to a pug. 
    If a pug ID is specified, the player is added to that pug if possible. If 
    it is not possible, a -1 is returned.

    If no pug ID is specified, the player is added to the first pug with space
    available. If no space is available, a new pug is created.

    @param player_id The ID of the player to add
    @param player_name The name of the player to add
    @param pug_id The ID of the pug to add the player to

    @return int The ID of the pug the player was added to, or -1 if none
    """
    def add_player(self, player_id, player_name, pug_id = None, size = 12):
        # if we have a pug_id, check if that pug exists
        if pug_id:
            pug = self._get_pug_by_id(pug)

            if pug and not pug.full:
                pug.add_player(player_id, player_name)
                return pug_id
            else:
                return -1

        else:
            # no pug id specified. add player to the first pug with space
            pug = self._get_pug_with_space(size)
            if pug:
                pug.add_player(player_id, player_name)

            else:
                # No pugs available with space. We need to make a new one!
                return self.create_pug(player_id, player_name, size = size)

    """
    This method removes the given player ID from any pugs they may be in.

    @param player_id The player to remove. If the player is not in a pug,
                     -1 is returned

    @return int The ID of the pug the player was removed from, -1 if the user
                is not in a pug, (-2 if the pug has been ended)?
    """
    def remove_player(self, player_id):
        pug = self._get_player_pug(player_id)

        if pug is None:
            return -1

        pug.remove_player(player_id)

        # if there's no more players in the pug, we need to end it
        if pug.player_count == 0:
            self._end_pug(pug)

            return -2
        else:
            return pug.id

    """
    This method is used to create a new pug. Size and map are optional. If the
    player is already in a pug, -1 is returned.

    @param player_id The ID of the player to add
    @param player_name The name of the player to add
    @param size The size of the pug (max number of players)
    @param map The map the pug will be on. If none, it means a vote will occur
               once the pug is full.

    @return int The ID of the newly created pug, or -1 if not possible.
    """
    def create_pug(self, player_id, player_name, size = 12, pug_map = None):
        if self._player_in_pug(player_id):
            return -1

        # create a new pug with id
        pug_id = int(round(time.time()))

        pug = Pug(pug_id, size, pug_map)
        pug.add_player(player_id, player_name)

        self._pugs.append(pug)

        return pug_id

    """
    This method is a public wrapper for _end_pug(). This serves to ensure that
    the pug object itself is always passed to _end_pug, rather than an ID. In
    otherwords, it's for method overloading (which we can otherwise only do by
    having optional parameters).

    @param pug_id The ID of the pug to end
    """
    def end_pug(self, pug_id):
        pug = self._get_pug_by_id(pug_id)

        if pug is None:
            return

        self._end_pug(pug)

    """
    Ends the given pug (i.e deletes it from the manager, maybe does some
    database shit at a later stage)

    @param Pug The pug to end
    """
    def _end_pug(self, pug):
        self._pugs.remove(pug)

    """
    Returns a dictionary of pug ids and their status. (i.e a complete listing 
    of current pugs and their complete status)

    This will be converted to a JSON packet by tornado.
    The format is documented in 'docs/json.format.md'
    """
    def get_pug_listing(self):
        return self.responder.construct_list_packet(self._pugs)

    """
    Returns a dictionary of a pug's status.
    """
    def get_pug_status(self, pug_id):
        pug = self._get_pug_by_id(pug_id)

        return self.responder.construct_status_packet(pug)

    def get_player_list(self, pug_id):
        pug = self._get_pug_by_id(pug_id)

        return self.responder.construct_player_list_packet(pug)

    """
    Determines if a player is in a pug.

    @param player_id The player to check for

    @return bool True if the player is in a pug, else False
    """
    def _player_in_pug(self, player_id):
        return self._get_player_pug(player_id) is not None

    """
    Gets the pug the given player is in (if any).

    @param player_id The player to check for

    @return Pug The pug the player is in, or none
    """
    def _get_player_pug(self, player_id):
        for pug in self._pugs:
            if pug.has_player(player_id):
                return pug

        return None

    """
    Searches through the pug list for a pug matching the given id.

    @param pug_id The pug ID to search for

    @return Pug The pug matching the given ID, or None
    """
    def _get_pug_by_id(self, pug_id):
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
