import sys
sys.path.append('..')

import random

import psycopg2.pool

import settings
from interfaces import PSQLDatabaseInterface
from entities.Pug import PlayerStats

def fill():
    dsn = "dbname=%s user=%s password=%s host=%s port=%s" % (
                settings.db_name, settings.db_user, settings.db_pass, 
                settings.db_host, settings.db_port
            )

    pool = psycopg2.pool.SimpleConnectionPool(minconn = 1, maxconn = 1,
        dsn = dsn)

    db = PSQLDatabaseInterface(pool, None)
    indexes = ("kills", "deaths", "wins", "rating")
    for i in indexes:
        db.add_stat_index(i)

    # build stat dict to insert
    stats = {}

    cm_modifier = 76561197960265728
    for i in xrange(10000):
        cid = cm_modifier + i
        pstat = PlayerStats()

        for k in pstat:
            val = 0
            if k == "rating":
                val = random.randint(1500, 2500)

            else:
                val = random.randint(0, 40)

            pstat[k] = val

        stats[cid] = pstat

        print "Built stat dict for %s" % cid

    # stats is now full. flush into database
    db.flush_player_stats(stats)

fill()
