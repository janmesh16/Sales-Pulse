"""
Export service for SalesPulse.
Generates CSV spreadsheets and formatted PDF reports using ReportLab.
"""

import io
import csv
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from utils.formatters import format_inr


def export_daily_report_csv(report):
    """Generate CSV bytes for daily report."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["SalesPulse - Daily Sales & Profit Report"])
    writer.writerow(["Date", report["date"]])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Bills", report["bills"]])
    writer.writerow(["Gross Revenue", f"INR {report['revenue']:.2f}"])
    writer.writerow(["Cost of Goods Sold (COGS)", f"INR {report['cogs']:.2f}"])
    writer.writerow(["Gross Profit", f"INR {report['gross_profit']:.2f}"])
    writer.writerow(["Expenses", f"INR {report['expenses']:.2f}"])
    writer.writerow(["Net Profit", f"INR {report['net_profit']:.2f}"])
    writer.writerow(["Net Profit Margin", f"{report['margin_pct']:.1f}%"])
    writer.writerow([])

    writer.writerow(["Payment Mode Breakdown"])
    writer.writerow(["Payment Mode", "Bills Count", "Total Revenue"])
    for pm in report["payment_modes"]:
        writer.writerow([pm["payment_mode"], pm["count"], f"INR {pm['total']:.2f}"])
    writer.writerow([])

    writer.writerow(["Itemized Product Sales"])
    writer.writerow(["Product Name", "SKU", "Qty Sold", "Revenue", "COGS", "Profit"])
    for item in report["itemized"]:
        writer.writerow([
            item["name"], item["sku"], item["qty"],
            f"INR {item['revenue']:.2f}", f"INR {item['cogs']:.2f}", f"INR {item['profit']:.2f}"
        ])

    return output.getvalue().encode("utf-8")


def export_monthly_report_csv(report):
    """Generate CSV bytes for monthly report."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["SalesPulse - Monthly Sales & Profit Report"])
    writer.writerow(["Period", f"{report['month']}/{report['year']}"])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Bills", report["bills"]])
    writer.writerow(["Revenue", f"INR {report['revenue']:.2f}"])
    writer.writerow(["COGS", f"INR {report['cogs']:.2f}"])
    writer.writerow(["Gross Profit", f"INR {report['gross_profit']:.2f}"])
    writer.writerow(["Expenses", f"INR {report['expenses']:.2f}"])
    writer.writerow(["Net Profit", f"INR {report['net_profit']:.2f}"])
    writer.writerow(["Profit Margin", f"{report['margin_pct']:.1f}%"])
    writer.writerow(["MoM Change vs Prev Month", f"{report['mom_change']:.1f}%"])
    writer.writerow([])

    writer.writerow(["Daily Breakdown"])
    writer.writerow(["Date", "Bills", "Revenue", "COGS", "Gross Profit"])
    for day in report["daily_breakdown"]:
        writer.writerow([
            day["d"], day["bills"], f"INR {day['revenue']:.2f}",
            f"INR {day['cogs']:.2f}", f"INR {day['gross_profit']:.2f}"
        ])
    writer.writerow([])

    writer.writerow(["Top 10 Products"])
    writer.writerow(["Product Name", "SKU", "Qty Sold", "Revenue", "Profit"])
    for item in report["top_products"]:
        writer.writerow([
            item["name"], item["sku"], item["qty"],
            f"INR {item['revenue']:.2f}", f"INR {item['profit']:.2f}"
        ])

    return output.getvalue().encode("utf-8")


def export_product_performance_csv(products):
    """Generate CSV bytes for product performance report."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["SalesPulse - Product Performance & Profitability Report"])
    writer.writerow(["SKU", "Product Name", "Category", "Cost Price", "Sell Price", "Current Stock", "Units Sold", "Total Revenue", "Total Profit", "Margin %"])
    for p in products:
        writer.writerow([
            p["sku"], p["name"], p["category_name"],
            f"INR {p['cost_price']:.2f}", f"INR {p['sell_price']:.2f}", p["stock_qty"],
            p["units_sold"], f"INR {p['total_revenue']:.2f}", f"INR {p['total_profit']:.2f}", f"{p['margin_pct']:.1f}%"
        ])

    return output.getvalue().encode("utf-8")


def export_report_pdf(title, subtitle, kpi_data, table_headers, table_rows):
    """
    Generic PDF report builder using ReportLab.
    Returns bytes buffer.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    # Title & Subtitle
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )
    sub_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(subtitle, sub_style))
    elements.append(Spacer(1, 10))

    # KPI Summary Cards / Table
    if kpi_data:
        kpi_table_data = []
        row = []
        for i, (k, v) in enumerate(kpi_data.items()):
            row.append(f"<b>{k}:</b> {v}")
            if len(row) == 3 or i == len(kpi_data) - 1:
                kpi_table_data.append(row)
                row = []

        if kpi_table_data:
            kt = Table(kpi_table_data, colWidths=[180] * len(kpi_table_data[0]))
            kt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1E293B')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            elements.append(kt)
            elements.append(Spacer(1, 15))

    # Main Data Table
    if table_headers and table_rows:
        data = [table_headers] + table_rows
        # Convert any long strings into Paragraphs
        cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8)
        header_style = ParagraphStyle('HeaderCell', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white)

        formatted_data = []
        for r_idx, r in enumerate(data):
            row_cells = []
            for c in r:
                st = header_style if r_idx == 0 else cell_style
                row_cells.append(Paragraph(str(c), st))
            formatted_data.append(row_cells)

        col_count = len(table_headers)
        avail_width = 540
        col_width = avail_width / col_count

        t = Table(formatted_data, colWidths=[col_width] * col_count, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F766E')),  # Teal brand
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')])
        ]))
        elements.append(t)

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()
