import sys
sys.path.append('..')

#import logging
#logging.basicConfig(level=logging.DEBUG)

import unittest
import psycopg2.pool

import settings

from puglib.PugManager import PugManager
from puglib.bans import BanManager
from entities.Pug import Pug
import puglib.Exceptions as PMEx
from interfaces import PSQLDatabaseInterface
from serverlib.ServerManager import ServerManager

class ManagerTestCase(unittest.TestCase):
    def setUp(self):
        PugManager.__load_pugs = lambda: None
        dsn = "dbname=%s user=%s password=%s host=%s port=%s" % (
                settings.db_name, settings.db_user, settings.db_pass, 
                settings.db_host, settings.db_port
            )

        self.pool = psycopg2.pool.SimpleConnectionPool(minconn = 1, maxconn = 1,
            dsn = dsn)

        self.db = PSQLDatabaseInterface(self.pool)
        
        self.sm = ServerManager(1, self.db)
        self.bm = BanManager(self.db)

        self.pm = PugManager("123abc", self.db, self.sm, self.bm)

        # clear any loaded pugs out; don't want to touch them
        self.pm._pugs = []

        # make these functions do nothing significant
        def flush_override(v):
            v.id = 1

        self.pm._flush_pug = flush_override
        self.bm._flush_ban = flush_override
        self.sm._flush_server = lambda s: None

    def tearDown(self):
        self.pool.closeall()

def fill_pug(m, pug):
    for i in range(2, pug.size+1):
        m.add_player(i, str(i), pug.id)

class CreatePugTest(ManagerTestCase):
    def test_create_pug(self):
        pug = self.pm.create_pug(1, "1")
        self.assertTrue(isinstance(pug, Pug))
        self.assertListEqual(self.pm._pugs, [ pug ])

    def test_end_pug(self):
        pug = self.pm.create_pug(1, "1")

        self.pm._end_pug(pug)
        self.assertListEqual(self.pm._pugs, [])

    def test_create_banned_player(self):
        self.bm.add_ban(
            {
                "bannee": {
                    "id": 1,
                    "name": "1"
                },
                "banner": {
                    "id": 2,
                    "name": "2"
                },

                "reason": "banned",
                "duration": 2
            })

        self.assertRaises(PMEx.PlayerBannedException, 
                          lambda: self.pm.create_pug(1, "1"))

    def test_create_player_in_pug(self):
        pug = self.pm.create_pug(1, "1")

        self.assertRaises(PMEx.PlayerInPugException,
                          lambda: self.pm.create_pug(1, "1"))


    def test_create_player_restricted(self):
        # base elo is 1500, so check for restriction above and below
        self.assertRaises(PMEx.PlayerRestrictedException, 
                    lambda: self.pm.create_pug(1, "1", restriction = -1400))

        self.assertRaises(PMEx.PlayerRestrictedException,
                    lambda: self.pm.create_pug(1, "1", restriction = 1600))


    def test_no_servers_available(self):
        pug = self.pm.create_pug(1, "1")

        self.assertRaises(PMEx.NoAvailableServersException,
                          lambda: self.pm.create_pug(2, "2"))

    def test_map_forced(self):
        pug = self.pm.create_pug(1, "1", pug_map = "cp_badlands")
        self.assertTrue(pug.map_forced)
        self.assertEquals(pug.map, "cp_badlands")

    def test_invalid_map_forced(self):
        self.assertRaises(PMEx.InvalidMapException,
                          lambda: self.pm.create_pug(1, "1", pug_map = "NO"))

class PlayerAddRemoveTest(ManagerTestCase):
    def test_add_player_no_pug(self):
        self.assertRaises(PMEx.InvalidPugException,
                          lambda: self.pm.add_player(1, "1", 0))

    def test_remove_player_no_pug(self):
        self.assertRaises(PMEx.PlayerNotInPugException,
                        lambda: self.pm.remove_player(1))

    @unittest.skip("This is tested by CreatePugTest.test_player_restricted")
    def test_add_player_restricted(self):
        pass

    @unittest.skip("This is tested by CreatePugTest.test_create_banned_player")
    def test_add_player_banned(self):
        pass

    @unittest.skip("This is tested by CreatePugTest.test_create_player_in_pug")
    def test_add_player_in_pug(self):
        pass

    def test_add_player(self):
        pug = self.pm.create_pug(1, "1")
        self.assertIn(1, pug.player_list())

        self.pm.add_player(2, "2", pug.id)
        self.assertIn(2, pug.player_list())

    def test_remove_player(self):
        pug = self.pm.create_pug(1, "1")

        self.pm.add_player(2, "2", pug.id)
        self.assertIn(2, pug.player_list())

        self.pm.remove_player(2)
        self.assertNotIn(2, pug.player_list())

    def test_remove_player_pug_empty(self):
        # what we're testing here is automatic pug ending if removing the
        # player empties the pug
        pug = self.pm.create_pug(1, "1")
        self.assertRaises(PMEx.PugEmptyEndException,
                          lambda: self.pm.remove_player(1))

    def test_add_pug_full(self):
        pug = self.pm.create_pug(1, "1")
        fill_pug(self.pm, pug)

        self.assertRaises(PMEx.PugFullException,
                          lambda: self.pm.add_player(13, "13", pug.id))

class MapVoteTest(ManagerTestCase):
    def create_full_pug(self):
        pug = self.pm.create_pug(1, "1")
        fill_pug(self.pm, pug)

        return pug

    def test_vote_begin_transition(self):
        pug = self.create_full_pug()

        self.assertTrue(pug.full)
        self.assertEquals(pug.get_state_string(), "MAP_VOTING")

    def test_vote_map(self):
        pug = self.create_full_pug()

        self.pm.vote_map(1, "cp_granary")
        self.assertIn(1, pug.player_votes)
        self.assertEquals(pug.player_votes[1], "cp_granary")

        self.pm.vote_map(2, "cp_badlands")
        self.assertIn(2, pug.player_votes)
        self.assertEquals(pug.player_votes[2], "cp_badlands")

        self.pm.vote_map(1, "cp_badlands")
        self.assertIn(1, pug.player_votes)
        self.assertEquals(pug.player_votes[1], "cp_badlands")

    def test_vote_invalid_map(self):
        self.create_full_pug()

        self.assertRaises(PMEx.InvalidMapException,
                          lambda: self.pm.vote_map(1, "NO_MAP"))

    def test_vote_not_in_pug(self):
        self.create_full_pug()

        self.assertRaises(PMEx.PlayerNotInPugException,
                          lambda: self.pm.vote_map(13, "cp_badlands"))

    def test_force_map(self):
        pug = self.pm.create_pug(1, "1")

        self.pm.force_map(1, "cp_badlands")

        self.assertTrue(pug.map_forced)
        self.assertEquals(pug.map, "cp_badlands")

        # non-existant pug
        self.assertRaises(PMEx.InvalidPugException,
                          lambda: self.pm.force_map(0, "cp_badlands"))

        # invalid map
        self.assertRaises(PMEx.InvalidMapException,
                          lambda: self.pm.force_map(1, "NO_MAP"))

        # too late to force the map
        pug.map_forced = False
        pug.map = None
        pug.begin_map_vote()
        self.assertRaises(PMEx.ForceMapException,
                          lambda: self.pm.force_map(1, "cp_badlands"))

    def test_vote_end_transition(self):
        pug = self.create_full_pug()

        self.assertEquals(pug.get_state_string(), "MAP_VOTING")

        # make it so that any positive value into status_check triggers
        # end_map_vote for this pug
        pug.map_vote_end = 0
        self.pm.status_check(1)
        self.assertTrue(pug.teams_done)

    def test_map_forced_transition(self):
        pug = self.pm.create_pug(1, "1")
        self.pm.force_map(pug.id, "cp_granary")
        fill_pug(self.pm, pug)

        self.assertEquals(pug.map, "cp_granary")
        self.assertEquals(pug.get_state_string(), "MAPVOTE_COMPLETED")

        self.pm.status_check(1)

        self.assertTrue(pug.teams_done)


def test_suites():
    classes = [ CreatePugTest, PlayerAddRemoveTest, MapVoteTest ]

    return [ unittest.TestLoader().loadTestsFromTestCase(x) for x in classes ]

if __name__ == "__main__":
    unittest.TestSuite(test_suites())

    unittest.main()
