
import collections
import time
import calendar
import random
import logging

states = {
    "GATHERING_PLAYERS": 0,
    "MAP_VOTING": 1,
    "MAPVOTE_COMPLETED": 2,
    "GAME_STARTED": 3,
    "GAME_OVER": 4
}

MAPVOTE_DURATION = 2

def rounded_ctime():
    return calendar.timegm(time.gmtime())

# Raised when trying to start a map vote when the map has been forced
class MapForcedException(Exception):
    pass

class Pug(object):
    def __init__(self, pid = -1, size = 12, pmap = None):
        self.id = pid
        self.size = size
        self.state = states["GATHERING_PLAYERS"]

        self.map = pmap

        if pmap is not None:
            self.map_forced = True
        else:
            self.map_forced = False

        self.admin = None
        #players is a dict in the form { cid: "name", ... }
        self._players = collections.OrderedDict()

        self.player_votes = {}
        self.map_votes = {}
        self.map_vote_start = -1
        self.map_vote_end = -1
        self.map_vote_duration = MAPVOTE_DURATION
        self.maps = [ u"cp_granary", u"cp_badlands" ]

        self.server = None
        self.server_id = -1

        self.team_red = []
        self.team_blue = []

        self.medic_red = -1
        self.medic_blue = -1

    def add_player(self, player_id, player_name):
        if self.full:
            return

        if self.player_count == 0:
            self.admin = player_id

        self._players[player_id] = player_name

    def remove_player(self, player_id):
        if player_id in self._players:
            del self._players[player_id]

            # update the admin to the next person in the pug
            if player_id == self.admin and self.player_count > 0:
                self.admin = self._players.keys()[0]

        if player_id in self.player_votes:
            self._decrement_map_vote(self.player_votes[player_id])

            del self.player_votes[player_id]

    def begin_map_vote(self):
        if self.map_forced:
            self.state = states["MAPVOTE_COMPLETED"]

        else:
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
        if self.state != states["MAP_VOTING"] or map_name not in self.maps:
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

    def force_map(self, map_name):
        self.map_forced = True
        self.map = map_name

    def shuffle_teams(self, stat_data):
        if not self.full:
            return

        # To select teams, we have to first select a medic for each team. 
        # After that we need to establish a score for each player and sort 
        # them by it
        
        # To select a medic, we loop over the players in the pug, picking
        # whoever has played more games since last playing medic until we have
        # atleast 2 potential medics. then we randomly pick 2 from the list

        potential_medics = []
        threshold = 4
        # need atleast 2 potential medics
        while len(potential_medics) < 2:
            # add players who have played more games (since last playing medic)
            # than the threshold until we have atleast 2 players. If we don't 
            # get 2 players on the first run, the threshold is decreased to 
            # incorporate more players until eventually the threshold may be 0
            # and every player is a candidate
            for cid in self._players:
                if stat_data[cid]["games_since_med"] > threshold and cid not in potential_medics:
                    potential_medics.append(cid)

            threshold -= 1

        # now we have our potential medics, so we can just shuffle and select them
        random.shuffle(potential_medics)
        logging.debug("Potential medics shuffled: %s", potential_medics)

        self.medic_blue = potential_medics.pop()
        self.medic_red = potential_medics.pop()

        # now that we have our medics, we can remove them from the player stats
        # & calculate player scores
        del stat_data[self.medic_blue]
        del stat_data[self.medic_red]

        # add player scores to the stat data
        total_pr = 0
        for cid in stat_data:
            score = stat_data[cid]["rating"]

            total_pr += score
            logging.debug("PLAYER: %s, SCORE: %s. New total: %s", cid, score, total_pr)

        # now we can sort by score. we'll get a list of sorted ids out
        # in order of highest score to lowest
        sorted_ids = sorted(stat_data, key = lambda k: stat_data[k]["score"], reverse = True)

        # now just setup the teams. SIMPLE, RIGHT? WRONG
        self.team_red.append(self.medic_red)
        self.team_blue.append(self.medic_blue)

        self.__allocate_players(sorted_ids, stat_data)

    def __allocate_players(self, ids, stat_data):
        # each team needs to have approximately total_pr/2 skill rating, or
        # as close to this as possible, in order to be considered even.
        # therefore, we need to iterate over possible team combinations
        # until we have the most even

        red = []
        red_score = 0

        blue = []
        blue_score = 0

        # establish base teams, by alternating the assignment
        count = 0
        for pid in ids:
            if (count % 2) == 0:
                red.append(pid)
                red_score += stat_data[pid]["score"]

            else:
                blue.append(pid)
                blue_score += stat_data[pid]["score"]

            count += 1

        # each possible team now has (self.size/2 - 1) players in it. now 
        # we iterate over both teams and swap if there's an improvement. 
        # much like a quicksort
        curr_score_diff = abs(red_score - blue_score)
        i = 0
        j = 0

        # loop over all red players
        while i < len(red):
            pred = red[i] #the current red player being checked

            # loop over all blue players for each red player. if a swap occurs,
            # we break from this inner loop and move to the next red player
            while j < len(blue):
                pblue = blue[j]
                
                # if we swapped pred and pblue, would the score difference become
                # smaller? if yes, then we should swap them
                new_red_score = red_score - stat_data[pred]["score"] + stat_data[pblue]["score"]
                new_blue_score = blue_score + stat_data[pred]["score"] - stat_data[pblue]["score"]
                new_diff = abs(new_red_score - new_blue_score)

                if new_diff < curr_score_diff:
                    # swap the players, and go onto the next red player
                    red[i] = pblue
                    blue[j] = pred

                    curr_score_diff = new_diff
                    red_score = new_red_score
                    blue_score = new_blue_score

                    logging.debug("%s swapped with %s. new difference: %s", pblue, pred, new_diff)

                    break

                # Swapping these players wouldn't provide an improvement, so
                # we just move onto the next blue player
                j += 1

            i += 1

        # our teams are now as balanced as we're going to get them, so merge
        # the temp teams with the real teams
        self.team_red += red
        self.team_blue += blue

        logging.info("Team allocation complete. Red: %s (Score: %s), Blue: %s (Score: %s)", self.team_red, red_score, self.team_blue, blue_score)

    def _player_score(self, pdata):
        # we need to establish a score for each player. we'll call this the 
        # 'pug rating', or PR
        # the formula is as follows:
        #   (100 + (kills + assists)/deaths + (damage_dealt/1000)/numplayed)^1.2
        score = 100
            
        if pdata["numplayed"] > 0:
            score += (pdata["kills"] + pdata["assists"]) / (pdata["deaths"] if pdata["deaths"] else 1)
            score += (pdata["damage_dealt"] / 1000) / pdata["numplayed"]

        score **= 1.2

        return score


    def has_player(self, player_id):
        return player_id in self._players

    @property
    def full(self):
        return self.size == self.player_count

    @property
    def player_count(self):
        return len(self._players)

    @property
    def players_list(self):
        return self._players.keys()

    @property
    def game_over(self):
        return self.state == states["GAME_OVER"]

