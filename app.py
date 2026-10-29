"""
Application factory module for SalesPulse.
Initializes Flask, sets up CSRF protection, registers Blueprints,
configures security headers, Jinja filters, and error handlers.
"""

from flask import Flask, render_template, session, g, request, jsonify, flash, redirect, url_for
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from db import init_db_pool, close_db, query_one
from utils.formatters import format_inr, format_date, format_datetime, format_percent

csrf = CSRFProtect()


def create_app(config_class=Config):
    """Factory function to build and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure ProxyFix for reverse proxy deployments (Render, Railway, Heroku, Nginx)
    # Correctly handles X-Forwarded-Proto, X-Forwarded-For, X-Forwarded-Host
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Initialize connection pooling and CSRF
    init_db_pool(app.config)
    csrf.init_app(app)

    # Register teardown function to close pooled DB connections
    app.teardown_appcontext(close_db)

    # Ensure default owner name update if legacy 'Anand Verma' exists in DB
    try:
        from db import execute_db
        with app.app_context():
            execute_db("UPDATE users SET name = 'Misbah Khan' WHERE role = 'OWNER' AND name LIKE '%Anand Verma%'")
    except Exception:
        pass

    # Register Jinja2 template filters
    app.jinja_env.filters["inr"] = format_inr
    app.jinja_env.filters["date"] = format_date
    app.jinja_env.filters["datetime"] = format_datetime
    app.jinja_env.filters["percent"] = format_percent

    # Context processor to inject common variables into all templates
    @app.context_processor
    def inject_global_vars():
        currency = "₹"
        shop_name = "SalesPulse Store"
        user_name = session.get("user_name")
        try:
            curr_row = query_one("SELECT setting_value FROM settings WHERE setting_key = 'currency'")
            if curr_row:
                currency = curr_row["setting_value"]
            shop_row = query_one("SELECT setting_value FROM settings WHERE setting_key = 'shop_name'")
            if shop_row:
                shop_name = shop_row["setting_value"]
            if session.get("user_id"):
                u_row = query_one("SELECT name FROM users WHERE user_id = %s", (session.get("user_id"),))
                if u_row:
                    user_name = u_row["name"]
                    session["user_name"] = user_name
        except Exception:
            pass

        return {
            "current_user": {
                "id": session.get("user_id"),
                "name": user_name,
                "email": session.get("user_email"),
                "role": session.get("role")
            },
            "is_owner": session.get("role") == "OWNER",
            "is_staff": session.get("role") == "STAFF",
            "currency_symbol": currency,
            "shop_name": shop_name
        }

    # Security headers middleware
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Content Security Policy allowing CDNs for Bootstrap & Chart.js
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        return response

    # Error handlers
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """Handle CSRF errors gracefully instead of showing raw 400 Bad Request."""
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "CSRF session expired or invalid. Please refresh the page."}), 400
        flash("Your session expired or cookies were refreshed. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    # Register Blueprints
    from blueprints.auth import auth_bp
    from blueprints.products import products_bp
    from blueprints.sales import sales_bp
    from blueprints.expenses import expenses_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.stock import stock_bp
    from blueprints.reports import reports_bp
    from blueprints.users import users_bp
    from blueprints.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)

    return app


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 5001))
    app = create_app()
    app.run(host="127.0.0.1", port=port, debug=True)
