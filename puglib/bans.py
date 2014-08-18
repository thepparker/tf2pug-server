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
        self["ban_duration"] = None
        self["reason"] = None
        self["expired"] = False

        super(Ban, self).__init__(*args, **kwargs)

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
        if self["ban_duration"] is None or self["ban_duration"] == 0:
            return

        if epoch() > self["ban_start_time"] + self["ban_duration"]:
            self["expired"] = True

    @property
    def duration(self):
        """ Gets ban duration """
        return self["ban_duration"]

    @property
    def expired(self):
        """ Gets the ban's expired status. """
        return self["expired"]
    
    @expired.setter
    def expired(self, value):
        self["expired"] = value

    @property
    def reason(self):
        return self["reason"]

    def __hash__(self):
        return hash(self["id"])


class BanAddException(Exception):
    """ Raised when adding a ban fails """
    pass

class NoBanFoundException(Exception):
    """ Raised when no ban can be found for the given CID """
    pass

class BanManager(object):
    def __init__(self, db):
        self.db = db

        self.bans = set()

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

        ban["banner_cid"] = banner["id"]
        ban["banner_name"] = banner["name"]

        ban["reason"] = ban_data["reason"]
        ban["ban_duration"] = ban_data["duration"]

        try:
            return self._add_ban(ban)
        except:
            raise BanAddException("Unable to add ban")


    def _add_ban(self, ban):
        """
        Internal method for adding ban to database/list
        """
        existing_ban = self.get_player_ban(ban["banned_cid"])
        if existing_ban is not None:
            # If the player already has an existing ban, we just update it with
            # the new values (might be a duration change/reason change)
            ban.id = existing_ban.id # make sure we set the ID or it'll dupe
            existing_ban.update(ban)

            ban = existing_ban
            
        self._flush_ban(ban)

        if existing_ban is None:
            self.bans.add(ban)

        return ban

    def remove_ban(self, cid):
        """
        Public ban removal. Finds ban matching CID and then calls internal
        method
        """
        ban = self.get_player_ban(cid)

        if ban is None:
            raise NoBanFoundException("No ban found for %s" % cid)

        self._remove_ban(ban)

    def _remove_ban(self, ban):
        """
        Internal ban object removal. All we do is set expired to True, flush
        the ban and then remove it from the set.
        """
        ban.expired = True
        self._flush_ban(ban)

        self.bans.remove(ban)

    def get_player_ban(self, cid):
        # Try find a ban matching the given cid. We check banned_cid
        for b in self.bans:
            if b["banned_cid"] == cid:
                return b

        return None

    def _flush_ban(self, ban):
        self.db.flush_ban(ban)


    def check_bans(self):
        """
        Check bans to see if any have expired
        """
        for b in self.bans.copy():
            b.check_expiration()

            if b.expired:
                # ban is expired, need to delete it
                self._remove_ban(b)

    def __load_bans(self):
        """
        Bans are only loaded on server start. From that point, it is assumed
        bans are managed entirely by this class. Hence, the database state will
        consistent with the stored state in this manager.
        """
        self.bans.clear()

        bans = self.db.get_bans()

        for x in bans:
            b = Ban(x)
            self.bans.add(b)

if __name__ == "__main__":
    from pprint import pprint
    """ Some simple tests of ban methods """
    b = Ban()

    print "Ban expired?: " + str(b.expired)
    b.expired = True
    print "Ban expired?: " + str(b.expired)

    class emptydb(object):
        def __init__(self):
            pass

        def flush_ban(self, *args, **kwargs):
            pass
        def get_bans(self, *args, **kwargs):
            return []

    db = emptydb()
    m = BanManager(db)

    new = {
        "bannee": {
            "id": 1,
            "name": "1"
        },
        "banner": {
            "id": 2,
            "name": "2"
        },

        "reason": "banned",
        "duration": 2
    }

    m.add_ban(new)
    print "Getting added ban:"
    b = m.get_player_ban(1)

    pprint(b)

    print "Deleting ban and checking it:"
    m.remove_ban(1)

    b = m.get_player_ban(1)
    pprint(b)

    print "Testing ban expiration"
    # test automatic expiration
    m.add_ban(new)
    b = m.get_player_ban(1)
    pprint(b)

    while not b.expired:
        m.check_bans()

    print "Ban has expired?"
    pprint(b)
    print "Ban still exists? " + str(m.get_player_ban(1))
