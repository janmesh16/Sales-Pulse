"""
Automated Playwright browser script for SalesPulse.
Runs an end-to-end user journey, tests UI workflows, and captures real screenshots
for Chapter 5 of the project report and documentation.
"""

import os
import time
import subprocess
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

BASE_URL = "http://127.0.0.1:5001"


def run_e2e_and_capture():
    print(f"Launching Flask test server at {BASE_URL}...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    server_process = subprocess.Popen(
        ["./venv/bin/python", "-c", "from app import create_app; app = create_app(); app.run(port=5001, debug=False)"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2) # Give server time to bind

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # -------------------------------------------------------------
            # Desktop Context (1366 x 768)
            # -------------------------------------------------------------
            desktop_context = browser.new_context(viewport={"width": 1366, "height": 768})
            page = desktop_context.new_page()

            # 1. Login Page
            print("Capturing 01_login.png...")
            page.goto(f"{BASE_URL}/login")
            page.wait_for_selector("#email")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_login.png"))

            # 2. Login as Staff
            print("Logging in as Staff...")
            page.fill("#email", "staff@salespulse.com")
            page.fill("#password", "Staff@123")
            page.click("button[type='submit']")
            page.wait_for_url(f"{BASE_URL}/home")

            print("Capturing 02_staff_home.png...")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_staff_home.png"))

            # 3. Staff Products View (No Cost Price)
            print("Capturing 03_staff_products.png...")
            page.goto(f"{BASE_URL}/products")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_staff_products.png"))

            # 4. New Sale (POS) Empty Cart
            print("Capturing 04_pos_empty.png...")
            page.goto(f"{BASE_URL}/sales/new")
            page.wait_for_selector("#productSearchInput")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_pos_empty.png"))

            # 5. New Sale (POS) Filled Cart
            print("Adding items to POS cart...")
            # Click 2 quick select buttons
            quick_btns = page.query_selector_all(".quick-add-btn")
            if quick_btns:
                quick_btns[0].click()
                if len(quick_btns) > 1:
                    quick_btns[1].click()
            time.sleep(0.5)

            # Enter customer name
            page.fill("#customerName", "Pooja Verma")
            page.fill("#customerPhone", "9820123456")
            print("Capturing 05_pos_filled.png...")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_pos_filled.png"))

            # 6. Complete Sale and View Receipt
            print("Submitting checkout...")
            page.click("#checkoutBtn")
            page.wait_for_url(lambda url: "/sales/" in url and "/receipt" in url)

            print("Capturing 06_receipt.png...")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_receipt.png"))

            # 7. Staff My Sales Today
            print("Capturing 07_staff_sales.png...")
            page.goto(f"{BASE_URL}/sales")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_staff_sales.png"))

            # Logout Staff
            page.goto(f"{BASE_URL}/logout")

            # -------------------------------------------------------------
            # Login as Owner
            # -------------------------------------------------------------
            print("Logging in as Owner...")
            page.goto(f"{BASE_URL}/login")
            page.fill("#email", "owner@salespulse.com")
            page.fill("#password", "Owner@123")
            page.click("button[type='submit']")
            page.wait_for_url(f"{BASE_URL}/dashboard")
            time.sleep(1.5) # Wait for Chart.js animations to stabilize

            # 8. Owner Dashboard
            print("Capturing 08_owner_dashboard.png...")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "08_owner_dashboard.png"))

            # 9. Owner Products Catalog
            print("Capturing 09_owner_products.png...")
            page.goto(f"{BASE_URL}/products")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "09_owner_products.png"))

            # 10. Add Product Form
            print("Capturing 10_product_form.png...")
            page.goto(f"{BASE_URL}/products/new")
            page.wait_for_selector("#sku")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "10_product_form.png"))

            # 11. CSV Bulk Import
            print("Capturing 11_csv_import.png...")
            page.goto(f"{BASE_URL}/products/import")
            page.wait_for_selector("#csv_file")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "11_csv_import.png"))

            # 12. Stock Overview
            print("Capturing 12_stock_overview.png...")
            page.goto(f"{BASE_URL}/stock")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "12_stock_overview.png"))

            # 13. Low Stock & Slow-Moving Alerts
            print("Capturing 13_stock_alerts.png...")
            page.goto(f"{BASE_URL}/stock/alerts")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "13_stock_alerts.png"))

            # 14. Expenses Management
            print("Capturing 14_expenses_list.png...")
            page.goto(f"{BASE_URL}/expenses")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "14_expenses_list.png"))

            # 15. Daily Report
            print("Capturing 15_daily_report.png...")
            page.goto(f"{BASE_URL}/reports/daily")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "15_daily_report.png"))

            # 16. Monthly Report
            print("Capturing 16_monthly_report.png...")
            page.goto(f"{BASE_URL}/reports/monthly")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "16_monthly_report.png"))

            # 17. Custom Range Report
            print("Capturing 17_custom_report.png...")
            today = time.strftime("%Y-%m-%d")
            page.goto(f"{BASE_URL}/reports/custom?start_date=2026-08-01&end_date={today}")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "17_custom_report.png"))

            # 18. Product Performance Report
            print("Capturing 18_product_performance.png...")
            page.goto(f"{BASE_URL}/reports/products")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "18_product_performance.png"))

            # 19. Staff User Management
            print("Capturing 19_user_management.png...")
            page.goto(f"{BASE_URL}/users")
            page.wait_for_selector("table")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "19_user_management.png"))

            # 20. Settings & Store Profile
            print("Capturing 20_settings.png...")
            page.goto(f"{BASE_URL}/settings")
            page.wait_for_selector("#shop_name")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "20_settings.png"))

            desktop_context.close()

            # -------------------------------------------------------------
            # Mobile Viewport Context (375 x 812 - iPhone X / 13)
            # -------------------------------------------------------------
            print("Capturing Mobile Responsive Views (375x812)...")
            mobile_context = browser.new_context(viewport={"width": 375, "height": 812})
            m_page = mobile_context.new_page()

            # Mobile Login & Dashboard
            m_page.goto(f"{BASE_URL}/login")
            m_page.fill("#email", "owner@salespulse.com")
            m_page.fill("#password", "Owner@123")
            m_page.click("button[type='submit']")
            m_page.wait_for_url(f"{BASE_URL}/dashboard")
            time.sleep(1)
            print("Capturing mobile_dashboard.png...")
            m_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "mobile_dashboard.png"))

            # Mobile POS Billing
            print("Capturing mobile_pos.png...")
            m_page.goto(f"{BASE_URL}/sales/new")
            m_page.wait_for_selector("#productSearchInput")
            m_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "mobile_pos.png"))

            # Mobile Offcanvas Navigation
            print("Capturing mobile_nav.png...")
            hamburger = m_page.query_selector("button[data-bs-target='#sidebarOffcanvas']")
            if hamburger:
                hamburger.click()
                time.sleep(0.5)
            m_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "mobile_nav.png"))

            mobile_context.close()
            browser.close()

        print("🎉 All 23 screenshots captured successfully into docs/screenshots/!")

    finally:
        server_process.terminate()
        server_process.wait()


if __name__ == "__main__":
    run_e2e_and_capture()
