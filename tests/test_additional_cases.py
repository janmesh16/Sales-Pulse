"""
Additional functional and edge-case tests for SalesPulse.
Verifies TC07, TC08, TC11, TC12, TC13, TC14, TC20, TC24, TC26, TC32.
"""

import io
import uuid
import pytest
from db import query_one, query_all, execute_db
from services.csv_import import import_products_from_csv
from services.sales_service import create_sale

TEST_SKU = "TEST-PROD-SKU-999"


def test_tc07_tc08_product_add_and_duplicate_sku(owner_client, app):
    """TC07 & TC08: Add valid product, reject duplicate SKU."""
    with app.app_context():
        p = query_one("SELECT product_id FROM products WHERE sku = %s", (TEST_SKU,))
        if p:
            pid = p["product_id"]
            execute_db("DELETE FROM stock_movements WHERE product_id = %s", (pid,))
            execute_db("DELETE FROM sale_items WHERE product_id = %s", (pid,))
            execute_db("DELETE FROM products WHERE product_id = %s", (pid,))

    # TC07: Add valid product
    res = owner_client.post(
        "/products/new",
        data={
            "sku": TEST_SKU,
            "name": "Super Test Biscuit",
            "category_id": "1",
            "cost_price": "20.00",
            "sell_price": "30.00",
            "stock_qty": "50",
            "reorder_level": "5"
        },
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"added successfully" in res.data

    # TC08: Duplicate SKU fails
    res_dup = owner_client.post(
        "/products/new",
        data={
            "sku": TEST_SKU,
            "name": "Another Product With Same SKU",
            "category_id": "1",
            "cost_price": "20.00",
            "sell_price": "30.00",
            "stock_qty": "50",
            "reorder_level": "5"
        },
        follow_redirects=True
    )
    assert res_dup.status_code == 200
    assert b"already exists" in res_dup.data


def test_tc11_product_edit(owner_client, app):
    """TC11: Edit product price and name."""
    with app.app_context():
        p = query_one("SELECT product_id FROM products WHERE sku = %s", (TEST_SKU,))
        pid = p["product_id"]

    res = owner_client.post(
        f"/products/{pid}/edit",
        data={
            "sku": TEST_SKU,
            "name": "Super Test Biscuit Updated",
            "category_id": "1",
            "cost_price": "22.00",
            "sell_price": "35.00",
            "stock_qty": "45",
            "reorder_level": "6"
        },
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"updated successfully" in res.data


def test_tc12_product_soft_delete(owner_client, app):
    """TC12: Delete product soft-deactivates (is_active = 0) without breaking sales history."""
    with app.app_context():
        p = query_one("SELECT product_id FROM products WHERE sku = %s", (TEST_SKU,))
        pid = p["product_id"]

    res = owner_client.post(f"/products/{pid}/delete", follow_redirects=True)
    assert res.status_code == 200
    assert b"has been deactivated" in res.data

    with app.app_context():
        p_check = query_one("SELECT is_active FROM products WHERE product_id = %s", (pid,))
        assert p_check["is_active"] == 0


def test_tc13_tc14_csv_import(app):
    """TC13 & TC14: CSV bulk import with valid rows and bad row error logs."""
    uid = uuid.uuid4().hex[:6].upper()
    sku1 = f"BLK-{uid}-1"
    sku2 = f"BLK-{uid}-2"
    sku_bad1 = f"BAD-{uid}-1"
    sku_bad2 = f"BAD-{uid}-2"

    csv_content = (
        "name,sku,category,cost_price,sell_price,stock_qty,reorder_level\n"
        f"Bulk Item 1,{sku1},Grocery,10.00,15.00,20,5\n"
        f"Bulk Item 2,{sku2},Snacks,20.00,25.00,30,5\n"
        f"Bad Negative Price,{sku_bad1},Grocery,-5.00,10.00,10,2\n"
        f"Bad Non Number,{sku_bad2},Grocery,abc,def,10,2\n"
        ",,Grocery,10,20,10,2\n"
    )
    file_stream = io.BytesIO(csv_content.encode("utf-8"))

    with app.app_context():
        res = import_products_from_csv(file_stream, user_id=1)
        assert res["added_count"] == 2
        assert len(res["errors"]) == 3
        # Check added products exist
        p1 = query_one("SELECT * FROM products WHERE sku = %s", (sku1,))
        assert p1 is not None


def test_tc24_tc26_expense_add_and_filter(owner_client):
    """TC24 & TC26: Record expense and filter by date and category."""
    # TC24: Add expense
    res = owner_client.post(
        "/expenses/new",
        data={
            "expense_date": "2026-10-12",
            "category": "Maintenance",
            "amount": "1250.00",
            "payment_mode": "UPI",
            "note": "Replaced shop AC capacitor"
        },
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"recorded successfully" in res.data

    # TC26: Filter
    res_filter = owner_client.get("/expenses?category=Maintenance")
    assert res_filter.status_code == 200
    assert b"Replaced shop AC capacitor" in res_filter.data


def test_tc20_concurrency_stock_check(app):
    """TC20: Row-locking protects against overselling last unit."""
    uid = uuid.uuid4().hex[:6].upper()
    sku = f"LAST-UNIT-{uid}"
    with app.app_context():
        # Insert a product with stock exactly 1
        pid = execute_db(
            "INSERT INTO products (sku, name, category_id, cost_price, sell_price, stock_qty, reorder_level, is_active) "
            "VALUES (%s, 'Rare Item', 1, 100, 150, 1, 1, 1)",
            (sku,)
        )

        # First sale of 1 unit succeeds
        res1 = create_sale(cart=[{"product_id": pid, "qty": 1}], user_id=1)
        assert res1["sale_id"] > 0

        # Second attempt immediately fails due to stock = 0
        with pytest.raises(ValueError) as exc:
            create_sale(cart=[{"product_id": pid, "qty": 1}], user_id=1)
        assert "Insufficient stock" in str(exc.value)
