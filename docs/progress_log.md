# SalesPulse — Engineering & Development Progress Log

This progress log documents the day-by-day development lifecycle, engineering milestones, and verification tasks for the **SalesPulse — Small Business Sales Analytics System**.

---

### Sprint Planning & Day 1: System Inception & Requirements Engineering
- **Date**: 2026-10-13
- **Tasks Completed**:
  - Analyzed problem statement for small kirana, bakery, and retail businesses.
  - Formulated the core financial identity: `Net Profit = Gross Revenue - Cost of Goods Sold (COGS) - Operating Overheads`.
  - Defined system scope, assumptions, user classes (Store Owner vs. Staff Cashier), and non-functional requirements.
  - Authored Software Requirements Specification (SRS) mapping 44 detailed functional test requirements.

---

### Day 2: Database Schema & Architectural Modeling
- **Date**: 2026-10-14
- **Tasks Completed**:
  - Created 3NF normalized schema in `schema.sql` covering `users`, `categories`, `products`, `sales`, `sale_items`, `expenses`, `stock_movements`, and `settings`.
  - Designed intentional historical denormalization for `sale_items.unit_cost` and `sale_items.unit_price` to safeguard past accounting periods against future catalog price edits.
  - Modeled three-tier architecture (Jinja2 + Bootstrap frontend, Flask application layer, MySQL pooled storage).
  - Designed system diagrams: Use Case, DFD Level 0 & Level 1, Class diagram, Activity flows, Sequence diagrams, and ER diagram.

---

### Day 3: Backend Scaffolding & Connection Pooling
- **Date**: 2026-10-15
- **Tasks Completed**:
  - Developed `config.py` with environment variable loading and session security parameters.
  - Created `db.py` featuring MySQL connection pooling via `mysql-connector-python`, parameterized query helpers, and automatic request teardown connection recycling.
  - Built custom decorators `@login_required` and `@owner_required` in `utils/decorators.py`.
  - Built input sanitizers and Indian Numbering System currency formatter `format_inr` (₹).

---

### Day 4: Core Authentication & Product Catalog Management
- **Date**: 2026-10-16
- **Tasks Completed**:
  - Implemented `blueprints/auth.py` with PBKDF2/scrypt password verification and rate-limiting after 5 consecutive failed attempts.
  - Built `blueprints/products.py` for Owner CRUD operations and soft-deactivation.
  - Restricted Staff accounts from viewing product cost prices in both HTML templates and JSON search endpoints.
  - Implemented bulk CSV product import engine with row-by-row diagnostics in `services/csv_import.py`.

---

### Day 5: POS Billing Engine & ACID Transactional Sales
- **Date**: 2026-10-17
- **Tasks Completed**:
  - Implemented `services/sales_service.py` with strict database transactions (`START TRANSACTION`, `SELECT ... FOR UPDATE` row locking, and rollback on stock deficit).
  - Built daily invoice sequencing logic: `SP-YYYYMMDD-0001`.
  - Built interactive POS billing terminal in `templates/sales/billing.html` with vanilla JavaScript autocomplete in `static/js/billing.js`.
  - Added sale cancellation routine restoring inventory units and creating `CANCEL_RETURN` stock movement records.

---

### Day 6: Inventory Health & Expense Tracking
- **Date**: 2026-10-18
- **Tasks Completed**:
  - Built `services/stock_service.py` for manual stock adjustments (Restock, Damage, Correction) and movement auditing.
  - Implemented low-stock detection (`stock_qty <= reorder_level`) and slow-moving product detection (0 sales in 30 days).
  - Developed `blueprints/expenses.py` for logging operating overheads across 8 categories (Rent, Electricity, Salaries, Transport, etc.).

---

### Day 7: Analytics Engine, Chart.js & Forecasting
- **Date**: 2026-10-19
- **Tasks Completed**:
  - Engineered `services/analytics_service.py` to compute real-time KPIs, excluding cancelled sales from all metrics.
  - Designed 6 interactive Chart.js visualizations in `static/js/charts.js` (Sales Trend, Top 5 Products, Expense Breakdown, Category Distribution, 6-Month Comparison, and 7-Day Forecast).
  - Built autoregressive moving-average forecasting engine in `services/forecast.py` incorporating weekday seasonality factors.

---

### Day 8: Reporting, PDF/CSV Exports & Data Seeding
- **Date**: 2026-10-20
- **Tasks Completed**:
  - Built Daily, Monthly, Custom Range, and Product Performance reports in `blueprints/reports.py`.
  - Implemented dynamic RFC-4180 CSV streaming and vector PDF generation using ReportLab in `services/export_service.py`.
  - Created `seed.py` generating 90 days of realistic sales, users, settings, and ~60 products.

---

### Day 9: Comprehensive Testing & UI Verification
- **Date**: 2026-10-21
- **Tasks Completed**:
  - Wrote pytest test suite across `tests/test_unit_calc.py`, `tests/test_sales_flow.py`, `tests/test_security.py`, `tests/test_reports.py`, and `tests/test_additional_cases.py`.
  - Verified 35 automated test cases passing with zero failures.
  - Executed Playwright browser automation script `tests/capture_screenshots.py` capturing 23 high-resolution desktop and mobile application screens.
  - Rendered all 12 system architecture diagrams into PNGs in `docs/diagrams/`.
