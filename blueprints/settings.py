"""
Settings and Profile Blueprint for SalesPulse.
Allows updating store profile (name, address, GSTIN, currency),
and changing user account passwords.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from utils.decorators import login_required, owner_required
from db import query_all, query_one, execute_db

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("", methods=["GET", "POST"])
@login_required
def settings_page():
    """Manage shop configurations and change current user's password."""
    user_id = session.get("user_id")
    user_role = session.get("role")

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_profile" and user_role == "OWNER":
            shop_name = request.form.get("shop_name", "").strip()
            shop_address = request.form.get("shop_address", "").strip()
            gstin = request.form.get("gstin", "").strip()
            currency = request.form.get("currency", "₹").strip()
            default_reorder = request.form.get("default_reorder_level", "5").strip()

            settings_to_update = {
                "shop_name": shop_name,
                "shop_address": shop_address,
                "gstin": gstin,
                "currency": currency,
                "default_reorder_level": default_reorder
            }

            for k, v in settings_to_update.items():
                execute_db(
                    """
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
                    """,
                    (k, v)
                )

            flash("Shop details updated successfully!", "success")
            return redirect(url_for("settings.settings_page"))

        elif action == "change_password":
            cur_pwd = request.form.get("current_password", "")
            new_pwd = request.form.get("new_password", "")
            confirm_pwd = request.form.get("confirm_password", "")

            user = query_one("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
            if not user or not check_password_hash(user["password_hash"], cur_pwd):
                flash("Current password is incorrect.", "danger")
                return redirect(url_for("settings.settings_page"))

            if len(new_pwd) < 6:
                flash("New password must be at least 6 characters.", "danger")
                return redirect(url_for("settings.settings_page"))

            if new_pwd != confirm_pwd:
                flash("New passwords do not match.", "danger")
                return redirect(url_for("settings.settings_page"))

            execute_db(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (generate_password_hash(new_pwd), user_id)
            )
            flash("Your password has been changed successfully!", "success")
            return redirect(url_for("settings.settings_page"))

    # Fetch store settings
    settings_rows = query_all("SELECT setting_key, setting_value FROM settings")
    settings_map = {r["setting_key"]: r["setting_value"] for r in settings_rows}

    return render_template("settings.html", settings=settings_map)
