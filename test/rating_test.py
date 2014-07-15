from rating import *

def test_rating():
    assert Rating(1) == Rating(1)
    assert Rating(1) <= Rating(2)
    assert Rating(1) != Rating(2)
    assert Rating(3) >= Rating(2)
    assert Rating(4) > Rating(3)
    assert Rating(3) < Rating(4)

    assert Rating(2) + Rating(2) == Rating(4)
    assert Rating(4) - Rating(2) == Rating(2)

def rate_4v4():
    team1 = [ Rating(1570+x) for x in range(4) ]
    team2 = [ Rating(1500+20*x) for x in range(4) ]
    
    print (team1,team2)
    print calculate_rating([team1, team2], [0, 1])

test_rating()
rate_4v4()

