"""
Database access module for SalesPulse.
Provides MySQL connection pooling, connection retrieval, and query execution helpers.
All queries MUST use parameterized execution to prevent SQL injection.
"""

import os
from urllib.parse import urlparse
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


def ensure_tables_exist(conn):
    """Ensure essential tables and default users exist in the connected database."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SHOW TABLES LIKE 'users'")
        if not cursor.fetchone():
            print("Database tables not found. Automatically initializing schema...")
            statements = [
                """CREATE TABLE IF NOT EXISTS users (
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(120) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('OWNER','STAFF') NOT NULL DEFAULT 'STAFF',
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS categories (
                    category_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(80) NOT NULL UNIQUE
                )""",
                """CREATE TABLE IF NOT EXISTS products (
                    product_id INT AUTO_INCREMENT PRIMARY KEY,
                    sku VARCHAR(40) NOT NULL UNIQUE,
                    name VARCHAR(150) NOT NULL,
                    category_id INT NOT NULL,
                    cost_price DECIMAL(10,2) NOT NULL CHECK (cost_price >= 0),
                    sell_price DECIMAL(10,2) NOT NULL CHECK (sell_price >= 0),
                    stock_qty INT NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
                    reorder_level INT NOT NULL DEFAULT 5,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(category_id),
                    INDEX idx_prod_cat (category_id),
                    INDEX idx_prod_name (name)
                )""",
                """CREATE TABLE IF NOT EXISTS sales (
                    sale_id INT AUTO_INCREMENT PRIMARY KEY,
                    invoice_no VARCHAR(20) NOT NULL UNIQUE,
                    sale_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    customer_name VARCHAR(100) NULL,
                    customer_phone VARCHAR(15) NULL,
                    subtotal DECIMAL(12,2) NOT NULL,
                    discount DECIMAL(12,2) NOT NULL DEFAULT 0,
                    total_amount DECIMAL(12,2) NOT NULL,
                    payment_mode ENUM('CASH','UPI','CARD') NOT NULL DEFAULT 'CASH',
                    status ENUM('COMPLETED','CANCELLED') NOT NULL DEFAULT 'COMPLETED',
                    user_id INT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    INDEX idx_sale_date (sale_date),
                    INDEX idx_sale_status (status)
                )""",
                """CREATE TABLE IF NOT EXISTS sale_items (
                    item_id INT AUTO_INCREMENT PRIMARY KEY,
                    sale_id INT NOT NULL,
                    product_id INT NOT NULL,
                    quantity INT NOT NULL CHECK (quantity > 0),
                    unit_price DECIMAL(10,2) NOT NULL,
                    unit_cost DECIMAL(10,2) NOT NULL,
                    line_total DECIMAL(12,2) NOT NULL,
                    FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(product_id),
                    INDEX idx_si_sale (sale_id),
                    INDEX idx_si_prod (product_id)
                )""",
                """CREATE TABLE IF NOT EXISTS expenses (
                    expense_id INT AUTO_INCREMENT PRIMARY KEY,
                    expense_date DATE NOT NULL,
                    category ENUM('Rent','Electricity','Salaries','Transport','Maintenance','Marketing','Packaging','Other') NOT NULL,
                    amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
                    payment_mode ENUM('CASH','UPI','CARD','BANK') NOT NULL DEFAULT 'CASH',
                    note VARCHAR(255) NULL,
                    user_id INT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    INDEX idx_exp_date (expense_date)
                )""",
                """CREATE TABLE IF NOT EXISTS stock_movements (
                    movement_id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    change_qty INT NOT NULL,
                    reason ENUM('SALE','RESTOCK','DAMAGE','CORRECTION','CANCEL_RETURN') NOT NULL,
                    ref_sale_id INT NULL,
                    user_id INT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(product_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    INDEX idx_sm_prod (product_id)
                )""",
                """CREATE TABLE IF NOT EXISTS settings (
                    setting_key VARCHAR(50) PRIMARY KEY,
                    setting_value VARCHAR(255) NOT NULL
                )"""
            ]
            for stmt in statements:
                cursor.execute(stmt)

            from werkzeug.security import generate_password_hash
            cursor.execute("INSERT IGNORE INTO settings (setting_key, setting_value) VALUES ('shop_name', 'SalesPulse Store'), ('currency', '₹')")
            cursor.execute(
                """INSERT IGNORE INTO users (name, email, password_hash, role, is_active)
                   VALUES ('Misbah Khan', 'owner@salespulse.com', %s, 'OWNER', 1),
                          ('Staff Cashier', 'staff@salespulse.com', %s, 'STAFF', 1)""",
                (generate_password_hash("Owner@123"), generate_password_hash("Staff@123"))
            )
            conn.commit()
            print("Schema initialized with default demo credentials.")
    except Exception as e:
        print(f"Schema check error: {e}")
    finally:
        cursor.close()


def init_db_pool(app_config=None):
    """Initialize the MySQL connection pool."""
    global _pool
    cfg = app_config or Config

    pool_name = _get_val(cfg, "DB_POOL_NAME", "salespulse_pool")
    db_name = _get_val(cfg, "DB_NAME", "salespulse")
    db_user = _get_val(cfg, "DB_USER", "root")
    db_password = _get_val(cfg, "DB_PASSWORD", "")
    db_host = _get_val(cfg, "DB_HOST", "localhost")
    db_port = _get_val(cfg, "DB_PORT", 3306)
    pool_size = int(_get_val(cfg, "DB_POOL_SIZE", 5))

    # Support full Service URI / DATABASE_URL if provided
    db_url = _get_val(cfg, "DATABASE_URL", None) or os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
    if db_url:
        p = urlparse(db_url)
        db_host = p.hostname or db_host
        if p.port:
            db_port = p.port
        if p.username:
            db_user = p.username
        if p.password:
            db_password = p.password
        if p.path and p.path.strip("/"):
            db_name = p.path.strip("/")

    try:
        db_port = int(db_port)
    except (ValueError, TypeError):
        db_port = 3306

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
            autocommit=False,
            ssl_disabled=False
        )
        # Verify connection and ensure schema tables exist
        init_conn = _pool.get_connection()
        ensure_tables_exist(init_conn)
        init_conn.close()
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
