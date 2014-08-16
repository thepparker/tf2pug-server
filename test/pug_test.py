"""
Test case for pug methods such as shuffle_teams, update_end_stats, map voting,
player restriction, updating game stats, etc.
"""

import sys
import logging
sys.path.append('..')
logging.basicConfig(level=logging.DEBUG)

from entities import Pug
from entities.Pug import PlayerStats

def test_add_player():
    print "Testing add_player"
    pug = Pug.Pug()
    pug.add_player(1L, "1", PlayerStats())
    assert 1L in pug._players
    assert 1L in pug.player_stats
    assert 1L in pug.game_stats

def test_remove_player():
    print "Testing remove_player"
    pug = Pug.Pug()
    pug.add_player(1L, "1", PlayerStats())

    # we need to make sure the map vote is removed too
    pug.begin_map_vote()
    pug.vote_map(1L, "cp_badlands")

    pug.remove_player(1L)
    assert 1L not in pug._players
    assert 1L not in pug.player_stats
    assert 1L not in pug.game_stats
    assert 1L not in pug.player_votes

def test_add_to_team():
    print "Testing add_to_team"
    pug = Pug.Pug()
    pug._add_to_team("blue", 1L)
    assert pug.teams["blue"] == set([ 1L ])
    pug._add_to_team("blue", [2L, 3L])
    assert pug.teams["blue"] == set([ 1L, 2L, 3L ])

def test_remove_from_team():
    print "Testing remove_from_team"
    pug = Pug.Pug()
    pug._add_to_team("blue", [ 1L, 2L, 3L ])
    
    pug._remove_from_team("blue", [ 1L ])
    assert pug.teams["blue"] == set([ 2L, 3L ])

    pug._remove_from_team("blue", [ 2L, 3L ])
    assert pug.teams["blue"] == set([])

def fill_pug():
    pug = Pug.Pug()
    pid = 1L
    while not pug.full:
        pug.add_player(pid, str(pid), PlayerStats())

    assert pug.full == True

    return pug

def test_shuffle_teams():
    print "Testing team creation (shuffle)"
    pug = fill_Pug.Pug()

    pug.shuffle_teams()

def test_map_vote():
    print "Testing map vote with player vote"
    pug = Pug.Pug()
    pug.add_player(1, str(1), PlayerStats())

    pug.begin_map_vote()
    assert pug.state == Pug.states["MAP_VOTING"]
    last_map = ""
    for m in pug.maps: 
        pug.vote_map(1, m)
        assert pug.player_votes[1] == m
        assert len(pug.map_votes) > 0
        assert pug.map_votes.most_common(1)[0] == (m, 1)
        last_map = m

    pug.end_map_vote()
    assert pug.state == Pug.states["MAPVOTE_COMPLETED"]
    assert pug.map == last_map

    #------------------------------------------------------
    print "Testing map vote with no vote"
    pug = Pug.Pug()
    pug.begin_map_vote()
    assert pug.state == Pug.states["MAP_VOTING"]
    pug.end_map_vote()
    assert pug.state == Pug.states["MAPVOTE_COMPLETED"]
    assert pug.map is not None

    #------------------------------------------------------
    print "Testing map vote with forced map"
    pug = Pug.Pug()
    pug.force_map("cp_granary")
    pug.begin_map_vote()
    assert pug.state == Pug.states["MAPVOTE_COMPLETED"]
    assert pug.map == "cp_granary"

    pug = Pug.Pug()
    pug.begin_map_vote()
    assert pug.state == Pug.states["MAP_VOTING"]
    
    pug.force_map("cp_granary")
    pug.end_map_vote()
    assert pug.state == Pug.states["MAPVOTE_COMPLETED"]
    assert pug.map == "cp_granary"

def test_update_score():
    print "Testing team score update"
    pug = Pug.Pug()
    assert pug.game_scores["blue"] == pug.game_scores["red"] == 0

    pug.update_score("blue", 2)
    assert pug.game_scores["blue"] == 2
    assert pug.game_scores["red"] == 0

    pug.update_score("red", 3)
    assert pug.game_scores["blue"] == 2
    assert pug.game_scores["red"] == 3    

def test_player_restriction():
    pug = Pug.Pug()
    print "Testing player restriction. Min rating: 100"
    pug.player_restriction = 100

    assert pug.player_restricted(120) == False
    assert pug.player_restricted(100) == False
    assert pug.player_restricted(90) == True

    pug.player_restriction = -100
    assert pug.player_restricted(100) == True
    assert pug.player_restricted(120) == True
    assert pug.player_restricted(90) == False

def test_helpers():
    print "Testing helper methods"
    pug = Pug.Pug()
    pug.add_player(1L, "1", PlayerStats())

    assert pug.has_player(1L) == True
    assert pug.player_list() == [ 1L ]
    assert pug.is_admin(1L) == True
    
    assert pug.player_role(1L) is None
    pug.medics["blue"] = 1L
    assert pug.player_role(1L) == "Medic"

    assert pug.player_name(1L) == "1"
    assert pug.get_state_string() == "GATHERING_PLAYERS"

    assert pug.teams_done == False
    assert pug.full == False
    assert pug.player_count == 1
    assert pug.game_started == False
    assert pug.game_over == False
    assert pug.password is None
    assert len(pug.map_votes) == 0

def test_update_game_stats():
    print "Testing game stat update"
    pug = Pug.Pug()
    pug.add_player(1L, "1", PlayerStats())
    
    assert pug.game_stats[1L] == PlayerStats()
    assert pug.game_stats[1L] is pug._get_game_stats(1L)

    assert pug.game_stats[1L]["kills"] == 0

    pug.update_game_stat(1L, "kills", 1)
    assert pug.game_stats[1L]["kills"] == 1

    pug.update_game_stat(1L, "kills", 1)
    assert pug.game_stats[1L]["kills"] == 2

    pug.update_game_stat(1L, "kills", 10, increment = False)
    assert pug.game_stats[1L]["kills"] == 10
    

def test_update_end_stats():
    print "Testing end of game stat update"
    pug = fill_Pug.Pug()

    # add stats to game stats and our own stat dict, merge, then assert
    # they are equal afterwards. fuark

def test():
    test_add_player()
    test_remove_player()
    test_add_to_team()
    test_remove_from_team()
    test_map_vote()
    test_update_score()
    test_player_restriction()
    test_helpers()
    test_update_game_stats()
    
test()
