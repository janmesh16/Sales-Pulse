"""
Database seeding script for SalesPulse.
Populates realistic 90 days of sales data, ~60 products across 8 categories,
monthly operating expenses, stock levels, low-stock alerts, slow-moving items,
and default user accounts (Owner and Staff).
"""

import random
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from db import get_raw_connection
from config import Config

def seed_database(config_class=Config):
    """Seed the database with comprehensive realistic retail data."""
    print("Connecting to database...")
    conn = get_raw_connection(config_class)
    cursor = conn.cursor(dictionary=True)

    try:
        # Clear existing tables (in foreign key order)
        print("Resetting existing tables...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        tables = ["sale_items", "sales", "stock_movements", "expenses", "products", "categories", "users", "settings"]
        for t in tables:
            cursor.execute(f"TRUNCATE TABLE {t};")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        # 1. Seed Settings
        print("Seeding store settings...")
        settings_data = [
            ("shop_name", "SalesPulse Supermart"),
            ("shop_address", "Plot 42, Commercial Complex, Sector 17, Navi Mumbai, MH - 400703"),
            ("gstin", "27AABCS1429B1Z8"),
            ("currency", "₹"),
            ("default_reorder_level", "5")
        ]
        for k, v in settings_data:
            cursor.execute("INSERT INTO settings (setting_key, setting_value) VALUES (%s, %s)", (k, v))

        # 2. Seed Users
        print("Seeding users...")
        owner_hash = generate_password_hash("Owner@123")
        staff_hash = generate_password_hash("Staff@123")

        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, role, is_active, created_at)
            VALUES (%s, %s, %s, 'OWNER', 1, NOW()), (%s, %s, %s, 'STAFF', 1, NOW())
            """,
            ("Anand Verma (Owner)", "owner@salespulse.com", owner_hash,
             "Rohan Sharma (Cashier)", "staff@salespulse.com", staff_hash)
        )
        owner_id = 1
        staff_id = 2

        # 3. Seed 8 Categories
        print("Seeding categories...")
        category_names = [
            "Grocery", "Beverages", "Snacks", "Stationery",
            "Personal Care", "Household", "Electronics Accessories", "Dairy"
        ]
        category_map = {}
        for name in category_names:
            cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
            category_map[name] = cursor.lastrowid

        # 4. Seed ~60 Realistic Products
        print("Seeding ~60 products...")
        product_definitions = [
            # Grocery
            ("GRO-ATT-001", "Aashirvaad Shudh Chakki Atta 5kg", "Grocery", 210.0, 260.0, 45, 10),
            ("GRO-RIC-001", "India Gate Basmati Rice 5kg", "Grocery", 420.0, 540.0, 30, 8),
            ("GRO-DAL-001", "Tata Sampann Toor Dal 1kg", "Grocery", 125.0, 160.0, 40, 10),
            ("GRO-OIL-001", "Fortune Sunlite Refined Oil 1L", "Grocery", 115.0, 145.0, 50, 12),
            ("GRO-SUG-001", "Madhur Pure & Hygienic Sugar 1kg", "Grocery", 42.0, 52.0, 60, 15),
            ("GRO-SLT-001", "Tata Salt Vacuum Evaporated 1kg", "Grocery", 20.0, 28.0, 80, 20),
            ("GRO-MAS-001", "Everest Garam Masala 100g", "Grocery", 68.0, 85.0, 35, 5),
            ("GRO-POH-001", "Rajdhani Thick Poha 500g", "Grocery", 32.0, 45.0, 25, 5),

            # Beverages
            ("BEV-TEA-001", "Tata Tea Gold 250g", "Beverages", 120.0, 155.0, 50, 10),
            ("BEV-COF-001", "Nescafe Classic Coffee Jar 50g", "Beverages", 145.0, 185.0, 40, 8),
            ("BEV-COL-001", "Coca-Cola Bottle 750ml", "Beverages", 32.0, 40.0, 60, 15),
            ("BEV-MNX-001", "Maaza Mango Drink 600ml", "Beverages", 30.0, 38.0, 45, 10),
            ("BEV-RED-001", "Red Bull Energy Drink Can 250ml", "Beverages", 95.0, 125.0, 20, 5),
            ("BEV-JUC-001", "Real Mixed Fruit Juice 1L", "Beverages", 95.0, 130.0, 30, 6),
            ("BEV-WAT-001", "Kinley Packaged Drinking Water 1L", "Beverages", 12.0, 20.0, 100, 25),
            ("BEV-GRN-001", "Tetley Green Tea Lemon & Honey 25 Bags", "Beverages", 140.0, 190.0, 20, 5),

            # Snacks
            ("SNK-LAY-001", "Lay's India's Magic Masala 50g", "Snacks", 15.0, 20.0, 75, 15),
            ("SNK-KUR-001", "Kurkure Masala Munch 85g", "Snacks", 15.0, 20.0, 70, 15),
            ("SNK-PRL-001", "Parle-G Gold Biscuits 1kg", "Snacks", 90.0, 120.0, 50, 10),
            ("SNK-ORI-001", "Cadbury Oreo Vanilla Biscuits 120g", "Snacks", 28.0, 35.0, 45, 8),
            ("SNK-MAG-001", "Maggi 2-Minute Masala Noodles 280g (4-Pack)", "Snacks", 50.0, 64.0, 85, 20),
            ("SNK-HAL-001", "Haldiram's Aloo Bhujia 400g", "Snacks", 88.0, 115.0, 40, 10),
            ("SNK-DRY-001", "Nutraj California Almonds 250g", "Snacks", 210.0, 280.0, 18, 5),
            ("SNK-CHO-001", "Cadbury Dairy Milk Silk 60g", "Snacks", 65.0, 85.0, 50, 10),

            # Stationery
            ("STN-PEN-001", "Reynolds 045 Fine Carbure Ball Pen (Blue)", "Stationery", 6.0, 10.0, 150, 25),
            ("STN-GEL-001", "Classmate Octane Gel Pen Pack of 5", "Stationery", 38.0, 50.0, 40, 8),
            ("STN-NTB-001", "Classmate Long Notebook 172 Pages", "Stationery", 45.0, 65.0, 60, 15),
            ("STN-STP-001", "Kangaro Stapler No. 10 with Pins", "Stationery", 55.0, 75.0, 25, 5),
            ("STN-SHT-001", "JK Copier A4 Paper Rim 500 Sheets", "Stationery", 280.0, 360.0, 20, 5),
            ("STN-COL-001", "Faber-Castell 12 Colour Pencils", "Stationery", 60.0, 80.0, 30, 6),
            ("STN-TPE-001", "Scotch Transparent Tape 1 inch", "Stationery", 22.0, 35.0, 40, 8),
            ("STN-SCS-001", "Munix Household Craft Scissors", "Stationery", 50.0, 70.0, 15, 4),

            # Personal Care
            ("PER-SOAP-001", "Dettol Original Bathing Soap 75g (Pack of 4)", "Personal Care", 130.0, 165.0, 40, 10),
            ("PER-SHMP-001", "Head & Shoulders Anti-Dandruff Shampoo 180ml", "Personal Care", 150.0, 199.0, 30, 6),
            ("PER-PAST-001", "Colgate MaxFresh Peppermint Paste 150g", "Personal Care", 92.0, 120.0, 50, 12),
            ("PER-BRSH-001", "Oral-B Shiny Clean Toothbrush (Medium)", "Personal Care", 22.0, 30.0, 60, 15),
            ("PER-FCE-001", "Himalaya Purifying Neem Face Wash 100ml", "Personal Care", 110.0, 150.0, 25, 5),
            ("PER-DEO-001", "Nivea Men Fresh Active Deodorant 150ml", "Personal Care", 160.0, 225.0, 20, 5),
            ("PER-CREM-001", "Vaseline Intensive Care Body Lotion 200ml", "Personal Care", 165.0, 230.0, 22, 5),
            ("PER-SNT-001", "Lifebuoy Total Hand Sanitizer 100ml", "Personal Care", 35.0, 50.0, 30, 8),

            # Household
            ("HOU-DET-001", "Surf Excel Easy Wash Detergent Powder 1kg", "Household", 115.0, 145.0, 45, 10),
            ("HOU-BAR-001", "Vim Dishwash Bar 300g", "Household", 25.0, 35.0, 70, 15),
            ("HOU-LIQ-001", "Lizol Floor Cleaner Citrus 500ml", "Household", 82.0, 105.0, 35, 8),
            ("HOU-HAR-001", "Harpic Power Plus Toilet Cleaner 500ml", "Household", 75.0, 98.0, 40, 10),
            ("HOU-MOS-001", "All Out Ultra Mosquito Repellent Refill (Pack of 2)", "Household", 125.0, 160.0, 30, 6),
            ("HOU-GAR-001", "Shalimar Premium Garbage Bags 30 Pcs", "Household", 70.0, 95.0, 25, 5),
            ("HOU-AIR-001", "Godrej aer Pocket Bathroom Fragrance 10g", "Household", 48.0, 65.0, 40, 8),
            ("HOU-FOIL-001", "Freshwrapp Aluminium Foil 9 Meters", "Household", 85.0, 115.0, 20, 5),

            # Electronics Accessories
            ("ELE-CAB-001", "boAt Rugged v3 Micro USB Cable 1.5m", "Electronics Accessories", 110.0, 199.0, 25, 5),
            ("ELE-TYPC-001", "boAt Deuce 300 Type-C Fast Cable 1.5m", "Electronics Accessories", 140.0, 249.0, 30, 6),
            ("ELE-CHG-001", "Mi 10W Fast Wall Adapter Charger", "Electronics Accessories", 220.0, 349.0, 15, 4),
            ("ELE-EAR-001", "boAt BassHeads 100 Wired Earphones", "Electronics Accessories", 230.0, 399.0, 20, 5),
            ("ELE-BAT-001", "Duracell Ultra AA Alkaline Batteries (Pack of 4)", "Electronics Accessories", 120.0, 170.0, 40, 8),
            ("ELE-OTG-001", "SanDisk Ultra Dual Drive Go Type-C 64GB", "Electronics Accessories", 520.0, 699.0, 12, 3),
            ("ELE-AUX-001", "Portronics 3.5mm Gold-Plated Aux Cable 1m", "Electronics Accessories", 75.0, 149.0, 20, 4),
            ("ELE-LED-001", "Philips 9W B22 Cool Daylight LED Bulb", "Electronics Accessories", 70.0, 100.0, 50, 12),

            # Dairy
            ("DAI-MIL-001", "Amul Taaza Homogenised Toned Milk 1L", "Dairy", 60.0, 74.0, 40, 10),
            ("DAI-BUT-001", "Amul Pasteurized Butter 100g", "Dairy", 46.0, 58.0, 50, 12),
            ("DAI-CHS-001", "Amul Processed Cheese Slices 200g (10 Slices)", "Dairy", 115.0, 145.0, 30, 8),
            ("DAI-PAN-001", "Mother Dairy Malai Paneer 200g", "Dairy", 72.0, 95.0, 35, 8),
            ("DAI-GHE-001", "Amul Pure Ghee Pouch 1L", "Dairy", 510.0, 630.0, 15, 4),
            ("DAI-CUR-001", "Amul Masti Dahi Pouch 400g", "Dairy", 28.0, 35.0, 45, 10)
        ]

        # Low-stock deliberate demo products: 5 products below reorder level
        low_stock_skus = {"ELE-CHG-001": 2, "GRO-MAS-001": 3, "HOU-AIR-001": 2, "SNK-DRY-001": 3, "PER-CREM-001": 1}
        # Slow-moving deliberate demo products: 4 products with ZERO sales in last 30 days
        slow_moving_skus = {"ELE-AUX-001", "STN-SCS-001", "BEV-GRN-001", "HOU-FOIL-001"}

        products_list = []
        for sku, name, cat_name, cost, sell, stock, reorder in product_definitions:
            cat_id = category_map[cat_name]
            initial_stock = low_stock_skus.get(sku, stock + 400) # Ensure ample stock for 90 days of transactions
            cursor.execute(
                """
                INSERT INTO products (sku, name, category_id, cost_price, sell_price, stock_qty, reorder_level, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, NOW() - INTERVAL 95 DAY)
                """,
                (sku, name, cat_id, cost, sell, initial_stock, reorder)
            )
            prod_id = cursor.lastrowid
            products_list.append({
                "product_id": prod_id,
                "sku": sku,
                "name": name,
                "cost_price": cost,
                "sell_price": sell,
                "stock_qty": initial_stock,
                "reorder_level": reorder
            })

        # Top 10 Popular items that sell frequently
        popular_skus = {"SNK-MAG-001", "DAI-MIL-001", "BEV-TEA-001", "SNK-LAY-001", "GRO-OIL-001",
                        "PER-SOAP-001", "HOU-DET-001", "DAI-BUT-001", "GRO-ATT-001", "STN-PEN-001"}
        popular_products = [p for p in products_list if p["sku"] in popular_skus]
        regular_products = [p for p in products_list if p["sku"] not in popular_skus and p["sku"] not in slow_moving_skus]
        slow_products = [p for p in products_list if p["sku"] in slow_moving_skus]

        # 5. Seed 90 Days of Sales
        print("Generating 90 days of realistic sales (this may take a few seconds)...")
        end_date = date.today()
        start_date = end_date - timedelta(days=89)

        payment_modes = ["CASH", "UPI", "CARD"]
        payment_weights = [0.45, 0.40, 0.15] # 45% Cash, 40% UPI, 15% Card
        customer_names = [
            "Pooja Sharma", "Vikram Malhotra", "Sunil Joshi", "Anita Desai",
            "Rajesh Kulkarni", "Meera Nair", "Deepak Verma", "Suresh Gupta",
            "Neha Patil", "Amitabh Sen", "Kavita Rao", "Manoj Tiwari",
            "Shweta Saxena", "Alok Pandey", "Ritu Singhal", None, None, None # Walk-ins
        ]

        total_sales_count = 0
        total_items_count = 0

        # Pre-track inventory decrements
        sold_qty_map = {p["product_id"]: 0 for p in products_list}

        for day_offset in range(90):
            current_day = start_date + timedelta(days=day_offset)
            is_weekend = current_day.weekday() in (5, 6)
            is_recent_30_days = (end_date - current_day).days < 30

            # Daily bills volume: 18-35 bills/day, slightly more on weekends, upward trend
            base_bills = 22 + int(day_offset * 0.08)
            daily_bills_target = random.randint(base_bills - 4, base_bills + 8)
            if is_weekend:
                daily_bills_target += random.randint(6, 12)

            for bill_seq in range(1, daily_bills_target + 1):
                inv_no = f"SP-{current_day.strftime('%Y%m%d')}-{bill_seq:04d}"
                sale_hour = random.randint(9, 21) # 9 AM to 9 PM
                sale_minute = random.randint(0, 59)
                sale_datetime = datetime(current_day.year, current_day.month, current_day.day, sale_hour, sale_minute)

                cashier_id = staff_id if random.random() < 0.65 else owner_id
                pay_mode = random.choices(payment_modes, weights=payment_weights)[0]
                cust = random.choice(customer_names)
                phone = f"98{random.randint(10000000, 99999999)}" if cust else None

                # Items per bill: 1 to 4 items
                num_items = random.choices([1, 2, 3, 4], weights=[0.40, 0.35, 0.18, 0.07])[0]

                # Pick candidates: popular items appear more often
                chosen_prods = []
                for _ in range(num_items):
                    if random.random() < 0.55:
                        p = random.choice(popular_products)
                    else:
                        if not is_recent_30_days and random.random() < 0.08 and slow_products:
                            p = random.choice(slow_products)
                        else:
                            p = random.choice(regular_products)
                    if p not in chosen_prods:
                        chosen_prods.append(p)

                if not chosen_prods:
                    chosen_prods = [random.choice(popular_products)]

                # Calculate line totals
                lines = []
                subtotal = 0.0
                for prod in chosen_prods:
                    qty = random.choices([1, 2, 3], weights=[0.75, 0.20, 0.05])[0]
                    line_total = round(prod["sell_price"] * qty, 2)
                    subtotal += line_total
                    sold_qty_map[prod["product_id"]] += qty
                    lines.append((prod, qty, line_total))

                subtotal = round(subtotal, 2)
                # Occasional discount (10% of bills get ₹10-₹50 discount)
                discount = 0.0
                if random.random() < 0.12 and subtotal > 150:
                    discount = float(random.choice([10, 20, 30, 50]))
                    discount = min(discount, subtotal * 0.2)
                total_amount = round(subtotal - discount, 2)

                # Insert sale
                cursor.execute(
                    """
                    INSERT INTO sales (invoice_no, sale_date, customer_name, customer_phone,
                                       subtotal, discount, total_amount, payment_mode, status, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'COMPLETED', %s)
                    """,
                    (inv_no, sale_datetime, cust, phone, subtotal, discount, total_amount, pay_mode, cashier_id)
                )
                sale_id = cursor.lastrowid
                total_sales_count += 1

                # Insert sale items
                for prod, qty, l_total in lines:
                    cursor.execute(
                        """
                        INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, unit_cost, line_total)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (sale_id, prod["product_id"], qty, prod["sell_price"], prod["cost_price"], l_total)
                    )
                    total_items_count += 1

        # 6. Reconcile Final Stock and Stock Movements
        print("Reconciling inventory levels and movements...")
        for p in products_list:
            pid = p["product_id"]
            sold = sold_qty_map[pid]
            # Ensure target stock is accurate
            if p["sku"] in low_stock_skus:
                final_stock = low_stock_skus[p["sku"]]
            else:
                final_stock = max(15, p["stock_qty"] - sold)

            cursor.execute("UPDATE products SET stock_qty = %s WHERE product_id = %s", (final_stock, pid))

            # Initial restock movement
            cursor.execute(
                """
                INSERT INTO stock_movements (product_id, change_qty, reason, user_id, created_at)
                VALUES (%s, %s, 'RESTOCK', %s, NOW() - INTERVAL 91 DAY)
                """,
                (pid, final_stock + sold, owner_id)
            )

        # 7. Seed Monthly Overheads (Rent, Electricity, Salaries, Weekly Misc)
        print("Seeding monthly operating expenses...")
        expense_months = set()
        for day_offset in range(90):
            d = start_date + timedelta(days=day_offset)
            expense_months.add((d.year, d.month))

        for (y, m) in sorted(list(expense_months)):
            # Rent: 1st of each month
            cursor.execute(
                """
                INSERT INTO expenses (expense_date, category, amount, payment_mode, note, user_id)
                VALUES (%s, 'Rent', 35000.00, 'BANK', 'Commercial shop rent paid to landlord', %s)
                """,
                (date(y, m, 1), owner_id)
            )
            # Electricity: 10th of each month
            cursor.execute(
                """
                INSERT INTO expenses (expense_date, category, amount, payment_mode, note, user_id)
                VALUES (%s, 'Electricity', 8450.00, 'UPI', 'Monthly electricity & power bill (MSEDCL)', %s)
                """,
                (date(y, m, 10), owner_id)
            )
            # Salaries: End of each month
            cursor.execute(
                """
                INSERT INTO expenses (expense_date, category, amount, payment_mode, note, user_id)
                VALUES (%s, 'Salaries', 28000.00, 'BANK', 'Store assistant & cashier monthly salaries', %s)
                """,
                (date(y, m, min(28, 28)), owner_id)
            )
            # Packaging & Transport
            cursor.execute(
                """
                INSERT INTO expenses (expense_date, category, amount, payment_mode, note, user_id)
                VALUES (%s, 'Packaging', 2400.00, 'CASH', 'Carry bags, thermal paper rolls, packaging boxes', %s)
                """,
                (date(y, m, 15), owner_id)
            )
            cursor.execute(
                """
                INSERT INTO expenses (expense_date, category, amount, payment_mode, note, user_id)
                VALUES (%s, 'Transport', 3200.00, 'UPI', 'Goods tempo freight from wholesale mandi', %s)
                """,
                (date(y, m, 20), owner_id)
            )

        conn.commit()
        print(f"✅ Seeding complete! Generated {total_sales_count} sales ({total_items_count} line items) over 90 days.")
        print("Default users: owner@salespulse.com / Owner@123, staff@salespulse.com / Staff@123")

    except Exception as e:
        conn.rollback()
        print(f"❌ Seeding failed: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_database()
