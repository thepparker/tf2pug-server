# This is the PUG manager library for TF2Pug. It handles pug creation, user
# user management and server management.
# The methods provided in this class are used by the API server. The data
# returned for certain methods is in the form of a dict, which is converted to
# a JSON packet by the tornado request write method. These methods document
# the specific format of that packet.

import logging
from Pug import Pug

class PugManager(object):
    def __init__(self, db):
        self.db = db

        # pugs are maintained as a list of Pug objects
        self._pugs = []

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

        return pug_id

    """
    Determines if a player is in a pug.

    @param player_id The player to check for

    @return bool True if the player is in a pug, else False
    """
    def _player_in_pug(self, player_id):
        for pug in self._pugs:
            if pug.has_player(player_id):
                return True

        return False

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
