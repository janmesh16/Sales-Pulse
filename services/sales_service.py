"""
Sales business logic service for SalesPulse.
Handles transactional sale creation with row-locking, stock decrement,
historical cost/price snapshotting, invoice generation, and sale cancellation.
"""

from datetime import datetime
from db import get_db, query_one, query_all


def generate_invoice_no(cursor):
    """
    Generate daily sequential invoice numbers: SP-YYYYMMDD-0001.
    Uses the database cursor inside the transaction.
    """
    today_str = datetime.now().strftime("%Y%m%d")
    prefix = f"SP-{today_str}-"

    cursor.execute(
        "SELECT invoice_no FROM sales WHERE invoice_no LIKE %s ORDER BY sale_id DESC LIMIT 1 FOR UPDATE",
        (f"{prefix}%",)
    )
    last_inv = cursor.fetchone()

    if last_inv:
        # Extract sequence number from e.g. SP-20261012-0005
        last_seq = int(last_inv['invoice_no'].split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:04d}"


def create_sale(cart, discount=0.0, payment_mode="CASH", customer_name=None, customer_phone=None, user_id=None):
    """
    Create a new sale transaction.
    - Validates cart items and checks stock with SELECT ... FOR UPDATE.
    - Snapshots unit_price and unit_cost into sale_items.
    - Decrements stock in products table.
    - Inserts stock_movement audit records.
    - Fully transactional: commits on success, rollbacks on any error.
    """
    if not cart or not isinstance(cart, list):
        raise ValueError("Cart is empty or invalid.")

    try:
        discount = float(discount)
    except (ValueError, TypeError):
        discount = 0.0

    if discount < 0:
        raise ValueError("Discount cannot be negative.")

    if payment_mode not in ["CASH", "UPI", "CARD"]:
        raise ValueError("Invalid payment mode.")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        subtotal = 0.0
        validated_lines = []

        # Lock rows and validate stock availability
        for item in cart:
            product_id = int(item.get("product_id"))
            qty = int(item.get("qty", 0))

            if qty <= 0:
                raise ValueError("Product quantity must be greater than zero.")

            cursor.execute(
                "SELECT product_id, name, sku, sell_price, cost_price, stock_qty "
                "FROM products WHERE product_id=%s AND is_active=1 FOR UPDATE",
                (product_id,)
            )
            product = cursor.fetchone()

            if not product:
                raise ValueError(f"Product ID {product_id} is inactive or does not exist.")

            if product["stock_qty"] < qty:
                raise ValueError(
                    f"Insufficient stock for '{product['name']}'. Requested: {qty}, Available: {product['stock_qty']}."
                )

            line_total = round(float(product["sell_price"]) * qty, 2)
            subtotal += line_total

            validated_lines.append({
                "product": product,
                "qty": qty,
                "unit_price": float(product["sell_price"]),
                "unit_cost": float(product["cost_price"]),
                "line_total": line_total
            })

        subtotal = round(subtotal, 2)
        if discount > subtotal:
            raise ValueError(f"Discount (₹{discount:.2f}) cannot exceed subtotal (₹{subtotal:.2f}).")

        total_amount = round(subtotal - discount, 2)
        invoice_no = generate_invoice_no(cursor)

        # 1. Insert Sales header
        cursor.execute(
            """
            INSERT INTO sales (invoice_no, sale_date, customer_name, customer_phone,
                               subtotal, discount, total_amount, payment_mode, status, user_id)
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, 'COMPLETED', %s)
            """,
            (invoice_no, customer_name or None, customer_phone or None,
             subtotal, discount, total_amount, payment_mode, user_id)
        )
        sale_id = cursor.lastrowid

        # 2. Insert Sale Items, update stock, and log stock movements
        for line in validated_lines:
            cursor.execute(
                """
                INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, unit_cost, line_total)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (sale_id, line["product"]["product_id"], line["qty"],
                 line["unit_price"], line["unit_cost"], line["line_total"])
            )

            cursor.execute(
                "UPDATE products SET stock_qty = stock_qty - %s WHERE product_id = %s",
                (line["qty"], line["product"]["product_id"])
            )

            cursor.execute(
                """
                INSERT INTO stock_movements (product_id, change_qty, reason, ref_sale_id, user_id, created_at)
                VALUES (%s, %s, 'SALE', %s, %s, NOW())
                """,
                (line["product"]["product_id"], -line["qty"], sale_id, user_id)
            )

        conn.commit()
        return {
            "sale_id": sale_id,
            "invoice_no": invoice_no,
            "total_amount": total_amount,
            "subtotal": subtotal,
            "discount": discount
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def cancel_sale(sale_id, user_id):
    """
    Cancel an existing sale (Owner privilege).
    - Verifies sale exists and is 'COMPLETED'.
    - Restores inventory quantity in products table.
    - Inserts 'CANCEL_RETURN' stock movements.
    - Sets sale status to 'CANCELLED'.
    - Fully transactional.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM sales WHERE sale_id = %s FOR UPDATE", (sale_id,))
        sale = cursor.fetchone()

        if not sale:
            raise ValueError("Sale not found.")

        if sale["status"] == "CANCELLED":
            raise ValueError("Sale is already cancelled.")

        # Fetch sale items to restore stock
        cursor.execute("SELECT * FROM sale_items WHERE sale_id = %s", (sale_id,))
        items = cursor.fetchall()

        for item in items:
            cursor.execute(
                "UPDATE products SET stock_qty = stock_qty + %s WHERE product_id = %s",
                (item["quantity"], item["product_id"])
            )
            cursor.execute(
                """
                INSERT INTO stock_movements (product_id, change_qty, reason, ref_sale_id, user_id, created_at)
                VALUES (%s, %s, 'CANCEL_RETURN', %s, %s, NOW())
                """,
                (item["product_id"], item["quantity"], sale_id, user_id)
            )

        cursor.execute("UPDATE sales SET status = 'CANCELLED' WHERE sale_id = %s", (sale_id,))
        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def get_sale_details(sale_id):
    """Retrieve full sale record including seller name and individual line items."""
    sale = query_one(
        """
        SELECT s.*, u.name as cashier_name
        FROM sales s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.sale_id = %s
        """,
        (sale_id,)
    )
    if not sale:
        return None

    items = query_all(
        """
        SELECT si.*, p.name as product_name, p.sku
        FROM sale_items si
        JOIN products p ON si.product_id = p.product_id
        WHERE si.sale_id = %s
        ORDER BY si.item_id ASC
        """,
        (sale_id,)
    )

    sale["items"] = items
    return sale
