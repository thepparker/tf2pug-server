import sys
sys.path.append('..')

import unittest
import threading
import socket
import logging

logging.basicConfig(level=logging.DEBUG)

from interfaces import get_log_interface, tflogging
from entities import Server, Pug

from tornado import ioloop


class RconConnection(object):
    def __init__(self, *args):
        pass

    def send_cmd(self, cmd, cb):
        print "SERVER: Command to send: %s" % cmd

    @property
    def closed(self):
        return False

class LoggingTestCase(unittest.TestCase):
    def setUp(self):
        self.server = Server.Server("TF2")

        self.server.rcon_connection = RconConnection()

        self.server.ip = "202.138.3.55"
        self.server.port = 27045
        self.server.rcon_password = "thanksobama"


        self.pug = Pug.Pug(pid = 1)
        # add some players to the pug for stats testing...

        self.pug.add_player(76561197960265729, "1", Pug.PlayerStats())
        self.pug.add_player(76561197960265730, "2", Pug.PlayerStats())
        self.pug.add_player(76561197960265731, "3", Pug.PlayerStats())
        for i in xrange(9):
            stat = Pug.PlayerStats()
            self.pug.add_player(i, str(i), stat)

        self.pug.begin_map_vote()
        self.pug.end_map_vote()
        self.pug.shuffle_teams()

        self.server.reserve(self.pug)
        self.server.prepare()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect(('127.0.0.1', self.server.log_port))

    def tearDown(self):
        self.socket.close()

class VerifyTestCase(unittest.TestCase):
    def setUp(self):
        self.iface = get_log_interface("TF2")(None)

    def tearDown(self):
        pass

    def test_normal_to_secret(self):
        self.assertTrue(self.iface._verify_data("RL"))
        self.assertTrue(self.iface._verify_data("S123L"))
        self.assertFalse(self.iface._verify_data("RL"))

    def test_secret_to_normal(self):
        self.assertTrue(self.iface._verify_data("S123L"))
        self.assertFalse(self.iface._verify_data("RL"))
        self.assertTrue(self.iface._verify_data("S123L"))

    def test_secret(self):
        self.assertTrue(self.iface._verify_data("S123L"))
        self.assertFalse(self.iface._verify_data("S456L"))
        self.assertTrue(self.iface._verify_data("S123L"))

class RegexTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def check_group_match(self, strings, group):
        for s in strings:
            """
            print "REGEXTEST Group: Checking string \"%s\" for group \"%s\"" % (
                s, group)
            """

            re_match = tflogging.check_regex_match(s)
            self.assertNotEquals(re_match, None)

            group, match, expr = re_match

            self.assertEquals(group, group)  

    def test_chat_regex(self):
        s1 = 'L 10/01/2012 - 21:58:09: "1<0><[U:1:2]><Red>" say "!teams"'
        s2 = 'L 10/01/2012 - 21:58:09: "1<0><[U:1:2]><Red>" say_team "!teams"'

        strings = [ s1, s2 ]

        self.check_group_match(strings, "chat")

    def test_round_regex(self):
        s1 = 'L 10/01/2012 - 22:02:34: World triggered "Round_Win" (winner "Blue")'
        s2 = 'L 10/01/2012 - 22:07:26: World triggered "Round_Overtime"'
        s3 = 'L 10/01/2012 - 22:07:27: World triggered "Round_Length" (seconds "288.70")'
        s4 = 'L 10/01/2012 - 22:07:32: World triggered "Round_Start"'
        s5 = 'L 10/01/2012 - 22:07:32: World triggered "Round_Setup_Begin"'
        s6 = 'L 10/01/2012 - 22:07:32: World triggered "Round_Setup_End"'

        strings = [ s1, s2, s3, s4, s5, s6 ]

        self.check_group_match(strings, "round")

    def test_connection_regex(self):
        s1 = 'L 10/01/2012 - 22:07:32: "1<0><[U:1:1]><>" connected, address "1.1.1.1:12345"'
        s2 = 'L 10/01/2012 - 22:07:32: "1<0><[U:1:1]><>" disconnected (reason "noob")'
        s3 = 'L 10/01/2012 - 22:07:32: "1<0><[U:1:1]><>" STEAM USERID validated'

        strings = [ s1, s2, s3 ]

        self.check_group_match(strings, "player_connection")

    def test_teamscore_regex(self):
        s1 = 'L 10/01/2012 - 22:07:27: Team "Red" current score "2" with "6" players'
        s2 = 'L 10/01/2012 - 22:07:27: Team "Blue" current score "3" with "6" players'
        s3 = 'L 10/01/2012 - 22:20:51: Team "Red" final score "3" with "6" players'
        s4 = 'L 10/01/2012 - 22:20:51: Team "Blue" final score "4" with "6" players'

        strings = [ s1, s2, s3, s4 ]

        self.check_group_match(strings, "team_score")

    def test_game_regex(self):
        s1 = 'L 10/01/2012 - 22:20:51: World triggered "Game_Over" reason "Reached Win Limit"'

        strings = [ s1 ]
        self.check_group_match(strings, "game_event")

    def test_stat_regex(self):
        s1 = 'L 10/01/2012 - 22:20:45: "1<0><[U:1:1]><Blue>" killed "2<2><[U:1:2]><Red>" with "scattergun" (attacker_position "-1803 129 236") (victim_position "-1767 278 218")'
        s2 = 'L 10/01/2012 - 22:20:45: "3<0><[U:1:3]><Blue>" triggered "kill assist" against "2<2><[U:1:2]><Red>" (assister_position "-1446 -200 236") (attacker_position "-1803 129 236") (victim_position "-1767 278 218")'
        s3 = 'L 10/01/2012 - 21:58:01: "1<0><[U:1:1]><Blue>" killed "2<2><[U:1:2]><Red>" with "knife" (customkill "backstab") (attacker_position "-1085 99 240") (victim_position "-1113 51 240")'

        strings = [ s1, s2, s3 ]

        self.check_group_match(strings, "player_stat")

    def test_unity_report_regex(self):
        s1 = 'L 10/01/2012 - 21:38:54: "{"token":"REPORT","data":{"reported":"STEAM_0:1:1","reporter":"STEAM_0:1:2","reason":"CHEATING","matchId":2}}"'

        strings = [ s1 ]

        self.check_group_match(strings, "report")

class ConnectTestCase(LoggingTestCase):
    def test_valid_connect(self):
        msg = 'RL 10/01/2012 - 22:07:32: "1<0><[U:1:1]><>" connected, address "1.1.1.1:12345"'
        print "Sending message " + msg

        self.socket.send(msg)

    def test_invalid_connect(self):
        msg = 'RL 10/01/2012 - 22:07:32: "4<0><[U:1:4]><>" connected, address "1.1.1.1:12345"'
        print "Sending message " + msg
        self.socket.send(msg)

# CID of [U:1:1]: 76561197960265729
# CID of [U:1:2]: 76561197960265730
cid1 = 76561197960265729
cid2 = 76561197960265730
cid3 = 76561197960265731

class StatTestCase(LoggingTestCase):
    ### Test sending messages, make sure they're processed properly
    def setUp(self):
        super(StatTestCase, self).setUp()

        self.pug.begin_game()

    def test_player_kill_msg(self):
        msg = 'RL 10/01/2012 - 22:20:45: "1<0><[U:1:1]><Blue>" killed "2<2><[U:1:2]><Red>" with "scattergun" (attacker_position "-1803 129 236") (victim_position "-1767 278 218")'
        self.socket.send(msg)

    def test_player_assist_msg(self):
        msg = 'RL 10/01/2012 - 22:20:45: "3<0><[U:1:3]><Blue>" triggered "kill assist" against "2<2><[U:1:2]><Red>" (assister_position "-1446 -200 236") (attacker_position "-1803 129 236") (victim_position "-1767 278 218")'
        self.socket.send(msg)

    def test_player_custom_kill_msg(self):
        msg = 'RL 10/01/2012 - 21:58:01: "1<0><[U:1:1]><Blue>" killed "2<2><[U:1:2]><Red>" with "knife" (customkill "backstab") (attacker_position "-1085 99 240") (victim_position "-1113 51 240")'
        self.socket.send(msg)

    # Now we can actually test the parsing
    def test_player_kill(self):
        kill = 'L 10/01/2012 - 22:20:45: "1<0><[U:1:1]><Blue>" killed "2<2><[U:1:2]><Red>" with "scattergun" (attacker_position "-1803 129 236") (victim_position "-1767 278 218")'
        reverse_kill = 'L 10/01/2012 - 22:20:45: "2<2><[U:1:2]><Red>" killed "1<0><[U:1:1]><Blue>" with "scattergun" (attacker_position "-1803 129 236") (victim_position "-1767 278 218")'

        self.server._log_interface._dispatch_parse(kill)
        self.assertEquals(self.pug.game_stats[cid1]["kills"], 1)
        self.assertEquals(self.pug.game_stats[cid2]["deaths"], 1)

        self.server._log_interface._dispatch_parse(kill)
        self.assertEquals(self.pug.game_stats[cid1]["kills"], 2)
        self.assertEquals(self.pug.game_stats[cid2]["deaths"], 2)

        self.server._log_interface._dispatch_parse(reverse_kill)
        self.assertEquals(self.pug.game_stats[cid1]["deaths"], 1)
        self.assertEquals(self.pug.game_stats[cid2]["kills"], 1)

    def test_player_assist(self):
        kill_assist = 'L 10/01/2012 - 22:20:45: "3<0><[U:1:3]><Blue>" triggered "kill assist" against "2<2><[U:1:2]><Red>" (assister_position "-1446 -200 236") (attacker_position "-1803 129 236") (victim_position "-1767 278 218")'

        self.server._log_interface._dispatch_parse(kill_assist)
        self.assertEquals(self.pug.game_stats[cid3]["assists"], 1)

    def test_player_custom_kill(self):
        kill_special = 'L 10/01/2012 - 21:58:01: "1<0><[U:1:1]><Blue>" killed "2<2><[U:1:2]><Red>" with "knife" (customkill "backstab") (attacker_position "-1085 99 240") (victim_position "-1113 51 240")'

        self.server._log_interface._dispatch_parse(kill_special)
        self.assertEquals(self.pug.game_stats[cid1]["kills"], 1)
        self.assertEquals(self.pug.game_stats[cid2]["deaths"], 1)

        self.server._log_interface._dispatch_parse(kill_special)
        self.assertEquals(self.pug.game_stats[cid1]["kills"], 2)
        self.assertEquals(self.pug.game_stats[cid2]["deaths"], 2)

class ChatTestCase(LoggingTestCase):
    def test_team_command(self):
        msg = 'S123L 10/01/2012 - 21:58:09: "1<0><[U:1:1]><Red>" say "!teams"'
        print "Sending message " + msg
        self.socket.send(msg)

    def test_start_command(self):
        msg = 'S123L 10/01/2012 - 21:58:09: "1<0><[U:1:1]><Red>" say "!start"'
        print "Sending message " + msg
        self.socket.send(msg)

    @unittest.skip("NYI")
    def test_replace_command(self):
        pass

class ReportTestCase(LoggingTestCase):
    def test_report(self):
        msg = 'L 10/01/2012 - 21:38:54: "{"token":"REPORT","data":{"reported":"STEAM_0:1:1","reporter":"STEAM_0:1:2","reason":"CHEATING","matchId":2}}"'
        print "Sending message " + msg
        self.socket.send(msg)

def test_suites():
    classes = [ RegexTestCase, VerifyTestCase, ConnectTestCase, StatTestCase, 
                ChatTestCase, ReportTestCase ]

    return [ unittest.TestLoader().loadTestsFromTestCase(x) for x in classes ]

if __name__ == "__main__":
    unittest.TestSuite(test_suites())

    # get a tornado ioloop instance running in another thread so we can
    # actually test this shiz
    t = threading.Thread(target = unittest.main)
    t.start()
    
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        quit()

