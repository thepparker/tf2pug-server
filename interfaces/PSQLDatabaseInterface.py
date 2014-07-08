from BaseDatabaseInterface import BaseDatabaseInterface

import logging

import psycopg2.extras
from psycopg2.extras import Json

"""
Implements the DatabaseInterface for PostgreSQL databases. This is currently
the only provided interface. See the base class for documentation.
"""
class PSQLDatabaseInterface(BaseDatabaseInterface):
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

    def get_tf_player_stats(self, ids):
        conn, cursor = self._get_db_objects()

        # ids is a list of 64 bit steamids (i.e pug.players_list)
        try:
            cursor.execute("""SELECT steamid, games_since_med, games_played, rating
                              FROM players
                              WHERE steamid IN %s""", (tuple(ids),))

            results = cursor.fetchall()
            stats = {}

            if results:
                for result in results:
                    logging.debug("player stat row: %s", result)
                    # result is tuple in the form 
                    # (steamid, games_since_med, games_played, rating)
                    stats[result[0]] = { 
                            "games_since_med": result[1],
                            "games_played": result[2],
                            "rating": float(result[3]) # Decimal -> Float
                        }

            return stats

        except:
            logging.exception("An exception occurred getting stats for %s" % ids)

        finally:
            self._close_db_objects(cursor, conn)

    def flush_tf_pug_med_stats(self, medics, nonmedics):
        conn, cursor = self._get_db_objects()

        try:
            # mogrifying inserts. we need to check who is NOT in the database.
            # to do this, we use the given list of IDs, get the results, and
            # for any IDs NOT in the result, we perform an insert.
            # we do this so that we minimize the number of queries required, so
            # that worst case is O(n+2) instead of ALWAYS being O(n+2) when 
            # inserts are required. If everyone is being updated, efficiency is
            # O(n+2). It also removes the need for using the dirty upsert 
            # function.

            # non medics first
            cursor.execute("SELECT steamid FROM players WHERE steamid IN %s", (tuple(nonmedics),))
            results = cursor.fetchall()
            if results:
                results = [ x[0] for x in results ] # make results a simple list of IDs
            else:
                results = []

            # now get all ids in nonmedics that are NOT in results
            insert_ids = [ x for x in nonmedics if x not in results ]
            if len(insert_ids) > 0: # obviously only perform if we have ids to insert...
                # create the list of tuples for insertion
                data = tuple([ (x, 1, 1) for x in insert_ids ])

                cursor.executemany("""INSERT INTO players (steamid, games_since_med, games_played)
                                      VALUES ('%s', '%s', '%s')""", data)

            #the rest, we just update
            update_ids = [ x for x in nonmedics if x not in insert_ids ]
            for cid in update_ids:
                cursor.execute("""UPDATE players
                                  SET games_since_med = COALESCE(games_since_med, 0) + 1,
                                      games_played = COALESCE(games_played, 0) + 1
                                  WHERE steamid = '%s'""", (cid,))
            conn.commit()

            # now medics, do the same as we did for non-medics
            cursor.execute("SELECT steamid FROM players WHERE steamid IN %s", (tuple(medics),))
            results = cursor.fetchall()
            if results:
                results = [ x[0] for x in results ]
            else:
                results = []

            insert_ids = [ x for x in medics if x not in results ]
            if len(insert_ids) > 0:
                data = tuple([ (x, 0, 1) for x in insert_ids ])

                cursor.executemany("""INSERT INTO players (steamid, games_since_med, games_played)
                                  VALUES ('%s', '%s', '%s')""", data)

            update_ids = [ x for x in medics if x not in insert_ids ]
            for cid in update_ids:
                cursor.execute("""UPDATE players
                                  SET games_since_med = 0,
                                      games_played = COALESCE(games_played, 0) + 1
                                  WHERE steamid = '%s'""", (cid,))

            conn.commit()

        except:
            logging.exception("An exception occurred flushing med stats")

        finally:
            self._close_db_objects(cursor, conn)

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
                cursor.execute("""SELECT data
                                  FROM pugs
                                  WHERE id IN %s""", [tuple(pug_ids)])

                results = cursor.fetchall()
                if results:
                    pugs = [ jsoninterface.loads(x[0]) for x in results ]
                
                # results is a list of Pug objects, converted using the jsoninterface

            return pugs

        except:
            logging.exception("An exception occurred getting pug data")

        finally:
            self._close_db_objects(cursor, conn)

    def flush_pug(self, api_key, jsoninterface, pid, pug):
        # this method is for existing pugs (pug that have already been flushed
        # at least once), such that the id already exists
        conn, cursor = self._get_db_objects()

        try:
            cursor.execute("UPDATE pugs SET data = %s WHERE id = %s", 
                            [Json(pug, dumps=jsoninterface.dumps), pid])

            conn.commit()

        except:
            logging.exception("An exception occurred flushing pug %d" % pid)

        finally:
            self._close_db_objects(cursor, conn)

    def flush_new_pug(self, api_key, jsoninterface, pug):
        conn, cursor = self._get_db_objects()

        try:
            pid = None
            cursor.execute("INSERT INTO pugs (data) VALUES (%s) RETURNING id", 
                            [Json(pug, dumps=jsoninterface.dumps)])

            result = cursor.fetchone()
            pid = None
            if result:
                pid = result[0]
            else:
                raise Exception("No ID returned when inserting new pug")

            cursor.execute("""INSERT INTO pugs_index (pug_entity_id, finished, api_key) 
                              VALUES (%s, %s, %s)""", [pid, pug.game_over, api_key])
            
            conn.commit()

            return pid

        except:
            logging.exception("An exception occurred flushing new pug")

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
