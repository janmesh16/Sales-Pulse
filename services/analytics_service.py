"""
Analytics and financial reporting service for SalesPulse.
Calculates Revenue, COGS, Gross Profit, Expenses, Net Profit, and Profit Margins.
Ensures cancelled sales are strictly excluded from all metrics.
"""

from datetime import datetime, date, timedelta
from db import query_one, query_all


def get_kpis():
    """
    Compute core Key Performance Indicators for the Owner dashboard:
    - Today's sales revenue & bill count
    - This month's revenue, COGS, expenses, net profit, margin %
    - Low-stock count
    - Best-selling product this month
    - Month-over-month (MoM) revenue change percentage
    """
    now = datetime.now()
    cur_year = now.year
    cur_month = now.month

    # Previous month calculation
    if cur_month == 1:
        prev_year = cur_year - 1
        prev_month = 12
    else:
        prev_year = cur_year
        prev_month = cur_month - 1

    # 1. Today's sales
    today_data = query_one(
        """
        SELECT COUNT(*) as bills, COALESCE(SUM(total_amount), 0) as revenue
        FROM sales
        WHERE DATE(sale_date) = CURDATE() AND status = 'COMPLETED'
        """
    )
    today_bills = today_data["bills"] if today_data else 0
    today_revenue = float(today_data["revenue"]) if today_data else 0.0

    # 2. Current month revenue & COGS
    cur_sales = query_one(
        """
        SELECT COALESCE(SUM(total_amount), 0) as revenue
        FROM sales
        WHERE status = 'COMPLETED'
          AND YEAR(sale_date) = %s AND MONTH(sale_date) = %s
        """,
        (cur_year, cur_month)
    )
    month_revenue = float(cur_sales["revenue"]) if cur_sales else 0.0

    cur_cogs = query_one(
        """
        SELECT COALESCE(SUM(si.quantity * si.unit_cost), 0) as cogs
        FROM sale_items si
        JOIN sales s ON s.sale_id = si.sale_id
        WHERE s.status = 'COMPLETED'
          AND YEAR(s.sale_date) = %s AND MONTH(s.sale_date) = %s
        """,
        (cur_year, cur_month)
    )
    month_cogs = float(cur_cogs["cogs"]) if cur_cogs else 0.0
    month_gross_profit = round(month_revenue - month_cogs, 2)

    # Current month expenses
    cur_expenses = query_one(
        """
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE YEAR(expense_date) = %s AND MONTH(expense_date) = %s
        """,
        (cur_year, cur_month)
    )
    month_expenses = float(cur_expenses["total"]) if cur_expenses else 0.0
    month_net_profit = round(month_gross_profit - month_expenses, 2)

    month_margin_pct = round((month_net_profit / month_revenue * 100), 1) if month_revenue > 0 else 0.0

    # 3. Previous month revenue for MoM comparison
    prev_sales = query_one(
        """
        SELECT COALESCE(SUM(total_amount), 0) as revenue
        FROM sales
        WHERE status = 'COMPLETED'
          AND YEAR(sale_date) = %s AND MONTH(sale_date) = %s
        """,
        (prev_year, prev_month)
    )
    prev_revenue = float(prev_sales["revenue"]) if prev_sales else 0.0

    if prev_revenue > 0:
        mom_change_pct = round(((month_revenue - prev_revenue) / prev_revenue) * 100, 1)
    else:
        mom_change_pct = 100.0 if month_revenue > 0 else 0.0

    # 4. Low stock count
    low_stock = query_one(
        """
        SELECT COUNT(*) as count
        FROM products
        WHERE is_active = 1 AND stock_qty <= reorder_level
        """
    )
    low_stock_count = low_stock["count"] if low_stock else 0

    # 5. Best selling product this month
    top_prod = query_one(
        """
        SELECT p.name, SUM(si.quantity) as qty
        FROM sale_items si
        JOIN sales s ON s.sale_id = si.sale_id
        JOIN products p ON p.product_id = si.product_id
        WHERE s.status = 'COMPLETED'
          AND YEAR(s.sale_date) = %s AND MONTH(s.sale_date) = %s
        GROUP BY p.product_id
        ORDER BY qty DESC
        LIMIT 1
        """,
        (cur_year, cur_month)
    )
    best_seller = top_prod["name"] if top_prod else "N/A"

    return {
        "today_bills": today_bills,
        "today_revenue": round(today_revenue, 2),
        "month_revenue": round(month_revenue, 2),
        "month_cogs": round(month_cogs, 2),
        "month_expenses": round(month_expenses, 2),
        "month_gross_profit": month_gross_profit,
        "month_net_profit": month_net_profit,
        "month_margin_pct": month_margin_pct,
        "low_stock_count": low_stock_count,
        "best_seller": best_seller,
        "mom_change_pct": mom_change_pct
    }


def get_daily_sales_trend(days=30):
    """
    Returns daily revenue and gross profit for the last `days` days.
    """
    rows = query_all(
        """
        SELECT DATE(s.sale_date) as d,
               COALESCE(SUM(s.total_amount), 0) as revenue,
               COALESCE(SUM(si.quantity * si.unit_cost), 0) as cogs
        FROM sales s
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        WHERE s.status = 'COMPLETED'
          AND s.sale_date >= CURDATE() - INTERVAL %s DAY
        GROUP BY DATE(s.sale_date)
        ORDER BY d ASC
        """,
        (days - 1,)
    )

    data_map = {}
    for r in rows:
        d_str = r["d"].strftime("%Y-%m-%d") if hasattr(r["d"], "strftime") else str(r["d"])
        rev = float(r["revenue"])
        cogs = float(r["cogs"])
        data_map[d_str] = {
            "revenue": round(rev, 2),
            "profit": round(rev - cogs, 2)
        }

    # Generate contiguous sequence of dates
    labels = []
    revenues = []
    profits = []
    start_date = date.today() - timedelta(days=days - 1)

    for i in range(days):
        cur_d = start_date + timedelta(days=i)
        cur_str = cur_d.strftime("%Y-%m-%d")
        labels.append(cur_d.strftime("%d %b"))
        val = data_map.get(cur_str, {"revenue": 0.0, "profit": 0.0})
        revenues.append(val["revenue"])
        profits.append(val["profit"])

    return {
        "labels": labels,
        "revenue": revenues,
        "profit": profits
    }


def get_top_products(metric="qty", limit=5):
    """
    Get top products this month sorted by quantity or revenue.
    """
    order_clause = "qty DESC" if metric == "qty" else "revenue DESC"
    rows = query_all(
        f"""
        SELECT p.name,
               SUM(si.quantity) as qty,
               SUM(si.line_total) as revenue,
               SUM(si.line_total - (si.quantity * si.unit_cost)) as profit
        FROM sale_items si
        JOIN sales s ON s.sale_id = si.sale_id
        JOIN products p ON p.product_id = si.product_id
        WHERE s.status = 'COMPLETED'
          AND s.sale_date >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
        GROUP BY p.product_id
        ORDER BY {order_clause}
        LIMIT %s
        """,
        (limit,)
    )

    labels = [r["name"] for r in rows]
    quantities = [int(r["qty"]) for r in rows]
    revenues = [float(r["revenue"]) for r in rows]
    profits = [float(r["profit"]) for r in rows]

    return {
        "labels": labels,
        "quantities": quantities,
        "revenues": revenues,
        "profits": profits
    }


def get_expense_breakdown_current_month():
    """Expense totals grouped by category for the current month."""
    rows = query_all(
        """
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE YEAR(expense_date) = YEAR(CURDATE()) AND MONTH(expense_date) = MONTH(CURDATE())
        GROUP BY category
        ORDER BY total DESC
        """
    )
    labels = [r["category"] for r in rows]
    amounts = [float(r["total"]) for r in rows]
    return {"labels": labels, "amounts": amounts}


def get_category_sales():
    """Sales revenue grouped by category for the last 30 days."""
    rows = query_all(
        """
        SELECT c.name as category, SUM(si.line_total) as revenue
        FROM sale_items si
        JOIN sales s ON s.sale_id = si.sale_id
        JOIN products p ON p.product_id = si.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE s.status = 'COMPLETED'
          AND s.sale_date >= CURDATE() - INTERVAL 30 DAY
        GROUP BY c.category_id
        ORDER BY revenue DESC
        """
    )
    labels = [r["category"] for r in rows]
    revenues = [float(r["revenue"]) for r in rows]
    return {"labels": labels, "revenues": revenues}


def get_revenue_vs_expenses(months=6):
    """Monthly revenue vs expenses for the past N months."""
    sales_rows = query_all(
        """
        SELECT DATE_FORMAT(sale_date, '%Y-%m') as ym,
               SUM(total_amount) as revenue
        FROM sales
        WHERE status = 'COMPLETED'
          AND sale_date >= CURDATE() - INTERVAL %s MONTH
        GROUP BY ym
        ORDER BY ym ASC
        """,
        (months,)
    )
    exp_rows = query_all(
        """
        SELECT DATE_FORMAT(expense_date, '%Y-%m') as ym,
               SUM(amount) as expenses
        FROM expenses
        WHERE expense_date >= CURDATE() - INTERVAL %s MONTH
        GROUP BY ym
        ORDER BY ym ASC
        """,
        (months,)
    )

    sales_map = {r["ym"]: float(r["revenue"]) for r in sales_rows}
    exp_map = {r["ym"]: float(r["expenses"]) for r in exp_rows}

    all_yms = sorted(list(set(list(sales_map.keys()) + list(exp_map.keys()))))
    labels = []
    revenues = []
    expenses = []

    for ym in all_yms:
        try:
            dt = datetime.strptime(ym, "%Y-%m")
            labels.append(dt.strftime("%b %Y"))
        except Exception:
            labels.append(ym)
        revenues.append(round(sales_map.get(ym, 0.0), 2))
        expenses.append(round(exp_map.get(ym, 0.0), 2))

    return {
        "labels": labels,
        "revenues": revenues,
        "expenses": expenses
    }


def get_daily_report(report_date):
    """
    Comprehensive daily report:
    Total bills, revenue, COGS, gross profit, expenses, net profit,
    payment mode breakdown, and itemized product sales.
    """
    # Summary
    summary = query_one(
        """
        SELECT COUNT(DISTINCT s.sale_id) as bills,
               COALESCE(SUM(s.total_amount), 0) as revenue,
               COALESCE(SUM(si.quantity * si.unit_cost), 0) as cogs
        FROM sales s
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        WHERE DATE(s.sale_date) = %s AND s.status = 'COMPLETED'
        """,
        (report_date,)
    )

    bills = summary["bills"] if summary else 0
    revenue = float(summary["revenue"]) if summary else 0.0
    cogs = float(summary["cogs"]) if summary else 0.0
    gross_profit = round(revenue - cogs, 2)

    # Expenses on that day
    exp_data = query_one(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE expense_date = %s",
        (report_date,)
    )
    expenses = float(exp_data["total"]) if exp_data else 0.0
    net_profit = round(gross_profit - expenses, 2)
    margin_pct = round((net_profit / revenue * 100), 1) if revenue > 0 else 0.0

    # Payment modes
    payment_modes = query_all(
        """
        SELECT payment_mode, COUNT(*) as count, SUM(total_amount) as total
        FROM sales
        WHERE DATE(sale_date) = %s AND status = 'COMPLETED'
        GROUP BY payment_mode
        """,
        (report_date,)
    )

    # Itemized product breakdown
    itemized = query_all(
        """
        SELECT p.name, p.sku, SUM(si.quantity) as qty,
               SUM(si.line_total) as revenue,
               SUM(si.quantity * si.unit_cost) as cogs,
               SUM(si.line_total - (si.quantity * si.unit_cost)) as profit
        FROM sale_items si
        JOIN sales s ON s.sale_id = si.sale_id
        JOIN products p ON p.product_id = si.product_id
        WHERE DATE(s.sale_date) = %s AND s.status = 'COMPLETED'
        GROUP BY p.product_id
        ORDER BY revenue DESC
        """,
        (report_date,)
    )

    return {
        "date": report_date,
        "bills": bills,
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "expenses": expenses,
        "net_profit": net_profit,
        "margin_pct": margin_pct,
        "payment_modes": payment_modes,
        "itemized": itemized
    }


def get_monthly_report(year, month):
    """
    Comprehensive monthly report:
    Daily breakdown table, top 10 products, category summary, expenses by category,
    net profit, and comparison with previous month.
    """
    # Monthly sales summary
    sales_sum = query_one(
        """
        SELECT COUNT(DISTINCT s.sale_id) as bills,
               COALESCE(SUM(s.total_amount), 0) as revenue,
               COALESCE(SUM(si.quantity * si.unit_cost), 0) as cogs
        FROM sales s
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        WHERE YEAR(s.sale_date) = %s AND MONTH(s.sale_date) = %s AND s.status = 'COMPLETED'
        """,
        (year, month)
    )

    bills = sales_sum["bills"] if sales_sum else 0
    revenue = float(sales_sum["revenue"]) if sales_sum else 0.0
    cogs = float(sales_sum["cogs"]) if sales_sum else 0.0
    gross_profit = round(revenue - cogs, 2)

    # Monthly expenses
    exp_sum = query_one(
        """
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE YEAR(expense_date) = %s AND MONTH(expense_date) = %s
        """,
        (year, month)
    )
    expenses = float(exp_sum["total"]) if exp_sum else 0.0
    net_profit = round(gross_profit - expenses, 2)
    margin_pct = round((net_profit / revenue * 100), 1) if revenue > 0 else 0.0

    # Daily breakdown
    daily_rows = query_all(
        """
        SELECT DATE(s.sale_date) as d,
               COUNT(DISTINCT s.sale_id) as bills,
               SUM(s.total_amount) as revenue,
               SUM(si.quantity * si.unit_cost) as cogs,
               (SUM(s.total_amount) - SUM(si.quantity * si.unit_cost)) as gross_profit
        FROM sales s
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        WHERE YEAR(s.sale_date) = %s AND MONTH(s.sale_date) = %s AND s.status = 'COMPLETED'
        GROUP BY DATE(s.sale_date)
        ORDER BY d ASC
        """,
        (year, month)
    )

    # Top 10 products
    top_products = query_all(
        """
        SELECT p.name, p.sku, SUM(si.quantity) as qty,
               SUM(si.line_total) as revenue,
               SUM(si.line_total - (si.quantity * si.unit_cost)) as profit
        FROM sale_items si
        JOIN sales s ON s.sale_id = si.sale_id
        JOIN products p ON p.product_id = si.product_id
        WHERE YEAR(s.sale_date) = %s AND MONTH(s.sale_date) = %s AND s.status = 'COMPLETED'
        GROUP BY p.product_id
        ORDER BY revenue DESC
        LIMIT 10
        """,
        (year, month)
    )

    # Expenses by category
    exp_categories = query_all(
        """
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE YEAR(expense_date) = %s AND MONTH(expense_date) = %s
        GROUP BY category
        ORDER BY total DESC
        """,
        (year, month)
    )

    # Previous month for comparison
    if month == 1:
        prev_y, prev_m = year - 1, 12
    else:
        prev_y, prev_m = year, month - 1

    prev_summary = query_one(
        """
        SELECT COALESCE(SUM(total_amount), 0) as revenue
        FROM sales
        WHERE YEAR(sale_date) = %s AND MONTH(sale_date) = %s AND status = 'COMPLETED'
        """,
        (prev_y, prev_m)
    )
    prev_rev = float(prev_summary["revenue"]) if prev_summary else 0.0
    mom_change = round(((revenue - prev_rev) / prev_rev * 100), 1) if prev_rev > 0 else (100.0 if revenue > 0 else 0.0)

    return {
        "year": year,
        "month": month,
        "bills": bills,
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "expenses": expenses,
        "net_profit": net_profit,
        "margin_pct": margin_pct,
        "daily_breakdown": daily_rows,
        "top_products": top_products,
        "expense_categories": exp_categories,
        "prev_revenue": prev_rev,
        "mom_change": mom_change
    }


def get_custom_range_report(start_date, end_date):
    """Report for arbitrary date range."""
    summary = query_one(
        """
        SELECT COUNT(DISTINCT s.sale_id) as bills,
               COALESCE(SUM(s.total_amount), 0) as revenue,
               COALESCE(SUM(si.quantity * si.unit_cost), 0) as cogs
        FROM sales s
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        WHERE DATE(s.sale_date) BETWEEN %s AND %s AND s.status = 'COMPLETED'
        """,
        (start_date, end_date)
    )
    bills = summary["bills"] if summary else 0
    revenue = float(summary["revenue"]) if summary else 0.0
    cogs = float(summary["cogs"]) if summary else 0.0
    gross_profit = round(revenue - cogs, 2)

    exp_sum = query_one(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE expense_date BETWEEN %s AND %s",
        (start_date, end_date)
    )
    expenses = float(exp_sum["total"]) if exp_sum else 0.0
    net_profit = round(gross_profit - expenses, 2)
    margin_pct = round((net_profit / revenue * 100), 1) if revenue > 0 else 0.0

    product_sales = query_all(
        """
        SELECT p.name, p.sku, SUM(si.quantity) as qty,
               SUM(si.line_total) as revenue,
               SUM(si.line_total - (si.quantity * si.unit_cost)) as profit
        FROM sale_items si
        JOIN sales s ON s.sale_id = si.sale_id
        JOIN products p ON p.product_id = si.product_id
        WHERE DATE(s.sale_date) BETWEEN %s AND %s AND s.status = 'COMPLETED'
        GROUP BY p.product_id
        ORDER BY revenue DESC
        """,
        (start_date, end_date)
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "bills": bills,
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "expenses": expenses,
        "net_profit": net_profit,
        "margin_pct": margin_pct,
        "product_sales": product_sales
    }


def get_product_performance_report():
    """All-time or active product performance: units sold, revenue, profit, margin %."""
    rows = query_all(
        """
        SELECT p.product_id, p.sku, p.name, c.name as category_name,
               p.stock_qty, p.cost_price, p.sell_price,
               COALESCE(SUM(si.quantity), 0) as units_sold,
               COALESCE(SUM(si.line_total), 0) as total_revenue,
               COALESCE(SUM(si.line_total - (si.quantity * si.unit_cost)), 0) as total_profit
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        LEFT JOIN sale_items si ON p.product_id = si.product_id
        LEFT JOIN sales s ON si.sale_id = s.sale_id AND s.status = 'COMPLETED'
        WHERE p.is_active = 1
        GROUP BY p.product_id
        ORDER BY total_revenue DESC
        """
    )
    for r in rows:
        rev = float(r["total_revenue"])
        prof = float(r["total_profit"])
        r["margin_pct"] = round((prof / rev * 100), 1) if rev > 0 else 0.0
    return rows
