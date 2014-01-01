
import collections
import time
import calendar

states = {
    "GATHERING_PLAYERS": 0,
    "MAP_VOTING": 1,
    "MAPVOTE_COMPLETED": 2,
    "GAME_STARTED": 3,
    "GAME_OVER": 4
}

MAPVOTE_DURATION = 60

def rounded_ctime():
    return calendar.timegm(time.gmtime())

# Raised when trying to start a map vote when the map has been forced
class MapForcedException(Exception):
    pass

class Pug(object):
    def __init__(self, pid, size, pmap):
        self.id = pid
        self.size = size
        self.map = pmap

        if pmap is not None:
            self.map_forced = True
        else:
            self.map_forced = False

        self._players = collections.OrderedDict()

        self.player_votes = {}
        self.map_votes = {}
        self.map_vote_start = -1
        self.map_vote_end = -1

        self.ip = "1.1.1.1"
        self.port = 22222
        self.password = 123

        self.state = states["GATHERING_PLAYERS"]

        self.team_red = []
        self.team_blue = []

    def add_player(self, player_id, player_name):
        self._players[player_id] = player_name

    def remove_player(self, player_id):
        if player_id in self._players:
            del self._players[player_id]

    def begin_map_vote(self):
        if self.map_forced:
            raise MapForcedException("Cannot begin vote when the map is forced")

        # we store the map vote start and end times. this way, clients can know
        # when they need to update the pug's status again after a map vote
        self.map_vote_start = rounded_ctime()
        self.map_vote_end = self.map_vote_start + MAPVOTE_DURATION

        self.state = states["MAP_VOTING"]

    def end_map_vote(self):
        sorted_votes = sorted(self.map_votes.keys(), key = lambda m: self.map_votes[m], reverse = True)

        self.map = sorted_votes[0]

        self.state = states["MAPVOTE_COMPLETED"]

    def vote_map(self, player_id, map_name):
        if self.state != states["MAP_VOTING"]:
            return

        if player_id in self.player_votes:
            # ignore votes if they're the same map
            if map_name == self.player_votes[player_id]:
                return

            # decrement the vote count of the previously voted map, increment
            # the newly voted map and set the player's voted map to the new map
            self._decrement_map_vote(self.player_votes[player_id])
            self._increment_map_vote(map_name)
            self.player_votes[player_id] = map_name

        else:
            # player hasn't voted yet, just increment their vote and set the
            # voted map
            self._increment_map_vote(map_name)
            self.player_votes[player_id] = map_name

    def _increment_map_vote(self, map_name):
        if map_name in self.map_votes:
            self.map_votes[map_name] += 1
        else:
            self.map_votes[map_name] = 1

    def _decrement_map_vote(self, map_name):
        if map_name in self.map_votes:
            self.map_votes[map_name] -= 1

            if self.map_votes[map_name] < 0:
                self.map_votes[map_name] = 0

        else:
            self.map_votes[map_name] = 0

    def shuffle_teams(self):
        pass

    def has_player(self, player_id):
        return player_id in self._players

    @property
    def full(self):
        return self.size == len(self._players)

    @property
    def admin(self):
        return self._players.keys()[0]

    @property
    def player_count(self):
        return len(self._players)
