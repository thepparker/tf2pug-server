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
                result = cursor.fetchone()
            else:
                cursor.execute("SELECT name, group, key FROM api_keys")
                result = cursor.fetchall()

            return result

        except:
            logging.exception("An exception occurred getting user info")

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
