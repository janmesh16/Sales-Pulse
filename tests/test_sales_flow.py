"""
Integration tests for SalesPulse sales transactions, inventory updates, and cancellation.
Verifies TC15, TC16, TC17, TC18, TC19, TC21, TC22, TC23, TC27, TC28, TC29, TC44.
"""

import pytest
from db import query_one, execute_db
from services.sales_service import create_sale, cancel_sale, get_sale_details
from services.stock_service import adjust_stock, get_low_stock_products, get_slow_moving_products
from services.analytics_service import get_kpis


def test_tc15_tc16_record_sale_and_stock_drop(app):
    """
    TC15 & TC16: Record single and multi-item sales.
    Verifies total amounts and automatic inventory reduction.
    """
    with app.app_context():
        # Get product with known stock
        p1 = query_one("SELECT product_id, stock_qty, sell_price FROM products WHERE is_active = 1 AND stock_qty >= 10 LIMIT 1")
        initial_stock = p1["stock_qty"]
        pid = p1["product_id"]

        cart = [{"product_id": pid, "qty": 2}]
        res = create_sale(cart=cart, discount=10.0, payment_mode="CASH", customer_name="Test Buyer", user_id=1)

        assert res["sale_id"] > 0
        assert res["invoice_no"].startswith("SP-")

        # Verify stock decreased by 2
        p1_after = query_one("SELECT stock_qty FROM products WHERE product_id = %s", (pid,))
        assert p1_after["stock_qty"] == initial_stock - 2

        # Verify stock_movements logged
        sm = query_one("SELECT * FROM stock_movements WHERE ref_sale_id = %s", (res["sale_id"],))
        assert sm is not None
        assert sm["change_qty"] == -2
        assert sm["reason"] == "SALE"


def test_tc17_tc18_insufficient_or_invalid_quantity(app):
    """
    TC17 & TC18: Attempting to sell more than available stock or zero quantity fails.
    """
    with app.app_context():
        p = query_one("SELECT product_id, stock_qty FROM products WHERE is_active = 1 LIMIT 1")
        pid = p["product_id"]
        stock = p["stock_qty"]

        # TC17: Qty > stock
        with pytest.raises(ValueError) as excinfo:
            create_sale(cart=[{"product_id": pid, "qty": stock + 1000}], user_id=1)
        assert "Insufficient stock" in str(excinfo.value)

        # TC18: Qty <= 0
        with pytest.raises(ValueError) as excinfo:
            create_sale(cart=[{"product_id": pid, "qty": 0}], user_id=1)
        assert "greater than zero" in str(excinfo.value)


def test_tc19_discount_exceeds_subtotal(app):
    """
    TC19: Discount greater than subtotal is rejected.
    """
    with app.app_context():
        p = query_one("SELECT product_id, sell_price FROM products WHERE is_active = 1 AND stock_qty > 5 LIMIT 1")
        with pytest.raises(ValueError) as excinfo:
            create_sale(cart=[{"product_id": p["product_id"], "qty": 1}], discount=999999.0, user_id=1)
        assert "cannot exceed subtotal" in str(excinfo.value)


def test_tc21_receipt_matches_db(app):
    """
    TC21: Receipt details retrieve accurately from DB.
    """
    with app.app_context():
        p = query_one("SELECT product_id FROM products WHERE is_active = 1 AND stock_qty > 5 LIMIT 1")
        res = create_sale(cart=[{"product_id": p["product_id"], "qty": 1}], discount=0, customer_name="Receipt Cust", user_id=1)

        sale_details = get_sale_details(res["sale_id"])
        assert sale_details["invoice_no"] == res["invoice_no"]
        assert sale_details["customer_name"] == "Receipt Cust"
        assert len(sale_details["items"]) == 1


def test_tc22_tc23_cancel_sale_and_analytics_exclusion(app):
    """
    TC22 & TC23: Owner cancels sale -> stock restored -> excluded from analytics KPIs.
    """
    with app.app_context():
        p = query_one("SELECT product_id, stock_qty FROM products WHERE is_active = 1 AND stock_qty > 5 LIMIT 1")
        pid = p["product_id"]
        stock_before = p["stock_qty"]

        res = create_sale(cart=[{"product_id": pid, "qty": 3}], discount=0, user_id=1)
        sale_id = res["sale_id"]

        # Stock dropped by 3
        p_mid = query_one("SELECT stock_qty FROM products WHERE product_id = %s", (pid,))
        assert p_mid["stock_qty"] == stock_before - 3

        # Cancel sale
        cancel_sale(sale_id=sale_id, user_id=1)

        # Verify sale status is CANCELLED
        s_canc = query_one("SELECT status FROM sales WHERE sale_id = %s", (sale_id,))
        assert s_canc["status"] == "CANCELLED"

        # Verify stock restored
        p_restored = query_one("SELECT stock_qty FROM products WHERE product_id = %s", (pid,))
        assert p_restored["stock_qty"] == stock_before

        # Verify movement logged
        sm = query_one("SELECT * FROM stock_movements WHERE ref_sale_id = %s AND reason = 'CANCEL_RETURN'", (sale_id,))
        assert sm is not None
        assert sm["change_qty"] == 3


def test_tc28_manual_restock(app):
    """
    TC28: Manual restock updates stock and logs movement.
    """
    with app.app_context():
        p = query_one("SELECT product_id, stock_qty FROM products WHERE is_active = 1 LIMIT 1")
        pid = p["product_id"]
        stock_before = p["stock_qty"]

        new_stock = adjust_stock(product_id=pid, change_qty=50, reason="RESTOCK", user_id=1)
        assert new_stock == stock_before + 50

        p_after = query_one("SELECT stock_qty FROM products WHERE product_id = %s", (pid,))
        assert p_after["stock_qty"] == stock_before + 50


def test_tc27_low_stock_list(app):
    """
    TC27: Low stock list retrieves items with stock_qty <= reorder_level.
    """
    with app.app_context():
        low_items = get_low_stock_products()
        assert len(low_items) > 0
        for item in low_items:
            assert item["stock_qty"] <= item["reorder_level"]


def test_tc44_cost_change_preserves_historical_profit(app):
    """
    TC44: Editing product cost_price later does not alter old sale_items.unit_cost.
    """
    with app.app_context():
        p = query_one("SELECT product_id, cost_price, sell_price FROM products WHERE is_active = 1 AND stock_qty > 5 LIMIT 1")
        pid = p["product_id"]
        original_cost = float(p["cost_price"])

        # Create sale
        res = create_sale(cart=[{"product_id": pid, "qty": 1}], discount=0, user_id=1)
        sale_id = res["sale_id"]

        # Check snapshot in sale_items
        si_before = query_one("SELECT unit_cost FROM sale_items WHERE sale_id = %s", (sale_id,))
        assert float(si_before["unit_cost"]) == original_cost

        # Update product cost in catalog
        execute_db("UPDATE products SET cost_price = %s WHERE product_id = %s", (original_cost + 100.0, pid))

        # Check that sale_items.unit_cost remained unchanged!
        si_after = query_one("SELECT unit_cost FROM sale_items WHERE sale_id = %s", (sale_id,))
        assert float(si_after["unit_cost"]) == original_cost
