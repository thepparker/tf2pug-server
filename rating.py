
K_table = {
    "2": 6,
    "1.9": 7,
    "1.8": 8,
    "1.7": 10,
    "1.6": 16,
    "1.5": 24,
    "1.4": 32
}

def K_lookup(self, rating):
    rating = float(rating)

    lookup_key = round(rating/1000, 1)
    if lookup_key > 2:
        lookup_key = 2
    if lookup_key < 1.4:
        lookup_key = 1.4

    return K_table[str(lookup_key)]


MU = 1500

WIN = 1
LOSS = 0
DRAW = 0.5

class Rating(object):
    def __init__(self, rating):
        self.rating = rating

    def __int__(self):
        return int(self.rating)
    
    def __long__(self):
        return long(self.rating)
    
    def __float__(self):
        return float(self.rating)

    def __repr__(self):
        t = type(self)
        return "%s(rating = %0.2f)" % (".".join([t.__module__, t.__name__]), self.rating)

class EloDuel(object):
    def __init__(self, mu = MU):
        self.mu = mu

    def new_rating(self, rating=None):
        if rating is None:
            return Rating(self.mu)

        else:
            return Rating(rating)

    def calculate_rating(self, teams, rank):
        for team in teams:
            # team is a list of Rating objects
            for p in team_players:
                p_rating = pug.player_stats[p]["rating"]
                # we need to do some lookup to find the K-factor for these
                # players. always use the winner's K-factor, or in the case of
                # a draw, the lower player's K-factor
                K_factor = K(1500) # default K-factor

                duel_sum = 0
                for e in opponent_players:
                    e_rating = pug.player_stats[e]["rating"]
                    expected_score = 1/(1+10^((e_rating-p_rating)/400)) # 0 < E < 1

                    if actual_score == 1:
                        # current player's K factor
                        K_factor = K(p_rating)
                    elif actual_score == 0:
                        # use the opponent's K-factor
                        K_factor = K(e_rating)
                    elif p_rating > e_rating:
                        # who ever has the lowest rating's K-factor
                        K_factor = K(e_rating)
                    else:
                        K_factor = K(p_rating)

                    rating_gain = K_factor*(actual_score-expected_score)

                    duel_sum += rating_gain

                new_rating = p_rating + duel_sum/len(opponent_players)

