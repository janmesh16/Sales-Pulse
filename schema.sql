-- SalesPulse Database Schema
-- Small Business Sales Analytics System

CREATE DATABASE IF NOT EXISTS salespulse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE salespulse;

CREATE TABLE IF NOT EXISTS users (
  user_id       INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(100) NOT NULL,
  email         VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('OWNER','STAFF') NOT NULL DEFAULT 'STAFF',
  is_active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
  product_id    INT AUTO_INCREMENT PRIMARY KEY,
  sku           VARCHAR(40) NOT NULL UNIQUE,
  name          VARCHAR(150) NOT NULL,
  category_id   INT NOT NULL,
  cost_price    DECIMAL(10,2) NOT NULL CHECK (cost_price >= 0),
  sell_price    DECIMAL(10,2) NOT NULL CHECK (sell_price >= 0),
  stock_qty     INT NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
  reorder_level INT NOT NULL DEFAULT 5,
  is_active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (category_id) REFERENCES categories(category_id),
  INDEX idx_prod_cat (category_id),
  INDEX idx_prod_name (name)
);

CREATE TABLE IF NOT EXISTS sales (
  sale_id        INT AUTO_INCREMENT PRIMARY KEY,
  invoice_no     VARCHAR(20) NOT NULL UNIQUE,
  sale_date      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  customer_name  VARCHAR(100) NULL,
  customer_phone VARCHAR(15) NULL,
  subtotal       DECIMAL(12,2) NOT NULL,
  discount       DECIMAL(12,2) NOT NULL DEFAULT 0,
  total_amount   DECIMAL(12,2) NOT NULL,
  payment_mode   ENUM('CASH','UPI','CARD') NOT NULL DEFAULT 'CASH',
  status         ENUM('COMPLETED','CANCELLED') NOT NULL DEFAULT 'COMPLETED',
  user_id        INT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  INDEX idx_sale_date (sale_date),
  INDEX idx_sale_status (status)
);

CREATE TABLE IF NOT EXISTS sale_items (
  item_id    INT AUTO_INCREMENT PRIMARY KEY,
  sale_id    INT NOT NULL,
  product_id INT NOT NULL,
  quantity   INT NOT NULL CHECK (quantity > 0),
  unit_price DECIMAL(10,2) NOT NULL,   -- selling price at time of sale
  unit_cost  DECIMAL(10,2) NOT NULL,   -- cost price at time of sale (snapshot)
  line_total DECIMAL(12,2) NOT NULL,
  FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(product_id),
  INDEX idx_si_sale (sale_id),
  INDEX idx_si_prod (product_id)
);

CREATE TABLE IF NOT EXISTS expenses (
  expense_id   INT AUTO_INCREMENT PRIMARY KEY,
  expense_date DATE NOT NULL,
  category     ENUM('Rent','Electricity','Salaries','Transport','Maintenance','Marketing','Packaging','Other') NOT NULL,
  amount       DECIMAL(12,2) NOT NULL CHECK (amount > 0),
  payment_mode ENUM('CASH','UPI','CARD','BANK') NOT NULL DEFAULT 'CASH',
  note         VARCHAR(255) NULL,
  user_id      INT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  INDEX idx_exp_date (expense_date)
);

CREATE TABLE IF NOT EXISTS stock_movements (
  movement_id   INT AUTO_INCREMENT PRIMARY KEY,
  product_id    INT NOT NULL,
  change_qty    INT NOT NULL,                       -- + restock, - sale/damage
  reason        ENUM('SALE','RESTOCK','DAMAGE','CORRECTION','CANCEL_RETURN') NOT NULL,
  ref_sale_id   INT NULL,
  user_id       INT NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(product_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  INDEX idx_sm_prod (product_id)
);

CREATE TABLE IF NOT EXISTS settings (
  setting_key   VARCHAR(50) PRIMARY KEY,
  setting_value VARCHAR(255) NOT NULL
);
