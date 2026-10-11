"""
Authentication Blueprint for SalesPulse.
Handles user login, logout, password verification, session lifecycle,
and rate-limiting failed login attempts.
"""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from db import query_one

auth_bp = Blueprint("auth", __name__)

# In-memory dictionary for login failure tracking: ip_or_email -> [attempts, lock_until]
_failed_attempts = {}


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login with rate limiting and role-based redirection."""
    if "user_id" in session:
        return redirect(url_for("dashboard.owner_dashboard" if session.get("role") == "OWNER" else "dashboard.staff_home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html", email=email)

        now = datetime.now()
        # Check rate-limiting lock
        if email in _failed_attempts:
            count, lock_until = _failed_attempts[email]
            if lock_until and now < lock_until:
                remaining_secs = int((lock_until - now).total_seconds())
                flash(f"Account temporarily locked due to too many failed attempts. Try again in {remaining_secs} seconds.", "danger")
                return render_template("login.html", email=email)

        user = query_one(
            "SELECT user_id, name, email, password_hash, role, is_active FROM users WHERE email = %s",
            (email,)
        )

        if not user or not check_password_hash(user["password_hash"], password):
            # Track failure
            attempts, _ = _failed_attempts.get(email, (0, None))
            attempts += 1
            lock_until = now + timedelta(minutes=5) if attempts >= 5 else None
            _failed_attempts[email] = (attempts, lock_until)

            flash("Invalid email or password.", "danger")
            return render_template("login.html", email=email)

        if not user["is_active"]:
            flash("Your account has been deactivated. Please contact the store owner.", "danger")
            return render_template("login.html", email=email)

        # Successful login: reset failed attempts & regenerate session
        _failed_attempts.pop(email, None)
        session.clear()
        session.permanent = True
        session["user_id"] = user["user_id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["role"] = user["role"]

        flash(f"Welcome back, {user['name']}!", "success")
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)

        if user["role"] == "OWNER":
            return redirect(url_for("dashboard.owner_dashboard"))
        return redirect(url_for("dashboard.staff_home"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Clear user session and redirect to login."""
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))
