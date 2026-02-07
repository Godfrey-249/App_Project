import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = 'pharma.db'

def init_db():
    """Initialize the database with necessary tables."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Products/Inventory Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            quantity INTEGER DEFAULT 0,
            price REAL,
            min_stock_level INTEGER DEFAULT 10
        )
    ''')
    
    # Sales Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER,
            total_price REAL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            attendee_name TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Deliveries Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER,
            delivery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            attendee_name TEXT,
            status TEXT DEFAULT 'Received',
            cost_price REAL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    # Seed some initial data if empty
    c.execute('SELECT count(*) FROM products')
    if c.fetchone()[0] == 0:
        products = [
            ('Paracetamol', 'Panadol', 100, 5.0, 20),
            ('Ibuprofen', 'Advil', 50, 8.5, 15),
            ('Amoxicillin', 'Generic', 30, 12.0, 10),
            ('Vitamin C', 'Redoxon', 80, 15.0, 20),
            ('Cough Syrup', 'Benylin', 25, 18.0, 5)
        ]
        c.executemany('INSERT INTO products (name, brand, quantity, price, min_stock_level) VALUES (?, ?, ?, ?, ?)', products)
        conn.commit()

    # Migration for existing schema: Check if 'status' column exists in deliveries
    try:
        c.execute('SELECT status FROM deliveries LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE deliveries ADD COLUMN status TEXT DEFAULT "Received"')
        conn.commit()

    # Migration for cost_price
    try:
        c.execute('SELECT cost_price FROM deliveries LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE deliveries ADD COLUMN cost_price REAL DEFAULT 0')
        conn.commit()

    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_NAME)

def get_inventory():
    """Fetch all inventory items."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

def add_product_stock(product_id, quantity, attendee_name, cost_price=0):
    """Add stock to existing product and record delivery (Direct Receive)."""
    conn = get_connection()
    c = conn.cursor()
    
    # Update product quantity
    c.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (quantity, product_id))
    
    # Record delivery
    c.execute("INSERT INTO deliveries (product_id, quantity, attendee_name, status, cost_price) VALUES (?, ?, ?, 'Received', ?)", 
              (product_id, quantity, attendee_name, cost_price))
    
    conn.commit()
    conn.close()

def schedule_delivery(product_id, quantity, owner_name, cost_price=0):
    """Schedule a delivery (Owner action). Does NOT update stock yet."""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("INSERT INTO deliveries (product_id, quantity, attendee_name, status, cost_price) VALUES (?, ?, ?, 'Scheduled', ?)", 
              (product_id, quantity, owner_name, cost_price))
    
    conn.commit()
    conn.close()

def get_scheduled_deliveries():
    """Fetch all deliveries with status 'Scheduled'."""
    conn = get_connection()
    query = '''
        SELECT d.id, p.name, d.quantity, d.delivery_date, d.attendee_name as scheduler, d.cost_price
        FROM deliveries d
        JOIN products p ON d.product_id = p.id
        WHERE d.status = 'Scheduled'
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def confirm_delivery(delivery_id, attendee_name):
    """Confirm a scheduled delivery and update stock (Attendee action)."""
    conn = get_connection()
    c = conn.cursor()
    
    # Get delivery details
    c.execute("SELECT product_id, quantity FROM deliveries WHERE id = ? AND status = 'Scheduled'", (delivery_id,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return False, "Delivery not found or already confirmed."
        
    product_id, quantity = result
    
    # Update product quantity
    c.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (quantity, product_id))
    
    # Update delivery status
    c.execute("UPDATE deliveries SET status = 'Received', attendee_name = ? WHERE id = ?", 
              (attendee_name, delivery_id))
    
    conn.commit()
    conn.close()
    return True, "Delivery confirmed and stock updated."

def get_profit_data():
    """Calculate total sales revenue and total delivery costs."""
    conn = get_connection()
    c = conn.cursor()
    
    # Total Revenue
    c.execute("SELECT SUM(total_price) FROM sales")
    result_sales = c.fetchone()[0]
    total_sales = result_sales if result_sales else 0
    
    # Total Cost (Expenses) - Includes Scheduled AND Received? 
    # User said "Sales minus goods bought". Goods bought usually implies 'Received'. 
    # But if Owner 'schedules' it, they 'bought' it? Let's count all deliveries as expenses to be safe/conservative, 
    # or just confirmed ones. Let's do ALL to reflect the "Willing to pay" commitment.
    # Actually, committed cost vs actual cost. Let's stick to ALL deliveries for now as "Goods Bought".
    
    c.execute("SELECT SUM(cost_price * quantity) FROM deliveries")
    result_cost = c.fetchone()[0]
    total_cost = result_cost if result_cost else 0
    
    conn.close()
    return total_sales, total_cost

    conn.close()
    return total_sales, total_cost

def get_all_deliveries():
    """Fetch all deliveries (scheduled and received) for history log."""
    conn = get_connection()
    query = '''
        SELECT 
            d.delivery_date as 'Date',
            p.name as 'Product',
            p.brand as 'Brand',
            d.quantity as 'Qty',
            d.cost_price as 'Unit Cost',
            (d.quantity * d.cost_price) as 'Total Cost',
            d.status as 'Status',
            d.attendee_name as 'Handler'
        FROM deliveries d
        JOIN products p ON d.product_id = p.id
        ORDER BY d.delivery_date DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def record_sale(product_id, quantity, attendee_name):
    """Record a sale and decrease stock. Returns True if successful, False if insufficient stock."""
    conn = get_connection()
    c = conn.cursor()
    
    # Check availability
    c.execute("SELECT quantity, price FROM products WHERE id = ?", (product_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        return False, "Product not found"
    
    current_qty, price = result
    
    if current_qty < quantity:
        conn.close()
        return False, f"Insufficient stock. Only {current_qty} available."
    
    # Update stock
    new_qty = current_qty - quantity
    c.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_qty, product_id))
    
    # Record sale
    total_price = price * quantity
    c.execute("INSERT INTO sales (product_id, quantity, total_price, attendee_name) VALUES (?, ?, ?, ?)",
              (product_id, quantity, total_price, attendee_name))
    
    conn.commit()
    conn.close()
    return True, "Sale recorded successfully"

def get_sales_data():
    """Fetch sales data for analysis."""
    conn = get_connection()
    query = '''
        SELECT s.sale_date, p.name, p.brand, s.quantity, s.total_price 
        FROM sales s
        JOIN products p ON s.product_id = p.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_low_stock_products():
    """Fetch products that are below minimum stock level."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products WHERE quantity <= min_stock_level", conn)
    conn.close()
    return df
