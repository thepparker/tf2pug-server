
import collections
import time
import calendar
import random
import logging

states = {
    "GATHERING_PLAYERS": 0,
    "MAP_VOTING": 1,
    "MAPVOTE_COMPLETED": 2,
    "TEAMS_SHUFFLED": 3,
    "GAME_STARTED": 4,
    "GAME_OVER": 5
}

MAPVOTE_DURATION = 2

def rounded_ctime():
    return calendar.timegm(time.gmtime())

# Raised when trying to start a map vote when the map has been forced
class MapForcedException(Exception):
    pass

class Pug(object):
    def __init__(self, pid = None, size = 12, pmap = None):
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
        self._players = {}
        self.player_stats = {}

        self.player_votes = {}
        self.map_votes = {}
        self.map_vote_start = -1
        self.map_vote_end = -1
        self.map_vote_duration = MAPVOTE_DURATION
        self.maps = [ u"cp_granary", u"cp_badlands" ]

        self.server = None
        self.server_id = -1

        self.password = None

        self.teams = {
            "red": [],
            "blue": []
        }

        self.team_ratings = {
            "red": 0,
            "blue": 0
        }

        self.game_scores = {
            "red": 0,
            "blue": 0
        }

        self.medics = {
            "red": -1,
            "blue": -1
        }

    def add_player(self, player_id, player_name):
        if self.full:
            return

        if self.player_count == 0:
            self.admin = player_id

        self._players[player_id] = player_name

    """
    Add a player to the specified team list. Player can also be a list, as
    per __allocate_players.
    """
    def __add_to_team(self, team, player):
        if isinstance(player, list):
            self.teams[team] += player
        else:
            self.teams[team].append(player)

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
        if self.map_forced:
            self.state = states["MAPVOTE_COMPLETED"]
            return

        sorted_votes = sorted(self.map_votes.keys(), key = lambda m: self.map_votes[m], reverse = True)

        if len(sorted_votes) > 0:
            self.map = sorted_votes[0]
        
        else:
            # no one voted for a map, pick 1 at random
            self.map = random.choice(self.maps)

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
        if not self.full or self.teams_done:
            return

        # keep all player stats for rating updating post-game
        self.player_stats = stat_data

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

        medics = []
        for team in self.teams:
            medic = potential_medics.pop()

            self.team_ratings[team] += stat_data[medic]["rating"]
            self.medics[team] = medic
            self.__add_to_team(team, medic)
            medics.append(medic)

        logging.debug("Medics - Red: %s Blue: %s. Now calculating the rest of team", 
                        self.medics["red"], self.medics["blue"])

        # now we can sort by score. we'll get a list of sorted ids out
        # in order of highest score to lowest
        sorted_ids = sorted(stat_data, key = lambda k: stat_data[k]["rating"], reverse = True)
        
        # remove the medics from the sorted ids, so we don't process them again
        # when allocating the rest of the players
        player_ids = [ x for x in sorted_ids if x not in medics ]

        # now just setup the teams. SIMPLE, RIGHT? WRONG
        self.__allocate_players(player_ids, stat_data)

        self.state = states["TEAMS_SHUFFLED"]

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
                red_score += stat_data[pid]["rating"]

            else:
                blue.append(pid)
                blue_score += stat_data[pid]["rating"]

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
                new_red_score = red_score - stat_data[pred]["rating"] + stat_data[pblue]["rating"]
                new_blue_score = blue_score + stat_data[pred]["rating"] - stat_data[pblue]["rating"]
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
        self.__add_to_team("red", red)
        self.__add_to_team("blue", blue)

        self.team_ratings["red"] += red_score
        self.team_ratings["blue"] += blue_score

        logging.info("Team allocation complete. Red: %s (Score: %s), Blue: %s (Score: %s)", 
                        self.teams["red"], red_score, self.teams["blue"], blue_score)

    def begin_game(self):
        if not self.game_started:
            self.state = states["GAME_STARTED"]

        else:
            pass

    def update_score(self, team, score):
        self.game_scores[team] = score

    def end_game(self):
        self.state = states["GAME_OVER"]
        # do we need to do anything else here..? rest is handled by the manager

    def has_player(self, player_id):
        return player_id in self._players

    def player_list(self):
        return self._players.keys()

    def is_admin(self, pid):
        return self.admin == pid

    def named_teams(self):
        """
        Returns a dictionary containing player names along with role for each 
        team instead of just cids
        """
        named = {}
        for team in self.teams:
            named[team] = [ (self.player_name(x), self.player_role(x)) for x in self.teams[team] ]

        return named

    def player_role(self, pid):
        if pid in self.medics.values():
            return "Medic"
        
        else:
            return None

    def player_name(self, pid):
        if pid in self._players:
            return self._players[pid]

    @property
    def teams_done(self):
        return self.state >= states["TEAMS_SHUFFLED"]

    @property
    def full(self):
        return self.size == self.player_count

    @property
    def player_count(self):
        return len(self._players)

    @property
    def game_started(self):
        return self.state == states["GAME_STARTED"]

    @property
    def game_over(self):
        return self.state == states["GAME_OVER"]

