import BaseDatabaseInterface.BaseDatabaseInterface
import logging

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
                cursor.execute("SELECT name, group FROM api_keys WHERE key = %s", (api_key,))

            else:
                cursor.execute("SELECT name, group, key FROM api_keys")
            
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
            cursor.execute("""SELECT steamid, games_since_med, games_played, rating
                              FROM players
                              WHERE steamid IN %s""", (tuple(ids),))

            results = cursor.fetchall()
            stats = {}

            if results:
                for result in results:
                    logging.debug("player stat row: %s" % result)

                    stats[result["steamid"]] = { 
                            "games_since_med": result["games_since_med"],
                            "games_played": result["games_played"],
                            "rating": result["rating"]
                        }

            return stats

        except:
            logging.exception("An exception occurred getting stats for %s" % ids)

        finally:
            self._close_db_objects(cursor, conn)

    def flush_pug_med_stats(self, medics, nonmedics):
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
            cursor.execute("SELECT steamid FROM players WHERE steamd IN %s", (tuple(nonmedics),))
            results = cursor.fetchall()
            results = [ x[0] for x in results ] # make results a simple list of IDs

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
            results = [ x[0] for x in results ]

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
            self._close_db_objects()

    def get_pugs(self, api_key, include_finished = False):
        conn, cursor = self._get_db_objects()

        try:
            # first we get the pug ids we're after from the index table
            cursor.execute("""SELECT pug_entity_id
                              FROM pugs_index
                              WHERE api_key = %s AND finished = %s""",
                              (api_key, finished))
            pug_ids = [ x[0] for x in cursor.fetchall() ] # results is a list of entity ids

            cursor.execute("""SELECT id, data
                              FROM pugs
                              WHERE id IN %s""", (tuple(pug_ids),))

            results = cursor.fetchall() 
            # results is a list of tuples containing (id, pug data as JSON)


        except:
            logging.exception("An exception occurred getting pug data")

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
            curs = conn.cursor(cursor_factory = psycopg2.extras.DictCursor)

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
