"""
Pytest fixtures and configuration for SalesPulse.
Sets up the Flask test client and authenticated sessions using the isolated test database.
"""

import pytest
from app import create_app
from config import TestConfig
from db import init_db_pool


@pytest.fixture(scope="session")
def app():
    """Create and configure a new Flask app instance for the test session."""
    app = create_app(TestConfig)
    return app


@pytest.fixture
def client(app):
    """A test client for making HTTP requests to the application."""
    return app.test_client()


@pytest.fixture
def owner_client(app, client):
    """A test client authenticated as the Store Owner."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Misbah Khan"
        sess["user_email"] = "owner@salespulse.com"
        sess["role"] = "OWNER"
    return client


@pytest.fixture
def staff_client(app, client):
    """A test client authenticated as a Staff Cashier."""
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["user_name"] = "Rohan Sharma (Cashier)"
        sess["user_email"] = "staff@salespulse.com"
        sess["role"] = "STAFF"
    return client
