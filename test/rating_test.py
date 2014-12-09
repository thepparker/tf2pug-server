import sys
sys.path.append('../puglib')

from rating import *

import random
from pprint import pprint
import math

def test_rating():
    assert Rating(1) == Rating(1)
    assert Rating(1) <= Rating(2)
    assert Rating(1) != Rating(2)
    assert Rating(3) >= Rating(2)
    assert Rating(4) > Rating(3)
    assert Rating(3) < Rating(4)

    assert Rating(2) + Rating(2) == Rating(4)
    assert Rating(4) - Rating(2) == Rating(2)

def rate_4v4_1500():
    # test 4v4 with all in 1.5 tier
    team1 = [ Rating(1570+x) for x in range(4) ]
    team2 = [ Rating(1500+20*x) for x in range(4) ]
    
    assert calculate_rating([team1, team2], [0, 1]) == [
            (Rating(rating = 1580.630), Rating(rating = 1581.596), 
                Rating(rating = 1582.562), Rating(rating = 1583.528)), 
            (Rating(rating = 1490.435), Rating(rating = 1509.766), 
                Rating(rating = 1529.085), Rating(rating = 1548.397))
        ]

    assert calculate_rating([team1, team2], [1, 0]) == [
            (Rating(rating = 1556.630), Rating(rating = 1557.596), 
                Rating(rating = 1558.562), Rating(rating = 1559.528)), 
            (Rating(rating = 1514.435), Rating(rating = 1533.766), 
                Rating(rating = 1553.085), Rating(rating = 1572.397))
        ]

    assert calculate_rating([team1, team2], [0, 0]) == [
            (Rating(rating = 1568.630), Rating(rating = 1569.596), 
                Rating(rating = 1570.562), Rating(rating = 1571.528)), 
            (Rating(rating = 1502.435), Rating(rating = 1521.766), 
                Rating(rating = 1541.085), Rating(rating = 1560.397))
        ]

def rate_6v6_all_1500():
    # test 6v6 with all same rating
    team1 = [ Rating(1500) for x in range(6) ]
    team2 = [ Rating(1500) for x in range(6) ]

    calculate_rating([ team1, team2 ], [0, 1])

def rate_5v6_random():
    # Test rating when teams are uneven at the end of the match
    print "Rating 5v6 (random rating)"
    team1 = [ Rating(random.randrange(1400, 1700)) for x in range(6) ]
    team2 = [ Rating(random.randrange(1400, 1700)) for x in range(5) ]

    # First just check for zero-sum equality with random ratings
    new_ratings = calculate_rating([ team1, team2 ], [1, 0])

    team1_change = float(sum(new_ratings[0]) - sum(team1))
    team2_change = float(sum(new_ratings[1]) - sum(team2))

    print "Rating change for random elo - Team 1: {0}. Team2: {1}".format(
                team1_change, team2_change)

    assert math.floor(abs(team1_change)) == math.floor(abs(team2_change))

    # Can't check rating equality here because of floating point inaccuracies
    # assert new_ratings = []

def rate_5v6_equal():
    print "Rating 5v6 (all ELO equal) - Team 2 Win"
    # Now we'll check zero-sum equality AND rating equality, since we have
    # known values
    team1 = [ Rating(1500) for x in range(6) ]
    team2 = [ Rating(1500) for x in range(5) ]

    new_ratings = calculate_rating([ team1, team2 ], [1, 0])
    team1_change = float(sum(new_ratings[0]) - sum(team1))
    team2_change = float(sum(new_ratings[1]) - sum(team2))

    print "Rating change for constant elo - Team 1: {0}. Team2: {1}".format(
                team1_change, team2_change)

    assert abs(team1_change) == abs(team2_change)
    
    assert new_ratings == [
            (Rating(rating = 1495.000), Rating(rating = 1495.000),
             Rating(rating = 1495.000), Rating(rating = 1495.000),
             Rating(rating = 1495.000), Rating(rating = 1495.000)),
            (Rating(rating = 1506.000), Rating(rating = 1506.000),
             Rating(rating = 1506.000), Rating(rating = 1506.000),
             Rating(rating = 1506.000))
        ]

    print "Rating 5v6 (all ELO equal) - Team 1 Win"
    new_ratings = calculate_rating([ team1, team2 ], [0, 1])
    team1_change = float(sum(new_ratings[0]) - sum(team1))
    team2_change = float(sum(new_ratings[1]) - sum(team2))

    print "Rating change for constant elo - Team 1: {0}. Team2: {1}".format(
                team1_change, team2_change)

    assert abs(team1_change) == abs(team2_change)

    assert new_ratings == [
            (Rating(rating = 1505.000), Rating(rating = 1505.000),
             Rating(rating = 1505.000), Rating(rating = 1505.000),
             Rating(rating = 1505.000), Rating(rating = 1505.000)),
            (Rating(rating = 1494.000), Rating(rating = 1494.000),
             Rating(rating = 1494.000), Rating(rating = 1494.000),
             Rating(rating = 1494.000))
        ]
    
def rate_5v6_nonequal_draw():
    team1 = [ Rating(1500+5*x) for x in range(6) ]
    team2 = [ Rating(1500+20+x) for x in range(5) ]

    new_ratings = calculate_rating([ team1, team2 ], [0, 0])

    team1_change = float(sum(new_ratings[0]) - sum(team1))
    team2_change = float(sum(new_ratings[1]) - sum(team2))

    print "Rating change for 5v6 draw - Team 1: {0}. Team2: {1}".format(
                team1_change, team2_change)

    assert math.floor(abs(team1_change)) == math.floor(abs(team2_change))

    assert new_ratings == [
            (Rating(rating = 1500.316), Rating(rating = 1505.244),
             Rating(rating = 1510.173), Rating(rating = 1515.101),
             Rating(rating = 1520.029), Rating(rating = 1524.957)),
            (Rating(rating = 1519.871), Rating(rating = 1520.853),
             Rating(rating = 1521.836), Rating(rating = 1522.819),
             Rating(rating = 1523.802))
        ]


def rate_1v1_cross_tier():
    team1 = [ Rating(1850) ]
    team2 = [ Rating(1750) ]

    assert calculate_rating([team1, team2], [1, 0]) == [
            (Rating(rating = 1843.599),), 
            (Rating(rating = 1756.401),)
        ]

    assert calculate_rating([team1, team2], [0, 1]) == [
            (Rating(rating = 1852.879),), 
            (Rating(rating = 1747.121),)
        ]

    assert calculate_rating([team1, team2], [0, 0]) == [
            (Rating(rating = 1848.599),), 
            (Rating(rating = 1751.401),)
        ]

def test():
    test_rating()
    rate_4v4_1500()
    rate_1v1_cross_tier()
    rate_5v6_random()
    rate_5v6_equal()
    rate_5v6_nonequal_draw()

if __name__ == "__main__":
    test()

