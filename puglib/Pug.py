

class Pug(object):
    def __init__(self, pid, size, pmap):
        self.id = pid
        self.size = size
        self.map = pmap

        self._players = {}

        self.player_votes = {}
        self.map_votes = {}

    def add_player(self, player_id, player_name):
        self._players[player_id] = player_name

    def vote_map(self, player_id, map_name):
        pass

    def has_player(self, player_id):
        return player_id in self._players

    @property
    def full(self):
        return self.size == len(self._players)
