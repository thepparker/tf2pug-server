
import math

K_table = {
    "2": 6,
    "1.9": 7,
    "1.8": 8,
    "1.7": 10,
    "1.6": 16,
    "1.5": 24,
    "1.4": 32
}

def K_lookup(rating):
    rating = float(rating)

    # convert rating to nearest 10, floor it, then convert to nearest 1 with
    # 1 decimal place. i.e 1580/100 = 15.8, floor(15.8) = 15.0, k = 15/10 = 1.5
    lookup_key = math.floor(round(rating/100, 1))/10
    if lookup_key > 2:
        lookup_key = 2
    if lookup_key < 1.4:
        lookup_key = 1.4

    return K_table[str(lookup_key)]

# base rating (start point for everyone)
BASE = 1500

# weight of win/loss/draw
WIN = 1
LOSS = 0
DRAW = 0.5

class Rating(object):
    def __init__(self, rating):
        self.rating = round(rating, 3)

    def __int__(self):
        return int(self.rating)
    
    def __long__(self):
        return long(self.rating)
    
    def __float__(self):
        return float(self.rating)

    def __repr__(self):
        t = type(self)
        return "%s(rating = %0.3f)" % (".".join([t.__module__, t.__name__]), self.rating)

    def __add__(self, other):
        if isinstance(other, Rating):
            return Rating(self.rating + other.rating)
        else:
            raise TypeError("%s cannot add to %s" % (repr(self), repr(other)))

    def __sub__(self, other):
        if isinstance(other, Rating):
            return Rating(self.rating - other.rating)
        else:
            raise TypeError("unsupported operand type(s) for -: '%s' and '%s'" % (
                                type(self).__name__, type(other).__name__))

    def __radd__(self, other):
        return self + other

    def __rsub__(self, other):
        return other - self

    def __gt__(self, other):
        return self.rating > other.rating

    def __lt__(self, other):
        return self.rating < other.rating

    def __eq__(self, other):
        return self.rating == other.rating

    def __ge__(self, other):
        return self.rating >= other.rating

    def __le__(self, other):
        return self.rating <= other.rating


def calculate_rating(teams, rank):
    if len(teams) != len(rank):
        raise ValueError("Dimension mismatch. len(teams) must match len(rank)")

    K = lambda r: K_lookup(r)

    new = [ [] for x in range(len(teams)) ]
    for i, team in enumerate(teams):
        # team is a list of Rating objects
        for j, e_team in enumerate(teams):
            if team == e_team: #skip if same team
                continue

            actual_score = 0
            # rank is reverse sorted (i.e 0,1,2,3), so we need to do this 
            # comparison backwards!
            if rank[i] < rank[j]:
                actual_score = WIN
            elif rank[i] > rank[j]:
                actual_score = LOSS
            else:
                actual_score = DRAW

            for p in team:
                # we need to do some lookup to find the K-factor for these
                # players. always use the winner's K-factor, or in the case of
                # a draw, the lower player's K-factor
                K_factor = K(p) # default K-factor

                duel_sum = 0
                num_e_players = len(e_team)
                for e in e_team:
                    expected_score = 1/(1+math.pow(10,((float(e)-float(p))/400))) # 0 < E < 1

                    if actual_score == LOSS or (actual_score == DRAW and p > e):
                        # if p team lost => use the opponent's K-factor.
                        # or, if draw and p rating > e rating, use e rating
                        # because it's the smallest
                        K_factor = K(e)

                    rating_gain = K_factor*(actual_score-expected_score)

                    duel_sum += rating_gain

                new_rating = float(p) + duel_sum/num_e_players
                new[i].append(Rating(new_rating))

    # make new teams immutable
    new = [ tuple(x) for x in new ]

    return new

