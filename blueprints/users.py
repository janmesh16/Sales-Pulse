"""
User and Staff Management Blueprint for SalesPulse (Owner only).
Allows adding and managing staff accounts and deactivating login access.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from utils.decorators import owner_required
from utils.validators import is_valid_email
from db import query_all, query_one, execute_db

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("")
@owner_required
def list_users():
    """List all application users (Owner and Staff)."""
    users = query_all("SELECT user_id, name, email, role, is_active, created_at FROM users ORDER BY role ASC, name ASC")
    return render_template("users/list.html", users=users)


@users_bp.route("/new", methods=["GET", "POST"])
@owner_required
def new_user():
    """Create a new Staff or Cashier user account."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "STAFF")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("users/form.html", user=request.form)

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return render_template("users/form.html", user=request.form)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("users/form.html", user=request.form)

        existing = query_one("SELECT user_id FROM users WHERE email = %s", (email,))
        if existing:
            flash(f"A user with email '{email}' already exists.", "danger")
            return render_template("users/form.html", user=request.form)

        pwd_hash = generate_password_hash(password)
        execute_db(
            """
            INSERT INTO users (name, email, password_hash, role, is_active, created_at)
            VALUES (%s, %s, %s, %s, 1, NOW())
            """,
            (name, email, pwd_hash, role)
        )
        flash(f"Account for '{name}' created successfully!", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/form.html", user={})


@users_bp.route("/<int:user_id>/toggle", methods=["POST"])
@owner_required
def toggle_user(user_id):
    """Toggle user active status."""
    user = query_one("SELECT * FROM users WHERE user_id = %s", (user_id,))
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("users.list_users"))

    if user["role"] == "OWNER":
        flash("Cannot deactivate the Owner account.", "danger")
        return redirect(url_for("users.list_users"))

    new_status = 0 if user["is_active"] else 1
    execute_db("UPDATE users SET is_active = %s WHERE user_id = %s", (new_status, user_id))

    action_text = "activated" if new_status else "deactivated"
    flash(f"User '{user['name']}' has been {action_text}.", "info")
    return redirect(url_for("users.list_users"))
