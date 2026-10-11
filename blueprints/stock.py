"""
Stock and Inventory Management Blueprint for SalesPulse (Owner only).
Provides stock adjustment workflows, low-stock threshold monitoring,
slow-moving product detection, and inventory movement audit logs.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.decorators import owner_required
from services.stock_service import adjust_stock, get_low_stock_products, get_slow_moving_products, get_stock_movements
from db import query_all

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")


@stock_bp.route("")
@owner_required
def stock_overview():
    """View current inventory stock levels with quick restock options."""
    products = query_all(
        """
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.is_active = 1
        ORDER BY p.stock_qty ASC, p.name ASC
        """
    )
    return render_template("stock/overview.html", products=products)


@stock_bp.route("/adjust", methods=["POST"])
@owner_required
def adjust_stock_action():
    """Apply manual stock adjustments (Restock, Damage, Correction)."""
    product_id = request.form.get("product_id")
    change_qty = request.form.get("change_qty")
    reason = request.form.get("reason")

    try:
        new_qty = adjust_stock(
            product_id=product_id,
            change_qty=change_qty,
            reason=reason,
            user_id=session.get("user_id")
        )
        flash(f"Stock adjusted successfully! New stock level: {new_qty}.", "success")
    except Exception as e:
        flash(f"Stock adjustment failed: {str(e)}", "danger")

    return redirect(request.referrer or url_for("stock.stock_overview"))


@stock_bp.route("/alerts")
@owner_required
def stock_alerts():
    """Display active low-stock warnings and slow-moving items (zero sales in 30 days)."""
    low_stock = get_low_stock_products()
    slow_moving = get_slow_moving_products(days=30)
    return render_template("stock/alerts.html", low_stock=low_stock, slow_moving=slow_moving)


@stock_bp.route("/movements")
@owner_required
def movements_log():
    """Audit log of all stock movements (sales, restocks, damages, cancel returns)."""
    movements = get_stock_movements(limit=100)
    return render_template("stock/movements.html", movements=movements)
