"""
Expenses Management Blueprint for SalesPulse (Owner only).
Allows recording operational overheads (Rent, Electricity, Salaries, etc.)
required for accurate Net Profit calculation.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.decorators import owner_required
from utils.validators import validate_expense_data
from db import query_all, query_one, execute_db

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")

EXPENSE_CATEGORIES = [
    'Rent', 'Electricity', 'Salaries', 'Transport',
    'Maintenance', 'Marketing', 'Packaging', 'Other'
]
PAYMENT_MODES = ['CASH', 'UPI', 'CARD', 'BANK']


@expenses_bp.route("")
@owner_required
def list_expenses():
    """List recorded expenses with category and date filtering."""
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    category = request.args.get("category", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    offset = (page - 1) * per_page

    where_clauses = []
    params = []

    if start_date:
        where_clauses.append("e.expense_date >= %s")
        params.append(start_date)
    if end_date:
        where_clauses.append("e.expense_date <= %s")
        params.append(end_date)
    if category:
        where_clauses.append("e.category = %s")
        params.append(category)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_res = query_one(f"SELECT COUNT(*) as total, COALESCE(SUM(amount), 0) as grand_total FROM expenses e {where_sql}", tuple(params))
    total_expenses = count_res["total"] if count_res else 0
    total_amount = float(count_res["grand_total"]) if count_res else 0.0
    total_pages = max(1, (total_expenses + per_page - 1) // per_page)

    query = f"""
        SELECT e.*, u.name as recorded_by
        FROM expenses e
        JOIN users u ON e.user_id = u.user_id
        {where_sql}
        ORDER BY e.expense_date DESC, e.expense_id DESC
        LIMIT %s OFFSET %s
    """
    params.extend([per_page, offset])
    expenses = query_all(query, tuple(params))

    return render_template(
        "expenses/list.html",
        expenses=expenses,
        categories=EXPENSE_CATEGORIES,
        selected_category=category,
        start_date=start_date,
        end_date=end_date,
        page=page,
        total_pages=total_pages,
        total_amount=total_amount
    )


@expenses_bp.route("/new", methods=["GET", "POST"])
@owner_required
def new_expense():
    """Record a new store expense."""
    if request.method == "POST":
        expense_date = request.form.get("expense_date", "").strip()
        category = request.form.get("category", "").strip()
        amount = request.form.get("amount", "").strip()
        payment_mode = request.form.get("payment_mode", "CASH")
        note = request.form.get("note", "").strip()

        is_valid, err_msg = validate_expense_data(expense_date, category, amount)
        if not is_valid:
            flash(err_msg, "danger")
            return render_template(
                "expenses/form.html",
                categories=EXPENSE_CATEGORIES,
                payment_modes=PAYMENT_MODES,
                expense=request.form
            )

        execute_db(
            """
            INSERT INTO expenses (expense_date, category, amount, payment_mode, note, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (expense_date, category, amount, payment_mode, note or None, session.get("user_id"))
        )
        flash("Expense recorded successfully!", "success")
        return redirect(url_for("expenses.list_expenses"))

    return render_template(
        "expenses/form.html",
        categories=EXPENSE_CATEGORIES,
        payment_modes=PAYMENT_MODES,
        expense={}
    )


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@owner_required
def edit_expense(expense_id):
    """Edit existing expense record."""
    expense = query_one("SELECT * FROM expenses WHERE expense_id = %s", (expense_id,))
    if not expense:
        flash("Expense record not found.", "danger")
        return redirect(url_for("expenses.list_expenses"))

    if request.method == "POST":
        expense_date = request.form.get("expense_date", "").strip()
        category = request.form.get("category", "").strip()
        amount = request.form.get("amount", "").strip()
        payment_mode = request.form.get("payment_mode", "CASH")
        note = request.form.get("note", "").strip()

        is_valid, err_msg = validate_expense_data(expense_date, category, amount)
        if not is_valid:
            flash(err_msg, "danger")
            return render_template(
                "expenses/form.html",
                categories=EXPENSE_CATEGORIES,
                payment_modes=PAYMENT_MODES,
                expense=request.form,
                is_edit=True
            )

        execute_db(
            """
            UPDATE expenses
            SET expense_date = %s, category = %s, amount = %s, payment_mode = %s, note = %s
            WHERE expense_id = %s
            """,
            (expense_date, category, amount, payment_mode, note or None, expense_id)
        )
        flash("Expense updated successfully!", "success")
        return redirect(url_for("expenses.list_expenses"))

    return render_template(
        "expenses/form.html",
        categories=EXPENSE_CATEGORIES,
        payment_modes=PAYMENT_MODES,
        expense=expense,
        is_edit=True
    )


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@owner_required
def delete_expense(expense_id):
    """Delete an expense record."""
    execute_db("DELETE FROM expenses WHERE expense_id = %s", (expense_id,))
    flash("Expense deleted successfully.", "info")
    return redirect(url_for("expenses.list_expenses"))
