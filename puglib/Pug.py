
import collections

class Pug(object):
    def __init__(self, pid, size, pmap):
        self.id = pid
        self.size = size
        self.map = pmap

        self._players = collections.OrderedDict()

        self.player_votes = {}
        self.map_votes = {}

        self.ip = "1.1.1.1"
        self.port = 22222
        self.password = 123

    def add_player(self, player_id, player_name):
        self._players[player_id] = player_name

    def remove_player(self, player_id):
        if player_id in self._players:
            del self._players[player_id]

    def vote_map(self, player_id, map_name):
        pass

    def has_player(self, player_id):
        return player_id in self._players

    @property
    def full(self):
        return self.size == len(self._players)

    @property
    def starter(self):
        return self._players.keys()[0]

    @property
    def player_count(self):
        return len(self._players)
