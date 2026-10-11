"""
Sales forecasting service for SalesPulse.
Predicts next 7 days of sales using a 7-day rolling simple moving average
with weekday seasonality weighting.
"""

from datetime import date, timedelta
from db import query_all


def get_sales_forecast(lookback_days=28, forecast_days=7):
    """
    Generate a 7-day revenue forecast based on the previous 28 days of completed sales.
    Calculates weekday seasonality factors and performs rolling autoregressive moving average.
    Returns:
    {
        "historical_labels": [...],
        "historical_data": [...],
        "forecast_labels": [...],
        "forecast_data": [...],
        "avg_daily_revenue": float
    }
    """
    start_date = date.today() - timedelta(days=lookback_days)
    end_date = date.today() - timedelta(days=1)

    rows = query_all(
        """
        SELECT DATE(sale_date) as d, COALESCE(SUM(total_amount), 0) as revenue
        FROM sales
        WHERE status = 'COMPLETED'
          AND DATE(sale_date) BETWEEN %s AND %s
        GROUP BY DATE(sale_date)
        ORDER BY d ASC
        """,
        (start_date, end_date)
    )

    revenue_map = {
        (r["d"].strftime("%Y-%m-%d") if hasattr(r["d"], "strftime") else str(r["d"])): float(r["revenue"])
        for r in rows
    }

    # Build full sequence of 28 days
    historical_dates = []
    historical_values = []
    weekday_totals = {i: [] for i in range(7)}  # 0=Monday, 6=Sunday

    for i in range(lookback_days):
        day_date = start_date + timedelta(days=i)
        day_str = day_date.strftime("%Y-%m-%d")
        rev = revenue_map.get(day_str, 0.0)

        historical_dates.append(day_date.strftime("%d %b"))
        historical_values.append(rev)
        weekday_totals[day_date.weekday()].append(rev)

    # Seasonality factor per weekday
    overall_avg = sum(historical_values) / len(historical_values) if historical_values else 0.0
    seasonality = {}
    for wd in range(7):
        wd_vals = weekday_totals[wd]
        wd_avg = sum(wd_vals) / len(wd_vals) if wd_vals else overall_avg
        seasonality[wd] = (wd_avg / overall_avg) if overall_avg > 0 else 1.0

    # Rolling 7-day moving average
    rolling_window = list(historical_values[-7:]) if len(historical_values) >= 7 else list(historical_values)
    if not rolling_window:
        rolling_window = [0.0] * 7

    forecast_labels = []
    forecast_values = []
    current_day = date.today()

    for i in range(forecast_days):
        target_date = current_day + timedelta(days=i)
        forecast_labels.append(target_date.strftime("%d %b (%a)"))

        base_sma = sum(rolling_window[-7:]) / 7.0
        weekday_factor = seasonality.get(target_date.weekday(), 1.0)
        # Apply seasonality with dampening to avoid over-amplification
        predicted_rev = round(max(0.0, base_sma * (0.5 + 0.5 * weekday_factor)), 2)

        forecast_values.append(predicted_rev)
        rolling_window.append(predicted_rev)

    return {
        "historical_labels": historical_dates,
        "historical_data": [round(v, 2) for v in historical_values],
        "forecast_labels": forecast_labels,
        "forecast_data": forecast_values,
        "avg_daily_revenue": round(overall_avg, 2)
    }
