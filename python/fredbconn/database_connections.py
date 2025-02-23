"""Uses pymysql to handle connections to the db, giving a decorator to connect to a database functions

Initialization:
    Call initialize_database before using the decorator
"""

import pymysql
from dbutils.pooled_db import PooledDB
from functools import wraps

pool = None

def initialize_database(max_total_connections, min_cached_connections,
                        max_cached_connections, database_host, database_user, database_password, database_name):
    """Function to be called to initialize the database pool of connections
    """
    global pool
    pool = PooledDB (
        creator = pymysql,
        maxconnections = max_total_connections,
        mincached = min_cached_connections,
        maxcached = max_cached_connections,
        blocking = True,
        host = database_host,
        user = database_user,
        password = database_password,
        database = database_name,
    )


def connected_to_database(fn):
    """Decorator to connect to database

    Usage:
        Passes as first parameter a cursor to work with the database and execute commands and fetch results.
        All actions performed inside the db are inside a big transaction, which is committed by the decorator when the function ends.
    """
    @wraps(fn)
    def ret_func(*args, **kwargs):
        conn = pool.connection()
        try:
            with conn.cursor() as cursor:
                ret = fn(cursor, *args, **kwargs)
                conn.commit()
        except Exception as e:
            ret = f"Error: {e}"
        finally:
            conn.close()
            return ret
    return ret_func
