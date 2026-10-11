"""
Inventory and stock monitoring service for SalesPulse.
Handles manual stock adjustments, audit logging, low-stock detection,
and identification of slow-moving inventory.
"""

from db import get_db, query_all, query_one


def adjust_stock(product_id, change_qty, reason, user_id):
    """
    Manually adjust stock for restock, damage, or correction.
    Audits the adjustment into stock_movements.
    """
    valid_reasons = ['RESTOCK', 'DAMAGE', 'CORRECTION']
    if reason not in valid_reasons:
        raise ValueError(f"Invalid reason. Must be one of {', '.join(valid_reasons)}.")

    try:
        qty_change = int(change_qty)
    except (ValueError, TypeError):
        raise ValueError("Change quantity must be an integer.")

    if qty_change == 0:
        raise ValueError("Change quantity cannot be zero.")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT product_id, name, stock_qty FROM products WHERE product_id = %s FOR UPDATE", (product_id,))
        prod = cursor.fetchone()
        if not prod:
            raise ValueError("Product not found.")

        new_stock = prod["stock_qty"] + qty_change
        if new_stock < 0:
            raise ValueError(f"Adjustment would result in negative stock ({new_stock}). Available: {prod['stock_qty']}.")

        cursor.execute("UPDATE products SET stock_qty = %s WHERE product_id = %s", (new_stock, product_id))
        cursor.execute(
            """
            INSERT INTO stock_movements (product_id, change_qty, reason, user_id, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (product_id, qty_change, reason, user_id)
        )
        conn.commit()
        return new_stock
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def get_low_stock_products():
    """Retrieve all active products where stock_qty is less than or equal to reorder_level."""
    return query_all(
        """
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.is_active = 1 AND p.stock_qty <= p.reorder_level
        ORDER BY p.stock_qty ASC, p.name ASC
        """
    )


def get_slow_moving_products(days=30):
    """
    Retrieve active products that have had zero sales in the specified number of days.
    """
    return query_all(
        """
        SELECT p.*, c.name as category_name,
               (SELECT MAX(s.sale_date)
                FROM sale_items si
                JOIN sales s ON si.sale_id = s.sale_id
                WHERE si.product_id = p.product_id AND s.status = 'COMPLETED') as last_sold_date
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.is_active = 1
          AND NOT EXISTS (
              SELECT 1
              FROM sale_items si
              JOIN sales s ON si.sale_id = s.sale_id
              WHERE si.product_id = p.product_id
                AND s.status = 'COMPLETED'
                AND s.sale_date >= CURDATE() - INTERVAL %s DAY
          )
        ORDER BY p.name ASC
        """,
        (days,)
    )


def get_stock_movements(product_id=None, limit=100):
    """Retrieve audit history of inventory movements."""
    if product_id:
        return query_all(
            """
            SELECT sm.*, p.name as product_name, p.sku, u.name as user_name
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.product_id
            JOIN users u ON sm.user_id = u.user_id
            WHERE sm.product_id = %s
            ORDER BY sm.created_at DESC
            LIMIT %s
            """,
            (product_id, limit)
        )
    return query_all(
        """
        SELECT sm.*, p.name as product_name, p.sku, u.name as user_name
        FROM stock_movements sm
        JOIN products p ON sm.product_id = p.product_id
        JOIN users u ON sm.user_id = u.user_id
        ORDER BY sm.created_at DESC
        LIMIT %s
        """,
        (limit,)
    )
