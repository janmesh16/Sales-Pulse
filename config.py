"""
Configuration module for SalesPulse.
Loads environment variables from .env and exposes application configurations.
"""

import os
from datetime import timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "salespulse-default-secret-key-change-in-prod")

    # Database settings (support both full DATABASE_URL / Service URI and individual variables)
    _db_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
    if _db_url:
        _parsed = urlparse(_db_url)
        DB_HOST = _parsed.hostname or "localhost"
        DB_PORT = int(_parsed.port or 3306)
        DB_USER = _parsed.username or "root"
        DB_PASSWORD = _parsed.password or ""
        DB_NAME = _parsed.path.lstrip("/") if _parsed.path else "salespulse"
    else:
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_PORT = int(os.getenv("DB_PORT", 3306))
        DB_USER = os.getenv("DB_USER", "root")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "")
        DB_NAME = os.getenv("DB_NAME", "salespulse")

    DB_POOL_NAME = "salespulse_pool"
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))

    # Security & Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1")
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB limit for CSV imports

    # CSRF protection enabled
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = int(os.getenv("WTF_CSRF_TIME_LIMIT", 3600))
    WTF_CSRF_CHECK_DEFAULT = True


class TestConfig(Config):
    """Configuration for running automated tests."""
    TESTING = True
    DB_NAME = os.getenv("TEST_DB_NAME", "salespulse_test")
    DB_POOL_NAME = "salespulse_test_pool"
    WTF_CSRF_ENABLED = False  # Allows standard test client posts unless CSRF test
