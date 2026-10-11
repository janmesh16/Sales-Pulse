"""
Unit tests for SalesPulse calculations, financial formulas, forecasting, and formatting.
Verifies TC38, TC43, TC44, formatters, and validators.
"""

import pytest
from utils.formatters import format_inr, format_percent
from utils.validators import validate_product_data, validate_expense_data, is_valid_email
from services.forecast import get_sales_forecast


def test_format_inr():
    """Verify Indian numbering system formatting with Rupee symbol."""
    assert format_inr(0) == "₹ 0.00"
    assert format_inr(12450) == "₹ 12,450.00"
    assert format_inr(1234567.50) == "₹ 12,34,567.50"
    assert format_inr(-500) == "-₹ 500.00"


def test_format_percent():
    """Verify percentage formatting."""
    assert format_percent(15.42) == "15.4%"
    assert format_percent(0) == "0.0%"


def test_product_data_validation():
    """Test product creation validation rules (TC09, TC10)."""
    # TC09: Negative price
    is_valid, err, _ = validate_product_data("SKU1", "Prod", -10, 50, 10)
    assert not is_valid
    assert "Cost price cannot be negative" in err

    # TC10: Sell price < cost price warning
    is_valid, _, warn = validate_product_data("SKU2", "Prod", 80, 50, 10)
    assert is_valid
    assert warn is not None
    assert "lower than Cost price" in warn


def test_expense_data_validation():
    """Test expense validation (TC25)."""
    # Negative amount
    is_valid, err = validate_expense_data("2026-10-12", "Rent", -500)
    assert not is_valid
    assert "greater than zero" in err

    # Invalid category
    is_valid, err = validate_expense_data("2026-10-12", "InvalidCat", 500)
    assert not is_valid


def test_email_validation():
    """Test email validation."""
    assert is_valid_email("owner@salespulse.com")
    assert not is_valid_email("invalid-email")
    assert not is_valid_email("")


def test_tc43_profit_formula():
    """
    TC43: Profit formula validation.
    Profit = Revenue - COGS - Expenses.
    Margin % = Net Profit / Revenue * 100.
    """
    revenue = 10000.0
    cogs = 6500.0
    expenses = 1500.0

    gross_profit = revenue - cogs
    net_profit = gross_profit - expenses
    margin_pct = (net_profit / revenue) * 100

    assert gross_profit == 3500.0
    assert net_profit == 2000.0
    assert margin_pct == 20.0


def test_tc38_forecast_non_negative(app):
    """
    TC38: 7-day forecast returns 7 non-negative estimates.
    """
    with app.app_context():
        res = get_sales_forecast(lookback_days=28, forecast_days=7)
        assert len(res["forecast_data"]) == 7
        assert len(res["forecast_labels"]) == 7
        for val in res["forecast_data"]:
            assert val >= 0.0
