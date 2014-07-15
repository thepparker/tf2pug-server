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

def rate_4v4_1500():
    # test 4v4 with all in 1.5 tier
    team1 = [ Rating(1570+x) for x in range(4) ]
    team2 = [ Rating(1500+20*x) for x in range(4) ]
    
    print (team1,team2)
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

def rate_1v1_cross_tier():
    team1 = [ Rating(1850) ]
    team2 = [ Rating(1750) ]

    print (team1, team2)
    print calculate_rating([team1, team2], [1, 0])

test_rating()
rate_4v4_1500()
rate_1v1_cross_tier()
