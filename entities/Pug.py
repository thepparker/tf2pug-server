
import time
import random
import logging
import collections

from puglib import rating

states = {
    "GATHERING_PLAYERS": 0,
    "MAP_VOTING": 1,
    "MAPVOTE_COMPLETED": 2,
    "TEAMS_SHUFFLED": 3,
    "GAME_STARTED": 4,
    "REPLACEMENT_REQUIRED": 5,
    "GAME_OVER": 6
}

MAPVOTE_DURATION = 30
AVAILABLE_MAPS = [ u"cp_granary", u"cp_badlands" ]

# Raised when trying to start a map vote when the map has been forced
class MapForcedException(Exception):
    pass

class PlayerStats(dict):
    """
    A simple class to wrap base player stats, and allow for the easy addition
    of new player stats. Since player stats are stored as a JSON string in the
    database, we can just use json.loads() to load the dict, and then pass it 
    to this constructor. Any stat set in the database will be restored, and any
    new stats will be initialized. Likewise, stats can be added by other
    objects (such as the parser), and they will be reflected in this object
    without us needing to do anything special.
    """

    # special stats are stats that are not incremented in update_end_stats,
    # they are set to whatever value is in the game stats dict
    SPECIAL_STATS = ("rating", "winstreak")

    def __init__(self, *args, **kwargs):
        # Set the base stats, and then super to restore any stats from the
        # database
        self["games_since_medic"] = 0
        self["games_played"] = 0
        self["rating"] = rating.BASE
        self["kills"] = 0
        self["deaths"] = 0
        self["assists"] = 0
        self["wins"] = 0
        self["losses"] = 0
        self["draws"] = 0
        self["winstreak"] = 0

        super(PlayerStats, self).__init__(*args, **kwargs)

class Pug(object):
    def __init__(self, pid = None, custom_id = None, size = 12, pmap = None,
                 restriction = None):
        self.id = pid
        self.custom_id = custom_id
        self.size = size
        self.state = states["GATHERING_PLAYERS"]
        self._previous_state = self.state
        self.start_time = time.time()

        self.map = pmap

        if pmap is not None:
            self.map_forced = True
        else:
            self.map_forced = False

        self.admin = None
        #players is a dict in the form { cid: "name", ... }
        self._players = {}
        self.player_stats = {} # stats before game
        self.game_stats = {} # stats obtained during this pug
        self.end_stats = {} # stats after game
        self.player_restriction = restriction # rating restriction

        self.player_votes = {}
        self.map_vote_start = -1
        self.map_vote_end = -1
        self.map_vote_duration = MAPVOTE_DURATION
        self.maps = AVAILABLE_MAPS

        self.server = None
        self.server_id = -1

        self.teams = {
            "red": set(),
            "blue": set()
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
            "red": 0,
            "blue": 0
        }

    def add_player(self, player_id, player_name, pstats):
        if self.full:
            return

        if self.player_count == 0:
            self.admin = player_id

        self._players[player_id] = player_name

        self.player_stats[player_id] = pstats
        self._get_game_stats(player_id)

        if self.state == states["REPLACEMENT_REQUIRED"]:
            self.state = self._previous_state

    """
    Add a player to the specified team list. Player can also be a list, as
    per __allocate_players.
    """
    def _add_to_team(self, team, player):
        if isinstance(player, list):
            self.teams[team] |= set(player)
        else:
            self.teams[team].add(player)

    def _remove_from_team(self, team, player):
        if isinstance(player, list):
            self.teams[team] -= set(player)
        else:
            self.teams[team].add(player)

    def remove_player(self, player_id):
        if player_id in self._players:
            del self._players[player_id]

            # update the admin to the next person in the pug
            if player_id == self.admin and self.player_count > 0:
                self.admin = self._players.keys()[0]

            # remove this player's stats
            del self.player_stats[player_id]
            del self.game_stats[player_id]

            # if the game is in progress, we need to change the state to 
            # replacement needed. we store the previous state so we can go
            # back to it if we get a replacement
            if self.state >= 1:
                self._previous_state = self.state
                self.state = states["REPLACEMENT_REQUIRED"]

        if player_id in self.player_votes:
            del self.player_votes[player_id]

    def begin_map_vote(self):
        if self.map_forced:
            self.state = states["MAPVOTE_COMPLETED"]

        else:
            # we store the map vote start and end times. this way, clients can know
            # when they need to update the pug's status again after a map vote
            self.map_vote_start = time.time()
            self.map_vote_end = self.map_vote_start + MAPVOTE_DURATION

            self.state = states["MAP_VOTING"]

    def end_map_vote(self):
        if self.map_forced:
            self.state = states["MAPVOTE_COMPLETED"]
            return

        if len(self.map_votes) > 0:
            self.map = self.map_votes.most_common(1)[0][0]
        
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
            self.player_votes[player_id] = map_name

        else:
            self.player_votes[player_id] = map_name

    def force_map(self, map_name):
        self.map_forced = True
        self.map = map_name

    def shuffle_teams(self):
        if not self.full or self.teams_done:
            return

        stat_data = self.player_stats

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
                if stat_data[cid]["games_since_medic"] > threshold and cid not in potential_medics:
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
            self._add_to_team(team, medic)
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
        self._add_to_team("red", red)
        self._add_to_team("blue", blue)

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

    def update_end_stats(self):
        # merge the game stats with the pre-game stats to get player's new
        # total stats

        # wins, losses, draws, games played. we just set these to 1, and 
        # they'll be incremented when we update with previous stats.
        team1, team2 = self.teams.keys()
        opposition = { team1: team2, team2: team1 } 
        for cid in self.game_stats:
            player_team = None
            for team in self.teams:
                if cid in self.teams[team]:
                    player_team = team
                    break

            team_score = self.game_scores[player_team]
            oppo_score = self.game_scores[opposition[player_team]]

            game_stat = self.game_stats[cid]
            pregame = self.player_stats[cid]

            if team_score > oppo_score: # this player won!
                game_stat["wins"] = 1

                # adjust win streak
                if pregame["winstreak"] < 0:
                    game_stat["winstreak"] = 1
                else:
                    game_stat["winstreak"] = pregame["winstreak"] + 1

            elif team_score < oppo_score: # player lost
                game_stat["losses"] = 1

                if pregame["winstreak"] < 0:
                    game_stat["winstreak"] = pregame["winstreak"] - 1
                else:
                    game_stat["winstreak"] = -1

            else: # draw
                game_stat["draws"] = 1
                game_stat["winstreak"] = 0

            game_stat["games_played"] = 1

            if cid not in self.medics.values():
                game_stat["games_since_medic"] = 1

            # update all other stats
            if cid not in self.player_stats: # don't have player pre-game stats
                self.end_stats[cid] = game_stat
                continue

            else:
                self.end_stats[cid] = PlayerStats()

            endgame = self.end_stats[cid]

            for stat, value in game_stat.iteritems():
                # if the stat existed before the game, just add to it. else,
                # we set it as new
                if stat in PlayerStats.SPECIAL_STATS:
                    endgame[stat] = value

                elif stat in pregame:
                    endgame[stat] = pregame[stat] + value

                else:
                    endgame[stat] = value

        # update games_since_medic for medics (i.e set to 0)
        for medic in self.medics.values():
            if medic in self.end_stats:
                self.end_stats[medic]["games_since_medic"] = 0

    def has_player(self, player_id):
        return player_id in self._players

    def player_restricted(self, rating):
        """
        Checks whether the given rating is within the allowed range for this
        pug. Restrictions are limits, and set such that a number < 0 means the
        player must have rating below the absolute value of the restriction,
        and a number > 0 means the player must have a rating equal to or above
        the rating.

        If the player is outside of the set range, they are considered to be
        restricted, and we return True.
        """
        if self.player_restriction is None:
            return False

        elif (self.player_restriction < 0
              and rating >= abs(self.player_restriction)):

            return True

        elif (self.player_restriction > 0 
              and rating < self.player_restriction):

            return True

        else:
            return False

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

    def get_state_string(self):
        for name, enum in states.items():
            if enum == self.state:
                return name

    def update_game_stat(self, player_id, statkey, value, increment = True):
        ps = self._get_game_stats(player_id)

        if (not increment) or (statkey not in ps):
            ps[statkey] = value

        else:
            ps[statkey] += value

    def _get_game_stats(self, player_id):
        if player_id in self.game_stats:
            return self.game_stats[player_id]

        else:
            rating_default = self.player_stats[player_id]["rating"] or rating.BASE

            new = PlayerStats(rating = rating_default)
            self.game_stats[player_id] = new

            return new

    def set_player_rating(self, player_id, rating):
        """
        Used by pug manager when updating ratings to set the player's new
        rating after the game.
        """
        if player_id in self.end_stats:
            self.end_stats[player_id]["rating"] = rating

    @staticmethod
    def map_available(map_name):
        return map_name in AVAILABLE_MAPS

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
        return self.state >= states["GAME_STARTED"]

    @property
    def game_over(self):
        return self.state == states["GAME_OVER"]

    @property
    def password(self):
        if self.server is None:
            return None
        else:
            return self.server.password

    @property
    def map_votes(self):
        return collections.Counter(self.player_votes.values())
