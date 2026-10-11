# SalesPulse — Viva Examination Preparation Guide & Demo Script

This document prepares the student for viva-voce questions, architectural defenses, conceptual queries, and includes an exact 5-minute live demo walkthrough.

---

## 1. Core Technical & Architectural Questions

### Q1: Why did you choose Flask over Django or Fast-API?
**Answer:**
- Flask is a lightweight WSGI microframework that gives full control over the application architecture without imposing an ORM or rigid defaults.
- For small business analytics, using Flask with **Blueprints** provides a clean, modular structure (`auth`, `products`, `sales`, `expenses`, `reports`, `dashboard`) while keeping performance snappy.
- It allows direct, optimized SQL execution with connection pooling rather than relying on heavy ORM overhead.

### Q2: Why MySQL instead of a NoSQL database like MongoDB?
**Answer:**
- Sales transactions and inventory accounting require **ACID guarantees** (Atomicity, Consistency, Isolation, Durability).
- If a customer buys 2 items, inventory deduction and sale recording must happen atomically. A crash midway must never leave stock decremented without a corresponding invoice.
- Relational joins, aggregate queries (`GROUP BY`, `SUM`, `HAVING`), and foreign-key constraints provide rock-solid consistency that document stores cannot guarantee without complex distributed multi-document transaction overhead.

### Q3: What is a Database Transaction and why is it essential in POS billing?
**Answer:**
- A transaction bundles multiple SQL operations into an all-or-nothing unit of work.
- In `create_sale()`:
  1. Product rows are locked with `SELECT ... FOR UPDATE` to prevent race conditions.
  2. The `sales` header is inserted.
  3. `sale_items` rows are inserted with unit price and unit cost snapshots.
  4. Product stock is decremented in `products`.
  5. Audit records are inserted into `stock_movements`.
- If any check fails (e.g. insufficient stock or network failure), `conn.rollback()` restores the database state. Only if every step succeeds is `conn.commit()` executed.

### Q4: Why do you store `unit_cost` in `sale_items` when it already exists in the `products` table?
**Answer:**
- This is an intentional and essential **historical snapshot (controlled denormalization)**.
- If we bought a product at ₹100 in January and made a sale, our COGS was ₹100. If inflation causes supplier prices to rise to ₹120 in March, updating `products.cost_price` to ₹120 must **never** alter the historical profit recorded in January.
- Snapshotting `unit_cost` and `unit_price` at the moment of checkout guarantees that audited accounting reports remain 100% immutable and accurate over time.

### Q5: How is Profit calculated across SalesPulse?
**Answer:**
- **Gross Revenue**: `Σ(sales.total_amount)` for `COMPLETED` sales.
- **Cost of Goods Sold (COGS)**: `Σ(sale_items.quantity × sale_items.unit_cost)`.
- **Gross Profit**: `Gross Revenue - COGS`.
- **Net Profit**: `Gross Profit - Σ(expenses in the same period)`.
- **Profit Margin %**: `(Net Profit / Gross Revenue) × 100`.
- All queries strictly enforce `WHERE status = 'COMPLETED'` so cancelled sales are excluded.

### Q6: How does the 7-day Sales Forecast algorithm work and what are its limitations?
**Answer:**
- **Algorithm**: An autoregressive 7-day **Simple Moving Average (SMA)** rolling window applied across the preceding 28 days of daily revenue.
- **Seasonality**: It computes weekday multipliers (e.g., Saturday/Sunday sales vs. weekday average) to apply retail footfall patterns to future projections.
- **Limitations**: As an SMA-based moving average, it is designed for baseline trend estimation. It does not predict sudden macroeconomic shifts, sudden competitor promotions, or unseasonal disruptions. In the UI, it is clearly designated as an *Estimate*.

### Q7: Explain Database Normalization in SalesPulse. Is it in 3NF?
**Answer:**
- Yes, the database is structured in **Third Normal Form (3NF)**:
  - **1NF**: All column values are atomic; primary keys exist on every table.
  - **2NF**: No partial dependencies; all non-key attributes depend on the entire primary key.
  - **3NF**: No transitive dependencies; attributes in `products` depend solely on `product_id`, `categories` on `category_id`, and `users` on `user_id`.
  - The historical cost snapshot in `sale_items` represents point-in-time temporal facts, adhering to dimensional and accounting modeling standards.

### Q8: How is SQL Injection prevented?
**Answer:**
- We strictly utilize **parameterized queries** (`cursor.execute(sql, (param1, param2))`) through `mysql-connector-python`.
- User input is sent separately from the SQL statement structure to the MySQL query parser. The database driver escapes and typesets parameters, making query manipulation impossible even if quotes or `' OR '1'='1` are entered. String formatting (`%s % var` or `f-strings`) is never used in SQL queries.

### Q9: How is Cross-Site Request Forgery (CSRF) mitigated?
**Answer:**
- We enforce `Flask-WTF` CSRF protection.
- Every HTML form embeds a unique encrypted `csrf_token()`.
- Client-side AJAX/fetch requests read the `<meta name="csrf-token">` tag and send an `X-CSRFToken` request header.
- Requests without a valid matching token are rejected with HTTP 400 Bad Request before hitting the view logic.

### Q10: How does Role-Based Access Control (RBAC) function?
**Answer:**
- Decorator `@login_required` checks if `session['user_id']` exists.
- Decorator `@owner_required` checks if `session['role'] == 'OWNER'`.
- Staff cashiers attempting to open owner routes (such as `/reports`, `/expenses`, `/stock`) receive HTTP 403 Forbidden.
- On the frontend and in API responses (`/products/api/search`), cost prices and margin numbers are never rendered or transmitted to Staff users.

---

## 2. Five-Minute Live Demo Script for the Examiner

1. **Step 1: Application Architecture & Login (0:00 - 1:00)**
   - Open browser at `http://127.0.0.1:5000/login`.
   - Explain the 2 distinct roles: Store Owner and Staff Cashier.
   - Log in as Staff (`staff@salespulse.com / Staff@123`).
   - Show that Staff lands on the Cashier Home screen, displaying today's shift count and sales.

2. **Step 2: Fast POS Billing Flow (1:00 - 2:15)**
   - Click **"Start New Sale"**.
   - Type in the search box (e.g., `"Tata"` or `"Lay's"`) to show instant live autocomplete.
   - Click to add products to the cart ticket.
   - Demonstrate the quantity stepper (`+` and `-`) and live total calculation.
   - Enter a discount (e.g. ₹20 flat or 10%).
   - Select Payment Mode (e.g. `UPI`).
   - Click **"Complete & Print Receipt"**.
   - Show the generated tax invoice (`/sales/<id>/receipt`) formatted with shop details and invoice number `SP-YYYYMMDD-XXXX`.

3. **Step 3: Inventory Integrity & Stock Drop (2:15 - 3:00)**
   - Log out of Staff and log in as Store Owner (`owner@salespulse.com / Owner@123`).
   - Navigate to **"Inventory & Stock"**.
   - Show that the items sold in the previous step had their stock count automatically decremented.
   - Click **"Stock Alerts"** to demonstrate:
     - Low-Stock alerts (products below reorder threshold).
     - Slow-Moving products (items with zero sales in the last 30 days).

4. **Step 4: Store Analytics Dashboard & 6 Charts (3:00 - 4:15)**
   - Navigate to **"Dashboard"**.
   - Highlight the 6 real-time KPI cards: Today's Sales, Monthly Revenue, Net Profit, Overhead Expenses, Low-Stock Count, and Month-over-Month (MoM) change.
   - Walk through the 6 interactive Chart.js graphs:
     1. 30-Day Sales & Profit Trend (Line chart)
     2. Top 5 Products by volume and revenue (Horizontal bar with metric toggle)
     3. Expense breakdown (Doughnut chart)
     4. Category sales distribution (Pie chart)
     5. 6-Month Revenue vs. Expenses comparison (Grouped bar chart)
     6. 7-Day moving average sales forecast (Dotted projection line)

5. **Step 5: Financial Reporting & Vector PDF Export (4:15 - 5:00)**
   - Navigate to **"Reports & Export"**.
   - Show the Daily Report breakdown and Monthly Report table.
   - Click **"Export PDF"** to trigger ReportLab on-the-fly PDF generation. Open the downloaded PDF in the browser to show clean tabular vector formatting.
   - Conclude by stating that SalesPulse provides small business owners enterprise-level visibility at zero license cost.
