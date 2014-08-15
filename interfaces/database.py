import logging
import json

import psycopg2.extras
from psycopg2.extras import Json

from BaseInterfaces import BaseDatabaseInterface

class PSQLDatabaseInterface(BaseDatabaseInterface):
    """
    Implements the DatabaseInterface for PostgreSQL databases. This is currently
    the only provided interface. See the base class for documentation.
    """
    def __init__(self, db):
        BaseDatabaseInterface.__init__(self, db)

        self._indexable_stats = []

    def add_stat_index(self, stat):
        self._indexable_stats.append(stat)

    def get_user_info(self, api_key = None):
        conn, cursor = self._get_db_objects()

        try:
            result = None

            if api_key:
                cursor.execute("""SELECT name, pug_group, server_group 
                                  FROM api_keys WHERE key = %s""", (api_key,))

            else:
                cursor.execute("SELECT name, pug_group, server_group, key FROM api_keys")
            
            result = cursor.fetchall()

            return result

        except:
            logging.exception("An exception occurred getting user info")

        finally:
            self._close_db_objects(cursor, conn)

    def get_player_stats(self, ids):
        conn, cursor = self._get_db_objects()

        # ids is a list of 64 bit steamids (i.e pug.players_list)
        try:
            cursor.execute("""SELECT steamid, data
                              FROM players
                              WHERE steamid IN %s""", (tuple(ids),))

            results = cursor.fetchall()
            stats = {}

            if results:
                for result in results:
                    logging.debug("player stat row: %s", result)
                    # result is tuple in the form (steamid, JSON string)
                    # the pug manager expects a dict with steamid as the root
                    # keys, and values of stat dicts. so we decode the json.
                    stats[result[0]] = json.loads(result[1])

            return stats

        except:
            logging.exception("An exception occurred getting stats for %s" % ids)
            raise

        finally:
            self._close_db_objects(cursor, conn)

    def flush_player_stats(self, player_stats):
        conn, cursor = self._get_db_objects()

        try:
            # player stats is a dict of PlayerStats objects, with keys being
            # 64bit steamids. We store the players as a JSON string, just like
            # we do for pugs. This allows us to easily add and remove stat
            # keys without the need for modifying the table. We maintain
            # an index table, players_index, which allows us to lookup players
            # based on stat data.

            # see which stats we should insert or update
            cids = player_stats.keys()
            cursor.execute("""SELECT steamid 
                              FROM players 
                              WHERE steamid IN %s""", tuple(cids))

            resuls = cursor.fetchall()
            # populate existing with the steamids that are already in the
            # table. these ids we will simply update
            existing = [ x[0] for x in results ] if results else []

            insert_ids = [ x for x in cids if x not in existing ]

            # Make data a list of tuples in the format (cid, JSON)
            insert = [ (x, Json(player_stats[x])) for x in insert_ids ]

            # opposite order for update because of query ordering
            update = [ (Json(player_stats[x]), x) for x in existing ]

            cursor.executemany("""INSERT INTO players (steamid, data) 
                                  VALUES (%s, %s)""", insert)

            cursor.executemany("""UPDATE players
                                  SET data = %s
                                  WHERE steamid = %s""", update)

            conn.commit()

        except:
            logging.exception("An exception occurred flushing player stats")

        finally:
            self._close_db_objects(cursor, conn)

        self._maintain_stat_index(player_stats)

    def _maintain_stat_index(self, player_stats):
        """
        Maintains the stat table index for each column listed in 
        self._indexable_stats
        """
        conn, cursor = self._get_db_objects()

        try:
            for col in self._indexable_stats:
                # col is the name of a key in the player stat dictionary
                for cid in player_stats:
                    pstat = player_stats[cid]
                    
                    if col not in pstat: # player does not contain this stat. skip?
                        continue

                    # see if this item already exists in the index
                    cursor.execute("""SELECT 1 
                                      FROM players_index
                                      WHERE steamid = %s AND item = %s""")
                    result = cursor.fetchone()
                    if result:
                        # exists, so we should update the value
                        cursor.execute("""UPDATE players_index
                                          SET value = %s
                                          WHERE steamid = %s AND item = %s""",
                                        [ pstat[col], cid, col ])
                    else:
                        # insert into index
                        cursor.execute("""INSERT INTO players_index 
                                            (steamid, item, value)
                                          VALUES (%s, %s, %s)""",
                                        [ cid, col, pstat[col] ])

                # commit after each indexable column
                conn.commit()

        except:
            logging.exception("An exception occurred updating the stat index")

        finally:
            self._close_db_objects()

    def get_pugs(self, api_key, jsoninterface, include_finished = False):
        conn, cursor = self._get_db_objects()

        # if using pg version 9.2+, you can simply use
        # psycopg2.extras.register_default_json(cursor, loads=jsoninterface.loads)
        # which will register the given loads method with the cursor, and any
        # json data field will be passed to the loads method. Since pg 9.1 only
        # supports json through an extension, this code is based on using a
        # text field to store json data, and then converting the results 
        # manually
        try:
            # first we get the pug ids we're after from the index table
            cursor.execute("""SELECT pug_entity_id
                              FROM pugs_index
                              WHERE api_key = %s AND finished = %s""",
                              (api_key, include_finished))
            
            results = cursor.fetchall()
            pug_ids = [ x[0] for x in results ] # list of entity ids
            pugs = []
            if len(pug_ids) > 0:
                cursor.execute("""SELECT id, data
                                  FROM pugs
                                  WHERE id IN %s""", [tuple(pug_ids)])

                results = cursor.fetchall()
                if results:
                    pugs = [ jsoninterface.loads(x[0], x[1]) for x in results ]
                
                # results is a list of Pug objects, converted using the jsoninterface

            return pugs

        except:
            logging.exception("An exception occurred getting pug data")
            return []

        finally:
            self._close_db_objects(cursor, conn)

    def flush_pug(self, api_key, jsoninterface, pug):
        conn, cursor = self._get_db_objects()

        try:
            if pug.id is None:
                # this is a new pug, so we need to INSERT into the pug table
                # AND update the index table. Then we set the pug's ID to the
                # new ID
                cursor.execute("INSERT INTO pugs (data) VALUES (%s) RETURNING id", 
                                [Json(pug, dumps=jsoninterface.dumps)])

                result = cursor.fetchone()
                if result and result[0]:
                    pug.id = result[0]
                else:
                    raise ValueError("No ID was returned on new pug insert")

                cursor.execute("""INSERT INTO pugs_index (pug_entity_id, finished, api_key) 
                                  VALUES (%s, %s, %s)""", [pug.id, pug.game_over, api_key])

            else:
                # Else, this pug has already been flushed once. So we just
                # update the data column, and the index if necessary
                cursor.execute("UPDATE pugs SET data = %s WHERE id = %s", 
                                [Json(pug, dumps=jsoninterface.dumps), pug.id])

                if pug.game_over:
                    cursor.execute("""UPDATE pugs_index 
                                      SET finished = true
                                      WHERE pug_entity_id = %s""", [pug.id])

            conn.commit()

        except:
            logging.exception("An exception occurred flushing pug %d" % pug.id)

        finally:
            self._close_db_objects(cursor, conn)

    def get_servers(self, group):
        conn, cursor = self._get_db_objects()

        try:
            # first close the normal cursor, because we want to use a dict
            # for this method, which will automatically get each row as a
            # dictionary for us. this also happens to be what we want to
            # return!
            cursor.close()
            cursor = conn.cursor(cursor_factory = psycopg2.extras.DictCursor)

            cursor.execute("""SELECT id, HOST(ip) as ip, port, rcon_password,
                                password, pug_id, log_port, server_group
                              FROM servers
                              WHERE server_group = %s""", [group])

            return cursor.fetchall()

        except:
            logging.exception("An exception occurred getting servers")
            return []

        finally:
            self._close_db_objects(cursor, conn)

    def flush_server(self, server):
        conn, cursor = self._get_db_objects()

        try:
            cursor.execute("""UPDATE servers SET password = %s, pug_id = %s,
                                log_port = %s
                              WHERE id = %s""",
                              [server.password, server.pug_id, server.log_port,
                                server.id])

            conn.commit()

        except:
            logging.exception("An exception occurred flushing a server")

        finally:
            self._close_db_objects(cursor, conn)

    """
    Gets a (connection, cursor) tuple from the database connection pool
    """
    def _get_db_objects(self):
        conn = None
        curs = None

        try:
            conn = self.db.getconn()

            curs = conn.cursor()

            return (conn, curs)
        
        except:
            logging.exception("Exception getting db objects")

            if curs and not curs.closed:
                curs.close()

            if conn:
                self.db.putconn(conn)

    """
    Closes the given cursor, and puts the connection back into the pool
    """
    def _close_db_objects(self, cursor, conn):
        if self.db.closed:
            return

        if cursor and not cursor.closed:
            cursor.close()

        if conn:
            conn.rollback() # rollback to the latest safe point just in case
            self.db.putconn(conn) # put the connection back into the database pool
