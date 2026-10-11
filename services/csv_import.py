"""
Bulk product CSV import service for SalesPulse.
Parses CSV uploads, validates data constraints, auto-resolves categories,
and generates detailed row-by-row error logs.
"""

import csv
import io
from db import get_db, query_one, execute_db


def import_products_from_csv(file_stream, user_id=None):
    """
    Import products from CSV stream.
    Expected header: name,sku,category,cost_price,sell_price,stock_qty,reorder_level
    Returns:
    {
        "total_rows": int,
        "added_count": int,
        "errors": [{"row": int, "sku": str, "error": str}]
    }
    """
    content = file_stream.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))

    required_fields = ["name", "sku", "category", "cost_price", "sell_price", "stock_qty", "reorder_level"]
    if not reader.fieldnames:
        return {"total_rows": 0, "added_count": 0, "errors": [{"row": 0, "sku": "N/A", "error": "CSV file is empty."}]}

    normalized_headers = {h.strip().lower(): h for h in reader.fieldnames}
    for rf in required_fields:
        if rf not in normalized_headers:
            return {
                "total_rows": 0,
                "added_count": 0,
                "errors": [{"row": 0, "sku": "N/A", "error": f"Missing required column header: '{rf}'"}]
            }

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    added_count = 0
    errors = []
    row_num = 1  # Header is row 1

    try:
        for row in reader:
            row_num += 1
            name = row.get(normalized_headers["name"], "").strip()
            sku = row.get(normalized_headers["sku"], "").strip()
            cat_name = row.get(normalized_headers["category"], "").strip()
            cost_str = row.get(normalized_headers["cost_price"], "").strip()
            sell_str = row.get(normalized_headers["sell_price"], "").strip()
            stock_str = row.get(normalized_headers["stock_qty"], "").strip()
            reorder_str = row.get(normalized_headers["reorder_level"], "").strip()

            if not name or not sku or not cat_name:
                errors.append({"row": row_num, "sku": sku or "N/A", "error": "Name, SKU, and Category are required."})
                continue

            try:
                cost = float(cost_str)
                sell = float(sell_str)
                stock = int(stock_str)
                reorder = int(reorder_str)
            except (ValueError, TypeError):
                errors.append({"row": row_num, "sku": sku, "error": "Cost, sell price, stock, and reorder must be valid numbers."})
                continue

            if cost < 0 or sell < 0 or stock < 0 or reorder < 0:
                errors.append({"row": row_num, "sku": sku, "error": "Prices and quantities cannot be negative."})
                continue

            # Check duplicate SKU
            cursor.execute("SELECT product_id FROM products WHERE sku = %s", (sku,))
            if cursor.fetchone():
                errors.append({"row": row_num, "sku": sku, "error": f"Duplicate SKU '{sku}'. Product already exists."})
                continue

            # Resolve Category
            cursor.execute("SELECT category_id FROM categories WHERE name = %s", (cat_name,))
            cat_row = cursor.fetchone()
            if cat_row:
                category_id = cat_row["category_id"]
            else:
                cursor.execute("INSERT INTO categories (name) VALUES (%s)", (cat_name,))
                category_id = cursor.lastrowid

            # Insert Product
            cursor.execute(
                """
                INSERT INTO products (sku, name, category_id, cost_price, sell_price, stock_qty, reorder_level, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, NOW())
                """,
                (sku, name, category_id, cost, sell, stock, reorder)
            )
            prod_id = cursor.lastrowid

            # Log initial stock movement if stock > 0
            if stock > 0:
                cursor.execute(
                    """
                    INSERT INTO stock_movements (product_id, change_qty, reason, user_id, created_at)
                    VALUES (%s, %s, 'RESTOCK', %s, NOW())
                    """,
                    (prod_id, stock, user_id or 1)
                )

            added_count += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()

    return {
        "total_rows": row_num - 1,
        "added_count": added_count,
        "errors": errors
    }
