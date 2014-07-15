from rating import *

def test_rating():
    assert Rating(1) == Rating(1)
    assert Rating(1) <= Rating(2)
    assert Rating(1) != Rating(2)
    assert Rating(3) >= Rating(2)
    assert Rating(4) > Rating(3)
    assert Rating(3) < Rating(4)

def rate_4v4():
    team1 = [ Rating(1530+x) for x in range(4) ]
    team2 = [ Rating(1460+20*x) for x in range(4) ]
    
    print calculate_rating([team1, team2], [0, 1])

rate_4v4()

