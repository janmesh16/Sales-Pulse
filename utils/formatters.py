"""
Formatting utilities for SalesPulse.
Provides Indian currency formatting (₹), date formatters, and percentage helpers.
"""

from datetime import datetime, date


def format_inr(amount):
    """
    Format numerical amounts according to Indian Numbering System with Rupee symbol:
    e.g. 12450.00 -> ₹ 12,450.00
         1234567.50 -> ₹ 12,34,567.50
    """
    if amount is None:
        return "₹ 0.00"
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return str(amount)

    is_negative = val < 0
    val = abs(val)

    # Format to 2 decimal places
    parts = f"{val:.2f}".split(".")
    int_part = parts[0]
    dec_part = parts[1]

    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        # Group remaining digits in pairs of two from right to left
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ",".join(groups) + "," + last_three

    result = f"₹ {formatted_int}.{dec_part}"
    return f"-{result}" if is_negative else result


def format_date(dt, format_str="%d %b %Y"):
    """Format date or datetime object into readable string."""
    if not dt:
        return "-"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", ""))
        except Exception:
            return dt
    return dt.strftime(format_str)


def format_datetime(dt, format_str="%d %b %Y, %I:%M %p"):
    """Format datetime object into readable string with time."""
    if not dt:
        return "-"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", ""))
        except Exception:
            return dt
    return dt.strftime(format_str)


def format_percent(val):
    """Format a number into a percentage with 1 decimal place."""
    if val is None:
        return "0.0%"
    try:
        return f"{float(val):.1f}%"
    except (ValueError, TypeError):
        return "0.0%"
