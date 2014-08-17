import calendar
import time

def epoch():
    return calendar.timegm(time.gmtime())

class Ban(dict):
    """
    Ban just implements a dict with data pertaining to a player's ban.
    """
    def __init__(self, *args, **kwargs):
        """
        Sets the default ban parameters. Ban start time defaults to the time of
        object creation.
        """
        self["id"] = None
        self["banned_cid"] = None
        self["banned_name"] = None
        self["banner_cid"] = None
        self["banner_name"] = None
        self["ban_start_time"] = epoch()
        self["ban_duration"] = 0
        self["reason"] = None
        self["expired"] = False

        super(Bans, self).__init__(*args, **kwargs)

    def tuplify(self):
        """
        Returns a tuple of ban information in the following order for easy
        database insertion. Order MUST be maintained.
        """
        return (self["banned_cid"], self["banned_name"], 
                self["banner_cid"], self["banner_name"],
                self["ban_start_time"], self.duration, self["reason"],
                self.expired)

    def check_expiration(self):
        # ban_duration of None means the ban is permanent
        if self["ban_duration"] is None:
            return

        if epoch() > self["ban_start_time"] + self["ban_duration"]:
            self["expired"] = True

    @property
    def duration(self):
        """ Gets ban duration """
        return self["ban_duration"]

    @property(self):
    def expired(self):
        """ Gets the ban's expired status. """
        return self["expired"]

class BanAddException(Exception):
    """ Raised when adding a ban fails """
    pass

class BanManager(object):
    def __init__(self, db):
        self.db = db

        self.bans = []

        self.__load_bans()

    def add_ban(self, ban_data):
        """
        Takes a dict (decoded JSON) of parameters for the ban. Format is:
        {
            "bannee": {
                "id": cid,
                "name": name
            },
            "banner": {
                "id": cid,
                "name": name
            }
            "reason": reason
            "duration": duration
        }

        Banne(r/e) ID MUST be 64bit SteamIDs. Duration is time in seconds for
        the length of the ban, or None if the ban is permanent.
        """
        # Just throw assertion exceptions if any of the data is bad. We could
        # throw custom exceptions but why? The server handles the exception.
        assert ("bannee" in ban_data and "banner" in ban_data 
                and "reason" in ban_data and "duration" in ban_data)
        assert isinstance(ban_data["bannee"]["id"], (int, long))
        assert isinstance(ban_data["banner"]["id"], (int, long))

        ban = Ban()

        bannee = ban_data["bannee"]
        banner = ban_data["banner"]
        ban["banned_cid"] = bannee["id"]
        ban["banned_name"] = bannee["name"]

        ban["banner_id"] = banner["id"]
        ban["banner_name"] = banner["name"]

        ban["reason"] = ban_data["reason"]
        ban["duration"] = ban_data["duration"]

        try:
            return self._add_ban(ban)
        except:
            raise BanAddException("Unable to add ban")


    def _add_ban(self, ban):
        """
        Internal method for adding ban to database/list
        """
        existing_ban = self._get_player_ban()
        if existing_ban is not None:
            # If the player already has an existing ban, we just update it with
            # the new values (might be a duration change/reason change)
            existing_ban.update(ban)
            ban = existing_ban
            
        self._flush_ban(ban)

        if existing_ban is None:
            self.bans.append(ban)

        return ban

    def delete_ban(self, cid):
        """
        Remove a player's ban. We just need the player's cid to do this. Don't
        care who removed it. Note that all we are doing is setting expired to True
        """
        pass

    def _get_player_ban(self, cid):
        # Try find a ban matching the given cid. We check banned_cid
        for b in self.bans:
            if b["banned_cid"] == cid:
                return b

        return None

    def _flush_ban(self, ban):
        self.db.flush_ban(ban)


    def __load_bans(self):
        """
        Bans are only loaded on server start. From that point, it is assumed
        bans are managed entirely by this class. Hence, the database state will
        consistent with the stored state in this manager.
        """
        del self.bans[:]

        bans = self.db.get_bans()

        self.bans = [ Ban(x) for x in bans ]


