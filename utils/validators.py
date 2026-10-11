"""
Input validation utilities for SalesPulse.
Ensures sanitization, type correctness, and positive constraints.
"""

import re


def is_valid_email(email):
    """Validate email address format."""
    if not email or len(email) > 120:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def validate_product_data(sku, name, cost_price, sell_price, stock_qty, reorder_level=5):
    """
    Validate product creation and update inputs.
    Returns (is_valid, error_message, warning_message).
    """
    if not sku or not sku.strip():
        return False, "SKU is required and cannot be empty.", None
    if not name or not name.strip():
        return False, "Product name is required.", None

    try:
        cost = float(cost_price)
        sell = float(sell_price)
        stock = int(stock_qty)
        reorder = int(reorder_level)
    except (ValueError, TypeError):
        return False, "Cost price, sell price, stock quantity, and reorder level must be valid numbers.", None

    if cost < 0:
        return False, "Cost price cannot be negative.", None
    if sell < 0:
        return False, "Selling price cannot be negative.", None
    if stock < 0:
        return False, "Stock quantity cannot be negative.", None
    if reorder < 0:
        return False, "Reorder level cannot be negative.", None

    warning = None
    if sell < cost:
        warning = f"Warning: Selling price (₹{sell:.2f}) is lower than Cost price (₹{cost:.2f}). This product will sell at a loss."

    return True, None, warning


def validate_expense_data(date_str, category, amount):
    """Validate expense data fields."""
    if not date_str:
        return False, "Expense date is required."
    valid_categories = [
        'Rent', 'Electricity', 'Salaries', 'Transport',
        'Maintenance', 'Marketing', 'Packaging', 'Other'
    ]
    if category not in valid_categories:
        return False, f"Invalid category. Must be one of {', '.join(valid_categories)}."
    try:
        amt = float(amount)
        if amt <= 0:
            return False, "Expense amount must be greater than zero."
    except (ValueError, TypeError):
        return False, "Amount must be a valid number."
    return True, None
