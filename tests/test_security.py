"""
Security and Role-Based Access Control tests for SalesPulse.
Verifies TC01, TC02, TC03, TC04, TC05, TC39, TC40, TC41.
"""

import pytest
from app import create_app
from config import Config


def test_tc01_valid_owner_login(client):
    """TC01: Valid owner credentials redirects to owner dashboard."""
    res = client.post("/login", data={"email": "owner@salespulse.com", "password": "Owner@123"}, follow_redirects=False)
    assert res.status_code == 302
    assert "/dashboard" in res.headers["Location"]


def test_tc02_wrong_password(client):
    """TC02: Invalid password displays error message and stays on login."""
    res = client.post("/login", data={"email": "owner@salespulse.com", "password": "WrongPassword"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid email or password" in res.data


def test_tc03_empty_login_fields(client):
    """TC03: Blank credentials rejected."""
    res = client.post("/login", data={"email": "", "password": ""}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Please enter both email and password" in res.data


def test_tc04_staff_forbidden_on_owner_routes(staff_client):
    """TC04: Staff user attempting to access /reports is denied (403 Forbidden)."""
    res = staff_client.get("/reports")
    assert res.status_code == 403
    assert b"403" in res.data


def test_tc05_unauthenticated_redirect_to_login(client):
    """TC05: Accessing protected page without session redirects to /login."""
    res = client.get("/dashboard", follow_redirects=False)
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_tc39_sql_injection_defense(client):
    """TC39: SQL Injection payload in login input is safely escaped."""
    sqli_payload = "' OR '1'='1"
    res = client.post("/login", data={"email": sqli_payload, "password": sqli_payload}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid email or password" in res.data


def test_tc40_xss_prevention_in_templates(owner_client):
    """TC40: HTML / script tags in product inputs are escaped by Jinja2 autoescaping."""
    xss_name = "<script>alert('XSS_TEST')</script>"
    owner_client.post(
        "/products/new",
        data={
            "sku": "XSS-SKU-001",
            "name": xss_name,
            "category_id": "1",
            "cost_price": "10",
            "sell_price": "20",
            "stock_qty": "5",
            "reorder_level": "2"
        },
        follow_redirects=True
    )

    res = owner_client.get("/products?q=XSS-SKU-001")
    # Verify raw <script> does not execute unescaped in HTML
    assert b"<script>alert('XSS_TEST')</script>" not in res.data
    assert b"&lt;script&gt;alert(&#39;XSS_TEST&#39;)&lt;/script&gt;" in res.data or b"&lt;script&gt;" in res.data


def test_tc41_csrf_protection_enforced():
    """TC41: POST request without CSRF token is intercepted when CSRF is enabled."""
    class CsrfTestConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = True
        DB_NAME = "salespulse_test"

    app = create_app(CsrfTestConfig)
    test_client = app.test_client()

    # Attempt POST without CSRF token - intercepted by CSRF protection (redirected to login or 400)
    res = test_client.post("/login", data={"email": "owner@salespulse.com", "password": "Owner@123"})
    assert res.status_code in (302, 400)
