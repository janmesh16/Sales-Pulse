"""
Sales and POS Billing Blueprint for SalesPulse.
Handles the retail billing terminal, receipt generation, sales history browsing,
and owner cancellation workflow.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from utils.decorators import login_required, owner_required
from services.sales_service import create_sale, cancel_sale, get_sale_details
from db import query_all, query_one

sales_bp = Blueprint("sales", __name__, url_prefix="/sales")


@sales_bp.route("/new")
@login_required
def new_sale():
    """Render the POS billing interface."""
    # Pre-load popular products for quick selection
    popular_products = query_all(
        """
        SELECT product_id, sku, name, sell_price, stock_qty
        FROM products
        WHERE is_active = 1 AND stock_qty > 0
        ORDER BY stock_qty DESC
        LIMIT 12
        """
    )
    for p in popular_products:
        p["sell_price"] = float(p["sell_price"])

    return render_template("sales/billing.html", popular_products=popular_products)


@sales_bp.route("/create", methods=["POST"])
@login_required
def api_create_sale():
    """
    Handle POS checkout submission.
    Accepts JSON payload: {cart: [{product_id, qty}], discount, payment_mode, customer_name, customer_phone}
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    cart = data.get("cart")
    discount = data.get("discount", 0.0)
    payment_mode = data.get("payment_mode", "CASH")
    customer_name = data.get("customer_name", "").strip()
    customer_phone = data.get("customer_phone", "").strip()

    if isinstance(cart, str):
        import json
        try:
            cart = json.loads(cart)
        except Exception:
            return jsonify({"success": False, "error": "Invalid cart format."}), 400

    if not cart:
        return jsonify({"success": False, "error": "Cart cannot be empty."}), 400

    try:
        result = create_sale(
            cart=cart,
            discount=discount,
            payment_mode=payment_mode,
            customer_name=customer_name,
            customer_phone=customer_phone,
            user_id=session.get("user_id")
        )
        return jsonify({
            "success": True,
            "sale_id": result["sale_id"],
            "invoice_no": result["invoice_no"],
            "redirect_url": url_for("sales.view_receipt", sale_id=result["sale_id"])
        })
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to record sale: {str(e)}"}), 500


@sales_bp.route("")
@login_required
def list_sales():
    """
    View sales transactions list.
    Owner can filter by date range, cashier, status.
    Staff is strictly restricted to viewing only their own sales created today.
    """
    user_role = session.get("role")
    user_id = session.get("user_id")

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    status = request.args.get("status", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    offset = (page - 1) * per_page

    where_clauses = []
    params = []

    if user_role == "STAFF":
        # Enforce staff restriction: only own sales for current day
        where_clauses.append("s.user_id = %s AND DATE(s.sale_date) = CURDATE()")
        params.append(user_id)
    else:
        # Owner filters
        if start_date:
            where_clauses.append("DATE(s.sale_date) >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("DATE(s.sale_date) <= %s")
            params.append(end_date)
        if status:
            where_clauses.append("s.status = %s")
            params.append(status)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_res = query_one(f"SELECT COUNT(*) as total FROM sales s {where_sql}", tuple(params))
    total_sales = count_res["total"] if count_res else 0
    total_pages = max(1, (total_sales + per_page - 1) // per_page)

    query = f"""
        SELECT s.*, u.name as cashier_name,
               (SELECT COUNT(*) FROM sale_items WHERE sale_id = s.sale_id) as items_count
        FROM sales s
        JOIN users u ON s.user_id = u.user_id
        {where_sql}
        ORDER BY s.sale_date DESC
        LIMIT %s OFFSET %s
    """
    params.extend([per_page, offset])
    sales = query_all(query, tuple(params))

    return render_template(
        "sales/list.html",
        sales=sales,
        start_date=start_date,
        end_date=end_date,
        selected_status=status,
        page=page,
        total_pages=total_pages,
        total_sales=total_sales
    )


@sales_bp.route("/<int:sale_id>/receipt")
@login_required
def view_receipt(sale_id):
    """Render printable invoice receipt with store settings."""
    sale = get_sale_details(sale_id)
    if not sale:
        flash("Sale invoice not found.", "danger")
        return redirect(url_for("sales.list_sales"))

    # Security check: staff can only view receipt if it's their own sale or today's
    if session.get("role") == "STAFF" and sale["user_id"] != session.get("user_id"):
        abort(403)

    # Fetch shop settings for invoice header
    settings_rows = query_all("SELECT setting_key, setting_value FROM settings")
    settings = {r["setting_key"]: r["setting_value"] for r in settings_rows}

    return render_template("sales/receipt.html", sale=sale, settings=settings)


@sales_bp.route("/<int:sale_id>/cancel", methods=["POST"])
@owner_required
def cancel_sale_action(sale_id):
    """Cancel sale and return stock back into inventory (Owner only)."""
    try:
        cancel_sale(sale_id, user_id=session.get("user_id"))
        flash(f"Sale #{sale_id} has been successfully cancelled and stock restored.", "success")
    except Exception as e:
        flash(f"Could not cancel sale: {str(e)}", "danger")

    return redirect(url_for("sales.list_sales"))
