"""
Database access module for SalesPulse.
Provides MySQL connection pooling, connection retrieval, and query execution helpers.
All queries MUST use parameterized execution to prevent SQL injection.
"""

import mysql.connector
from mysql.connector import pooling
from flask import current_app, g
from config import Config

_pool = None


def _get_val(cfg, key, default=None):
    if hasattr(cfg, "get") and callable(cfg.get):
        val = cfg.get(key)
        if val is not None:
            return val
    return getattr(cfg, key, default)


def init_db_pool(app_config=None):
    """Initialize the MySQL connection pool."""
    global _pool
    cfg = app_config or Config

    pool_name = _get_val(cfg, "DB_POOL_NAME", "salespulse_pool")
    db_name = _get_val(cfg, "DB_NAME", "salespulse")
    db_user = _get_val(cfg, "DB_USER", "root")
    db_password = _get_val(cfg, "DB_PASSWORD", "")
    db_host = _get_val(cfg, "DB_HOST", "localhost")
    db_port = int(_get_val(cfg, "DB_PORT", 3306))
    pool_size = int(_get_val(cfg, "DB_POOL_SIZE", 10))

    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name=pool_name,
            pool_size=pool_size,
            pool_reset_session=True,
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False
        )
    except mysql.connector.Error as err:
        print(f"Error initializing MySQL connection pool: {err}")
        raise err


def get_db():
    """
    Get a database connection from the pool for the current application context.
    The connection is cached in Flask's g object and closed during request teardown.
    """
    global _pool
    if _pool is None:
        init_db_pool(current_app.config if current_app else Config)

    if "db_conn" not in g:
        g.db_conn = _pool.get_connection()
    return g.db_conn


def close_db(e=None):
    """Close the database connection and return it to the pool at the end of the request."""
    db_conn = g.pop("db_conn", None)
    if db_conn is not None and db_conn.is_connected():
        try:
            db_conn.close()
        except Exception:
            pass


def get_raw_connection(app_config=None):
    """
    Get a standalone database connection directly from the pool or directly connect.
    Useful for background jobs, seed scripts, or standalone services.
    """
    global _pool
    cfg = app_config or Config
    try:
        if _pool is None:
            init_db_pool(cfg)
        return _pool.get_connection()
    except Exception:
        # Fallback to direct connection if pool fails or standalone script
        return mysql.connector.connect(
            host=getattr(cfg, "DB_HOST", "localhost"),
            port=getattr(cfg, "DB_PORT", 3306),
            user=getattr(cfg, "DB_USER", "root"),
            password=getattr(cfg, "DB_PASSWORD", ""),
            database=getattr(cfg, "DB_NAME", "salespulse"),
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False
        )


def query_all(query, params=None, dictionary=True):
    """Execute a parameterized SELECT query and return all matching rows."""
    conn = get_db()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        cursor.execute(query, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()


def query_one(query, params=None, dictionary=True):
    """Execute a parameterized SELECT query and return the first matching row or None."""
    conn = get_db()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        cursor.execute(query, params or ())
        return cursor.fetchone()
    finally:
        cursor.close()


def execute_db(query, params=None, commit=True):
    """
    Execute an INSERT, UPDATE, or DELETE query using parameters.
    Returns lastrowid for INSERT or rowcount for UPDATE/DELETE.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        if commit:
            conn.commit()
        return cursor.lastrowid or cursor.rowcount
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        cursor.close()
