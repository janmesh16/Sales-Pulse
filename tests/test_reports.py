"""
Reports, Dashboard, and Export tests for SalesPulse.
Verifies TC30, TC31, TC33, TC34, TC35, TC36, TC37.
"""

from datetime import date
from db import query_one
from services.analytics_service import get_kpis


def test_tc30_dashboard_kpis_match_sql(owner_client, app):
    """TC30: Dashboard KPI numbers match raw SQL calculations."""
    with app.app_context():
        kpis = get_kpis()
        today_sql = query_one(
            "SELECT COUNT(*) as bills, COALESCE(SUM(total_amount), 0) as rev FROM sales WHERE DATE(sale_date)=CURDATE() AND status='COMPLETED'"
        )
        assert kpis["today_bills"] == today_sql["bills"]
        assert round(kpis["today_revenue"], 2) == round(float(today_sql["rev"]), 2)


def test_tc31_all_six_chart_endpoints_return_json(owner_client):
    """TC31: All 6 Chart.js endpoints return valid HTTP 200 JSON."""
    endpoints = [
        "/api/chart/sales-trend",
        "/api/chart/top-products?metric=qty",
        "/api/chart/expense-breakdown",
        "/api/chart/category-sales",
        "/api/chart/monthly-compare",
        "/api/chart/forecast",
        "/api/kpis"
    ]
    for ep in endpoints:
        res = owner_client.get(ep)
        assert res.status_code == 200
        assert res.is_json


def test_tc33_tc34_daily_and_monthly_report_views(owner_client):
    """TC33 & TC34: Daily and Monthly reports render successfully."""
    today_str = date.today().strftime("%Y-%m-%d")
    res_daily = owner_client.get(f"/reports/daily?date={today_str}")
    assert res_daily.status_code == 200
    assert b"Daily Sales" in res_daily.data

    res_monthly = owner_client.get("/reports/monthly?year=2026&month=10")
    assert res_monthly.status_code == 200
    assert b"Monthly Performance" in res_monthly.data


def test_tc35_export_csv(owner_client):
    """TC35: CSV report export returns text/csv content."""
    res = owner_client.get("/reports/daily?export=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["Content-Type"]
    assert b"SalesPulse - Daily Sales & Profit Report" in res.data


def test_tc36_export_pdf(owner_client):
    """TC36: PDF report export returns valid application/pdf binary."""
    res = owner_client.get("/reports/daily?export=pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["Content-Type"]
    assert res.data.startswith(b"%PDF")


def test_tc37_date_range_no_data(owner_client):
    """TC37: Future date range with zero data renders cleanly without crash."""
    res = owner_client.get("/reports/custom?start_date=2099-01-01&end_date=2099-01-31")
    assert res.status_code == 200
    assert b"No sales recorded in this date range" in res.data
