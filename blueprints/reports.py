"""
Reports and Export Blueprint for SalesPulse (Owner only).
Provides Daily, Monthly, Custom Range, and Product Performance reports,
along with on-demand CSV spreadsheets and downloadable PDF generation.
"""

from datetime import datetime, date
from flask import Blueprint, render_template, request, Response, redirect, url_for, flash
from utils.decorators import owner_required
from services.analytics_service import (
    get_daily_report, get_monthly_report,
    get_custom_range_report, get_product_performance_report
)
from services.export_service import (
    export_daily_report_csv, export_monthly_report_csv,
    export_product_performance_csv, export_report_pdf
)
from utils.formatters import format_inr

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("")
@reports_bp.route("/daily")
@owner_required
def daily_report():
    """Daily revenue, COGS, profit, and itemized product sales report."""
    target_date = request.args.get("date", date.today().strftime("%Y-%m-%d")).strip()
    export_format = request.args.get("export")

    report = get_daily_report(target_date)

    if export_format == "csv":
        csv_bytes = export_daily_report_csv(report)
        return Response(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=daily_report_{target_date}.csv"}
        )

    if export_format == "pdf":
        kpi_data = {
            "Total Bills": report["bills"],
            "Revenue": format_inr(report["revenue"]),
            "COGS": format_inr(report["cogs"]),
            "Gross Profit": format_inr(report["gross_profit"]),
            "Expenses": format_inr(report["expenses"]),
            "Net Profit": format_inr(report["net_profit"]),
            "Profit Margin": f"{report['margin_pct']}%"
        }
        headers = ["Product Name", "SKU", "Qty", "Revenue", "Profit"]
        rows = [
            [it["name"], it["sku"], it["qty"], format_inr(it["revenue"]), format_inr(it["profit"])]
            for it in report["itemized"]
        ]
        pdf_bytes = export_report_pdf(
            f"Daily Sales & Profit Report - {target_date}",
            "Comprehensive breakdown of daily bills, margins, and expenses.",
            kpi_data, headers, rows
        )
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment;filename=daily_report_{target_date}.pdf"}
        )

    return render_template("reports/daily.html", report=report, selected_date=target_date)


@reports_bp.route("/monthly")
@owner_required
def monthly_report():
    """Monthly report with day-by-day table, top products, expenses, and MoM comparison."""
    now = datetime.now()
    year = int(request.args.get("year", now.year))
    month = int(request.args.get("month", now.month))
    export_format = request.args.get("export")

    report = get_monthly_report(year, month)

    if export_format == "csv":
        csv_bytes = export_monthly_report_csv(report)
        return Response(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=monthly_report_{year}_{month:02d}.csv"}
        )

    if export_format == "pdf":
        kpi_data = {
            "Total Bills": report["bills"],
            "Monthly Revenue": format_inr(report["revenue"]),
            "COGS": format_inr(report["cogs"]),
            "Gross Profit": format_inr(report["gross_profit"]),
            "Expenses": format_inr(report["expenses"]),
            "Net Profit": format_inr(report["net_profit"]),
            "Margin %": f"{report['margin_pct']}%",
            "MoM Change": f"{report['mom_change']}%"
        }
        headers = ["Date", "Bills", "Revenue", "COGS", "Gross Profit"]
        rows = [
            [str(d["d"]), d["bills"], format_inr(d["revenue"]), format_inr(d["cogs"]), format_inr(d["gross_profit"])]
            for d in report["daily_breakdown"]
        ]
        pdf_bytes = export_report_pdf(
            f"Monthly Performance Report - {month:02d}/{year}",
            "Month-to-date financial metrics, daily trend, and product rankings.",
            kpi_data, headers, rows
        )
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment;filename=monthly_report_{year}_{month:02d}.pdf"}
        )

    return render_template("reports/monthly.html", report=report, year=year, month=month)


@reports_bp.route("/custom")
@owner_required
def custom_range_report():
    """Custom date range analytics and sales metrics."""
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    export_format = request.args.get("export")

    report = None
    if start_date and end_date:
        report = get_custom_range_report(start_date, end_date)

        if export_format == "pdf" and report:
            kpi_data = {
                "Range": f"{start_date} to {end_date}",
                "Bills": report["bills"],
                "Revenue": format_inr(report["revenue"]),
                "COGS": format_inr(report["cogs"]),
                "Gross Profit": format_inr(report["gross_profit"]),
                "Expenses": format_inr(report["expenses"]),
                "Net Profit": format_inr(report["net_profit"])
            }
            headers = ["Product Name", "SKU", "Qty", "Revenue", "Profit"]
            rows = [
                [it["name"], it["sku"], it["qty"], format_inr(it["revenue"]), format_inr(it["profit"])]
                for it in report["product_sales"]
            ]
            pdf_bytes = export_report_pdf(
                f"Sales Report ({start_date} to {end_date})",
                "Custom date range sales and profitability aggregation.",
                kpi_data, headers, rows
            )
            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={"Content-Disposition": f"attachment;filename=custom_report_{start_date}_{end_date}.pdf"}
            )

    return render_template("reports/custom.html", report=report, start_date=start_date, end_date=end_date)


@reports_bp.route("/products")
@owner_required
def product_performance():
    """Product performance and profit margin ranking."""
    export_format = request.args.get("export")
    products = get_product_performance_report()

    if export_format == "csv":
        csv_bytes = export_product_performance_csv(products)
        return Response(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=product_performance_report.csv"}
        )

    if export_format == "pdf":
        headers = ["SKU", "Product Name", "Category", "Units Sold", "Revenue", "Profit", "Margin %"]
        rows = [
            [p["sku"], p["name"][:20], p["category_name"], p["units_sold"],
             format_inr(p["total_revenue"]), format_inr(p["total_profit"]), f"{p['margin_pct']}%"]
            for p in products
        ]
        pdf_bytes = export_report_pdf(
            "Product Performance & Margin Ranking",
            "Comprehensive catalog profitability and volume analysis.",
            {}, headers, rows
        )
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment;filename=product_performance.pdf"}
        )

    return render_template("reports/products.html", products=products)
