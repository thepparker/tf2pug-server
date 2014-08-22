"""
Test case for database methods. Manual verification of output is required
"""

import sys
import logging
import psycopg2.pool
sys.path.append('..')

import settings
from interfaces import PSQLDatabaseInterface, TFPugJsonInterface
from entities import Pug, Server
from pprint import pprint

logging.basicConfig(LEVEL=logging.DEBUG)
dsn = "dbname=%s user=%s password=%s host=%s port=%s" % (
                settings.db_name, settings.db_user, settings.db_pass, 
                settings.db_host, settings.db_port)

conn = psycopg2.pool.SimpleConnectionPool(dsn = dsn, minconn = 1, maxconn = 1)

dbif = PSQLDatabaseInterface(conn)

PLAYER_IDS = [1L,2L,3L,4L,5L,6L,7L,8L,9L,10L,11L,12L]

api_key = "123abc"
server_group = 1

player_stats = {}
for cid in PLAYER_IDS:
    player_stats[cid] = Pug.PlayerStats()

pugs = [ Pug.Pug() ]

# we want to use the various methods supplied in PSQLDatabaseInterface and
# see if they have the correct output
def test_user_info():
    # single user
    print "User info for '%s':" % api_key
    user = dbif.get_user_info(api_key)
    pprint(user)

    # all users
    print "All users:"
    users = dbif.get_user_info()
    pprint(users)

def test_get_player_stats():
    print "GETTING PLAYER STATS FOR %s: " % PLAYER_IDS
    stats = dbif.get_player_stats(PLAYER_IDS)
    for cid in stats:
        stats[cid] = Pug.PlayerStats(stats[cid])

    print "Player stats equal? %s" % (stats == player_stats)
    #pprint(stats)

def test_flush_player_stats():
    print "Flushing stat data:"
    print "stat data cids: %s" % player_stats.keys()
    for cid in player_stats:
        player_stats[cid]["kills"] = 10

    player_stats[1]["rating"] = 2000
    player_stats[2]["kills"] = 12
    player_stats[2]["rating"] = 1700

    dbif.flush_player_stats(player_stats)

def test_stat_index():
    print "Adding stat index 'kills'"
    dbif.add_stat_index("kills")
    dbif.add_stat_index("rating")

    test_flush_player_stats()

def test_get_pugs():
    print "Getting pugs for API key %s" % api_key
    pugs = dbif.get_pugs(api_key, TFPugJsonInterface())
    pprint(pugs)

def test_flush_pug(end = False):
    print "Flushing pugs, end: %s" % end
    for pug in pugs:
        if end:
            pug.end_game()

        dbif.flush_pug(api_key, TFPugJsonInterface(), pug)

def test_get_servers():
    print "Getting servers for group %d" % server_group
    serverdata = dbif.get_servers(server_group)
    pprint(serverdata)

def test_flush_server():
    print "Flushing server"
    server = Server.Server("TF2")
    server.id = 1
    server.password = "TESTPASS"

    dbif.flush_server(server)

def test_all():
    # check user info
    print "Testing user info"
    test_user_info()

    # check player stats initial
    print "First get_player_stats"
    test_get_player_stats()

    print "Flushing player stats and getting them again"
    # flush player stats and get them to see result
    test_flush_player_stats()
    test_get_player_stats()

    print "Stat index flush"
    # test the stat index
    test_stat_index()

    print "Flushing new pug and getting it again"
    # get pugs/flush pugs
    test_flush_pug()
    test_get_pugs()

    print "Flushing ended pug and checking pug listing"
    test_flush_pug(True)
    test_get_pugs()

    print "Getting servers & flushing"
    test_get_servers()
    test_flush_server()

    print "Getting server after flush"
    test_get_servers()

test_all()

conn.closeall()
