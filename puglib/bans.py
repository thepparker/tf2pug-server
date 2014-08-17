import calendar
import time

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
        self["ban_start_time"] = calendar.timegm(time.gmtime())
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
                self["ban_start_time"], self["ban_duration"], self["reason"],
                self["expired"])

    @property
    def duration(self):
        return self["ban_duration"]

    @property(self):
    def expired(self):
        return self["expired"]

class BanManager(object):
    def __init__(self, db):
        self.db = db

        self.bans = []

    def add_ban(self):
        pass
