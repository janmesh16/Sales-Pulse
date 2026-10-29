"""
Dashboard Blueprint for SalesPulse.
Renders Owner Dashboard (KPIs, Charts) and Staff Home (Daily cashier summary).
Exposes JSON endpoints for Chart.js client-side rendering.
"""

from flask import Blueprint, render_template, session, jsonify, request, redirect, url_for
from utils.decorators import login_required, owner_required
from services.analytics_service import (
    get_kpis, get_daily_sales_trend, get_top_products,
    get_expense_breakdown_current_month, get_category_sales,
    get_revenue_vs_expenses
)
from services.forecast import get_sales_forecast
from db import query_all, query_one

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """Root redirect depending on user login state."""
    if "user_id" in session:
        return redirect(url_for("dashboard.owner_dashboard" if session.get("role") == "OWNER" else "dashboard.staff_home"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/dashboard")
@owner_required
def owner_dashboard():
    """Main Owner analytics and financial overview dashboard."""
    kpi_data = get_kpis()
    return render_template("dashboard.html", kpis=kpi_data)


@dashboard_bp.route("/home")
@login_required
def staff_home():
    """Cashier home screen with personal today metrics and quick sale button."""
    user_id = session.get("user_id")

    # Today's personal sales statistics
    stats = query_one(
        """
        SELECT COUNT(*) as bills, COALESCE(SUM(total_amount), 0) as total_sales
        FROM sales
        WHERE user_id = %s AND DATE(sale_date) = CURDATE() AND status = 'COMPLETED'
        """,
        (user_id,)
    )

    recent_sales = query_all(
        """
        SELECT s.*, (SELECT COUNT(*) FROM sale_items WHERE sale_id = s.sale_id) as items_count
        FROM sales s
        WHERE s.user_id = %s AND DATE(s.sale_date) = CURDATE()
        ORDER BY s.sale_date DESC
        LIMIT 5
        """,
        (user_id,)
    )

    return render_template(
        "staff_home.html",
        bills_count=stats["bills"] if stats else 0,
        total_sales=float(stats["total_sales"]) if stats else 0.0,
        recent_sales=recent_sales
    )


# -------------------------------------------------------------
# JSON Chart APIs (Owner Only)
# -------------------------------------------------------------

@dashboard_bp.route("/api/kpis")
@owner_required
def api_kpis():
    """Returns current KPIs in JSON format."""
    return jsonify(get_kpis())


@dashboard_bp.route("/api/chart/sales-trend")
@owner_required
def api_chart_sales_trend():
    """30-day daily sales & profit trend."""
    return jsonify(get_daily_sales_trend(days=30))


@dashboard_bp.route("/api/chart/top-products")
@owner_required
def api_chart_top_products():
    """Top 5 best-selling products this month."""
    metric = request.args.get("metric", "qty")
    return jsonify(get_top_products(metric=metric, limit=5))


@dashboard_bp.route("/api/chart/expense-breakdown")
@owner_required
def api_chart_expense_breakdown():
    """Monthly expense breakdown by category."""
    return jsonify(get_expense_breakdown_current_month())


@dashboard_bp.route("/api/chart/category-sales")
@owner_required
def api_chart_category_sales():
    """Category-wise revenue distribution."""
    return jsonify(get_category_sales())


@dashboard_bp.route("/api/chart/monthly-compare")
@owner_required
def api_chart_monthly_compare():
    """Grouped 6-month Revenue vs Expenses comparison."""
    return jsonify(get_revenue_vs_expenses(months=6))


@dashboard_bp.route("/api/chart/forecast")
@owner_required
def api_chart_forecast():
    """7-day sales forecast using rolling moving average."""
    return jsonify(get_sales_forecast(lookback_days=28, forecast_days=7))
