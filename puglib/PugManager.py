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

# Raised when trying to add a player to a full pug
class PugFullException(Exception):
    pass

# Raised when an invalid pug is given
class InvalidPugException(Exception):
    pass

# Raised when a player is already in a pug (during pug creation)
class PlayerInPugException(Exception):
    pass

# Raised when a player is not in a pug
class PlayerNotInPugException(Exception):
    pass

# Raised when a pug doesn't exist
class NonExistantPugException(Exception):
    pass

# Raised when a pug is ended because it becomes empty after a remove
class PugEmptyEndException(Exception):
    pass

class PugManager(object):
    def __init__(self, db):
        self.db = db

        # pugs are maintained as a list of Pug objects
        self._pugs = []

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

        # if we have a pug_id, check if that pug exists
        if pug_id:
            pug = self.get_pug_by_id(pug)

            if pug is None:
                raise InvalidPugException("Pug with id %d does not exist" % pug_id)

            if not pug.full:
                pug.add_player(player_id, player_name)

                return pug
            else:
                raise PugFullException("Pug %d is full" % pug.id )
                

        else:
            # no pug id specified. add player to the first pug with space
            pug = self._get_pug_with_space(size)
            if pug:
                pug.add_player(player_id, player_name)
                return pug

            else:
                # No pugs available with space. We need to make a new one!
                return self.create_pug(player_id, player_name, size = size)

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

        # create a new pug with id
        pug_id = int(round(time.time()))

        pug = Pug(pug_id, size, pug_map)
        pug.add_player(player_id, player_name)

        self._pugs.append(pug)

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

    @param Pug The pug to end
    """
    def _end_pug(self, pug):
        self._pugs.remove(pug)

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
