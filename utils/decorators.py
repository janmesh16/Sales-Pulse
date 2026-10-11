"""
Authentication and role-based access decorators for SalesPulse.
Provides @login_required and @owner_required to protect routes.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, request, abort


def login_required(f):
    """Decorator ensuring that a user is logged in before accessing a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def owner_required(f):
    """
    Decorator ensuring that only users with the 'OWNER' role can access the route.
    Staff members attempting access are denied (403 Forbidden).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        if session.get("role") != "OWNER":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
