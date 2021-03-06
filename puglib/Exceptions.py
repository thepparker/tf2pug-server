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

# Raised when a player tries to leave the pug too late
class PlayerLeaveTooLateException(Exception):
    pass

# Raised when a pug is ended because it becomes empty after a remove
class PugEmptyEndException(Exception):
    pass

# Raised when we're unable to force the map. Likely due to it being too late
class ForceMapException(Exception):
    pass

# Raised when we cannot vote for maps. i.e when not in map voting state
class NoMapVoteException(Exception):
    pass

# Raised when attempting to vote for an invalid map
class InvalidMapException(Exception):
    pass

# Raised when no more servers are available
class NoAvailableServersException(Exception):
    pass

# Raised when a player is banned
class PlayerBannedException(Exception):
    pass

# Raised when a player is too high or too low rating for the pug
class PlayerRestrictedException(Exception):
    pass
