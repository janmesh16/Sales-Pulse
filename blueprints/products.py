"""
Products and Categories Blueprint for SalesPulse.
Provides product catalog browsing, CRUD operations for Owner,
soft deactivation, CSV imports, and JSON search API for the POS screen.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import login_required, owner_required
from utils.validators import validate_product_data
from services.csv_import import import_products_from_csv
from db import query_all, query_one, execute_db

products_bp = Blueprint("products", __name__, url_prefix="/products")


@products_bp.route("")
@login_required
def list_products():
    """Display product catalog with search, category filtering, and pagination."""
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = 20
    offset = (page - 1) * per_page

    where_clauses = ["p.is_active = 1"]
    params = []

    if search:
        where_clauses.append("(p.name LIKE %s OR p.sku LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    if category_id:
        where_clauses.append("p.category_id = %s")
        params.append(category_id)

    where_sql = " AND ".join(where_clauses)

    count_res = query_one(f"SELECT COUNT(*) as total FROM products p WHERE {where_sql}", tuple(params))
    total_products = count_res["total"] if count_res else 0
    total_pages = max(1, (total_products + per_page - 1) // per_page)

    query = f"""
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE {where_sql}
        ORDER BY p.name ASC
        LIMIT %s OFFSET %s
    """
    params.extend([per_page, offset])
    products = query_all(query, tuple(params))

    categories = query_all("SELECT * FROM categories ORDER BY name ASC")

    return render_template(
        "products/list.html",
        products=products,
        categories=categories,
        search=search,
        selected_category=category_id,
        page=page,
        total_pages=total_pages,
        total_products=total_products
    )


@products_bp.route("/new", methods=["GET", "POST"])
@owner_required
def new_product():
    """Create a new product (Owner only)."""
    categories = query_all("SELECT * FROM categories ORDER BY name ASC")

    if request.method == "POST":
        sku = request.form.get("sku", "").strip().upper()
        name = request.form.get("name", "").strip()
        category_id = request.form.get("category_id")
        cost_price = request.form.get("cost_price")
        sell_price = request.form.get("sell_price")
        stock_qty = request.form.get("stock_qty")
        reorder_level = request.form.get("reorder_level", 5)

        is_valid, err_msg, warn_msg = validate_product_data(sku, name, cost_price, sell_price, stock_qty, reorder_level)
        if not is_valid:
            flash(err_msg, "danger")
            return render_template("products/form.html", categories=categories, product=request.form)

        # Check duplicate SKU
        existing = query_one("SELECT product_id FROM products WHERE sku = %s", (sku,))
        if existing:
            flash(f"A product with SKU '{sku}' already exists.", "danger")
            return render_template("products/form.html", categories=categories, product=request.form)

        if not category_id:
            flash("Please select a category.", "danger")
            return render_template("products/form.html", categories=categories, product=request.form)

        # Insert product
        execute_db(
            """
            INSERT INTO products (sku, name, category_id, cost_price, sell_price, stock_qty, reorder_level, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1, NOW())
            """,
            (sku, name, category_id, cost_price, sell_price, stock_qty, reorder_level)
        )

        if warn_msg:
            flash(warn_msg, "warning")
        flash(f"Product '{name}' added successfully!", "success")
        return redirect(url_for("products.list_products"))

    return render_template("products/form.html", categories=categories, product={})


@products_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@owner_required
def edit_product(product_id):
    """Edit existing product details (Owner only). Historical sales prices remain untouched."""
    product = query_one("SELECT * FROM products WHERE product_id = %s", (product_id,))
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("products.list_products"))

    categories = query_all("SELECT * FROM categories ORDER BY name ASC")

    if request.method == "POST":
        sku = request.form.get("sku", "").strip().upper()
        name = request.form.get("name", "").strip()
        category_id = request.form.get("category_id")
        cost_price = request.form.get("cost_price")
        sell_price = request.form.get("sell_price")
        stock_qty = request.form.get("stock_qty")
        reorder_level = request.form.get("reorder_level", 5)

        is_valid, err_msg, warn_msg = validate_product_data(sku, name, cost_price, sell_price, stock_qty, reorder_level)
        if not is_valid:
            flash(err_msg, "danger")
            return render_template("products/form.html", categories=categories, product=request.form, is_edit=True)

        # Check duplicate SKU excluding current
        existing = query_one("SELECT product_id FROM products WHERE sku = %s AND product_id != %s", (sku, product_id))
        if existing:
            flash(f"Another product with SKU '{sku}' already exists.", "danger")
            return render_template("products/form.html", categories=categories, product=request.form, is_edit=True)

        execute_db(
            """
            UPDATE products
            SET sku = %s, name = %s, category_id = %s, cost_price = %s,
                sell_price = %s, stock_qty = %s, reorder_level = %s
            WHERE product_id = %s
            """,
            (sku, name, category_id, cost_price, sell_price, stock_qty, reorder_level, product_id)
        )

        if warn_msg:
            flash(warn_msg, "warning")
        flash(f"Product '{name}' updated successfully!", "success")
        return redirect(url_for("products.list_products"))

    return render_template("products/form.html", categories=categories, product=product, is_edit=True)


@products_bp.route("/<int:product_id>/delete", methods=["POST"])
@owner_required
def delete_product(product_id):
    """Soft delete (deactivate) a product so historical sales references remain intact."""
    product = query_one("SELECT * FROM products WHERE product_id = %s", (product_id,))
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("products.list_products"))

    execute_db("UPDATE products SET is_active = 0 WHERE product_id = %s", (product_id,))
    flash(f"Product '{product['name']}' has been deactivated.", "info")
    return redirect(url_for("products.list_products"))


@products_bp.route("/categories", methods=["GET", "POST"])
@owner_required
def categories_manage():
    """Manage product categories."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Category name cannot be empty.", "danger")
        else:
            existing = query_one("SELECT category_id FROM categories WHERE name = %s", (name,))
            if existing:
                flash(f"Category '{name}' already exists.", "danger")
            else:
                execute_db("INSERT INTO categories (name) VALUES (%s)", (name,))
                flash(f"Category '{name}' created successfully!", "success")
        return redirect(url_for("products.categories_manage"))

    categories = query_all(
        """
        SELECT c.*, COUNT(p.product_id) as product_count
        FROM categories c
        LEFT JOIN products p ON c.category_id = p.category_id AND p.is_active = 1
        GROUP BY c.category_id
        ORDER BY c.name ASC
        """
    )
    return render_template("products/categories.html", categories=categories)


@products_bp.route("/import", methods=["GET", "POST"])
@owner_required
def import_csv():
    """Bulk import products via CSV file upload."""
    if request.method == "POST":
        if "csv_file" not in request.files:
            flash("No file part selected.", "danger")
            return redirect(request.url)

        file = request.files["csv_file"]
        if file.filename == "":
            flash("Please choose a CSV file to upload.", "danger")
            return redirect(request.url)

        if not file.filename.lower().endswith(".csv"):
            flash("Invalid file format. Please upload a .csv file.", "danger")
            return redirect(request.url)

        try:
            result = import_products_from_csv(file.stream, user_id=session.get("user_id"))
            return render_template("products/import_results.html", result=result)
        except Exception as e:
            flash(f"Error during import: {str(e)}", "danger")
            return redirect(request.url)

    return render_template("products/import.html")


@products_bp.route("/api/search")
@login_required
def api_search_products():
    """
    JSON search endpoint for POS billing autocomplete.
    Staff members receive product info with sell_price, but cost_price is NEVER sent.
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    sql = """
        SELECT product_id, sku, name, sell_price, stock_qty
        FROM products
        WHERE is_active = 1 AND (name LIKE %s OR sku LIKE %s)
        ORDER BY name ASC
        LIMIT 10
    """
    rows = query_all(sql, (f"%{query}%", f"%{query}%"))
    for r in rows:
        r["sell_price"] = float(r["sell_price"])
    return jsonify(rows)
