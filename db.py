import sqlite3
from abc import ABC
from datetime import datetime, timedelta
import random
import string


class DatabaseManager(ABC):
    """Manages SQLite in-memory database for SQL Investigation environment."""

    def __init__(self, task_id: int = 1):
        """Initialize in-memory SQLite connection for a specific task."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.task_id = task_id
        self._setup_task_db(task_id)

    def _setup_task_db(self, task_id: int):
        """Route to task-specific database setup."""
        if task_id == 1:
            self.setup_task1_db()
        elif task_id == 2:
            self.setup_task2_db()
        elif task_id == 3:
            self.setup_task3_db()
        else:
            self.setup_task1_db()  # Default fallback

    def setup_task1_db(self):
        """Task 1: Simple schema with customers and orders only.
        Business Question: Find the total number of orders per country
        """
        cursor = self.conn.cursor()
        
        # Create simplified tables for Task 1
        cursor.execute("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                country TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                created_date TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)
        
        # Insert data for Task 1 (customers + orders)
        self._insert_task1_data(cursor)
        self.conn.commit()

    def setup_task2_db(self):
        """Task 2: Medium schema with customers and orders (different structure).
        Business Question: Calculate total spending by each customer
        """
        cursor = self.conn.cursor()
        
        # Create tables for Task 2 with different structure
        cursor.execute("""
            CREATE TABLE customers (
                cust_id INTEGER PRIMARY KEY,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                signup_date TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                cust_id INTEGER NOT NULL,
                order_amount REAL NOT NULL,
                order_status TEXT NOT NULL,
                order_date TEXT NOT NULL,
                FOREIGN KEY (cust_id) REFERENCES customers(cust_id)
            )
        """)
        
        # Insert data for Task 2
        self._insert_task2_data(cursor)
        self.conn.commit()

    def setup_task3_db(self):
        """Task 3: Complex schema with products, orders, and order_items.
        Business Question: Identify products by category with high order values
        """
        cursor = self.conn.cursor()
        
        # Create full schema for Task 3
        cursor.execute("""
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                product_category TEXT NOT NULL,
                unit_price REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                order_status TEXT NOT NULL,
                order_date TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE order_items (
                item_id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        """)
        
        # Insert data for Task 3
        self._insert_task3_data(cursor)
        self.conn.commit()

    def setup_ecommerce_db(self):
        """Create tables and populate with realistic fake data."""
        cursor = self.conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                country TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                created_date TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # Insert fake data
        self._insert_fake_data(cursor)
        self.conn.commit()

    def _insert_task1_data(self, cursor):
        """Insert data specific to Task 1: customers + orders."""
        first_names = ["John", "Jane", "Michael", "Sarah", "Robert", "Emily", "David", "Laura", "James", "Jennifer", "William", "Maria", "Richard", "Jessica", "Thomas"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        countries = ["USA", "Canada", "UK", "Germany", "France", "Spain", "Australia", "Japan", "Brazil", "Mexico"]
        
        # Insert 12 customers
        for i in range(12):
            first = random.choice(first_names)
            last = random.choice(last_names)
            name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}{i}@example.com"
            country = random.choice(countries)
            cursor.execute(
                "INSERT INTO customers (name, email, country) VALUES (?, ?, ?)",
                (name, email, country)
            )
        
        # Insert 25 orders
        order_statuses = ["completed", "pending", "shipped"]
        base_date = datetime.now() - timedelta(days=60)
        
        for i in range(25):
            customer_id = random.randint(1, 12)
            amount = round(random.uniform(50, 1500), 2)
            status = random.choice(order_statuses)
            days_offset = random.randint(0, 60)
            created_date = (base_date + timedelta(days=days_offset)).strftime("%Y-%m-%d")
            
            cursor.execute(
                "INSERT INTO orders (customer_id, amount, status, created_date) VALUES (?, ?, ?, ?)",
                (customer_id, amount, status, created_date)
            )

    def _insert_task2_data(self, cursor):
        """Insert data specific to Task 2: customers + orders (different column names)."""
        first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry", "Iris", "Jack"]
        last_names = ["Anderson", "Brown", "Clark", "Davis", "Evans", "Foster", "Green", "Harris", "Jackson", "King"]
        
        # Insert 10 customers with different column names
        base_date = datetime.now() - timedelta(days=120)
        for i in range(10):
            first = random.choice(first_names)
            last = random.choice(last_names)
            customer_name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}{i}@company.com"
            signup_date = (base_date + timedelta(days=random.randint(0, 120))).strftime("%Y-%m-%d")
            
            cursor.execute(
                "INSERT INTO customers (customer_name, email, signup_date) VALUES (?, ?, ?)",
                (customer_name, email, signup_date)
            )
        
        # Insert 20 orders with different column names
        order_statuses = ["completed", "pending", "shipped", "delivered"]
        base_date = datetime.now() - timedelta(days=90)
        
        for i in range(20):
            cust_id = random.randint(1, 10)
            order_amount = round(random.uniform(100, 2000), 2)
            order_status = random.choice(order_statuses)
            order_date = (base_date + timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d")
            
            cursor.execute(
                "INSERT INTO orders (cust_id, order_amount, order_status, order_date) VALUES (?, ?, ?, ?)",
                (cust_id, order_amount, order_status, order_date)
            )

    def _insert_task3_data(self, cursor):
        """Insert data specific to Task 3: products + orders + order_items (complex joins)."""
        # Insert 12 products with different categories
        product_data = [
            ("Laptop Pro", "Electronics", 1299.99),
            ("Wireless Mouse", "Electronics", 49.99),
            ("USB-C Cable", "Accessories", 19.99),
            ("Monitor 4K", "Electronics", 449.99),
            ("Desk Chair", "Furniture", 399.99),
            ("Standing Desk", "Furniture", 699.99),
            ("Mechanical Keyboard", "Electronics", 159.99),
            ("Webcam HD", "Electronics", 99.99),
            ("Phone Stand", "Accessories", 24.99),
            ("Laptop Stand", "Accessories", 79.99),
            ("USB Hub", "Accessories", 39.99),
            ("Screen Filter", "Accessories", 29.99),
            ("Vintage Books", "Books", 15.99),
        ]
        
        for name, category, price in product_data:
            randomized_price = price * random.uniform(0.95, 1.05)
            cursor.execute(
                "INSERT INTO products (product_name, product_category, unit_price) VALUES (?, ?, ?)",
                (name, category, round(randomized_price, 2))
            )
        
        # Insert 15 orders
        base_date = datetime.now() - timedelta(days=45)
        for i in range(15):
            customer_id = random.randint(1, 20)
            total_amount = round(random.uniform(50, 3000), 2)
            order_status = random.choice(["completed", "shipped", "processing"])
            order_date = (base_date + timedelta(days=random.randint(0, 45))).strftime("%Y-%m-%d")
            
            cursor.execute(
                "INSERT INTO orders (customer_id, total_amount, order_status, order_date) VALUES (?, ?, ?, ?)",
                (customer_id, total_amount, order_status, order_date)
            )
            order_id = cursor.lastrowid
            
            # Insert 1-4 order items per order
            num_items = random.randint(1, 4)
            for _ in range(num_items):
                product_id = random.randint(1, 12)  # Normal products 1-12
                quantity = random.randint(1, 3)
                line_total = round(random.uniform(30, 800), 2)
                
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, line_total) VALUES (?, ?, ?, ?)",
                    (order_id, product_id, quantity, line_total)
                )

        # Force AT LEAST ONE order for product 13 ("Vintage Books") that fails the HAVING clause (< 3 orders, < 100 avg)
        cursor.execute(
            "INSERT INTO orders (customer_id, total_amount, order_status, order_date) VALUES (?, ?, ?, ?)",
            (1, 15.99, "completed", "2023-01-01")
        )
        order_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, line_total) VALUES (?, ?, ?, ?)",
            (order_id, 13, 1, 15.99)
        )

    def _insert_fake_data(self, cursor):
        """Insert realistic fake data into tables."""
        # Customer names and countries
        first_names = ["John", "Jane", "Michael", "Sarah", "Robert", "Emily", "David", "Laura", "James", "Jennifer", "William", "Maria", "Richard", "Jessica", "Thomas"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]
        countries = ["USA", "Canada", "UK", "Germany", "France", "Spain", "Australia", "Japan", "Brazil", "Mexico"]
        
        # Insert 15 customers
        customers = []
        for i in range(15):
            first = random.choice(first_names)
            last = random.choice(last_names)
            name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}{i}@example.com"
            country = random.choice(countries)
            cursor.execute(
                "INSERT INTO customers (name, email, country) VALUES (?, ?, ?)",
                (name, email, country)
            )
            customers.append(i + 1)
        
        # Product data
        product_data = [
            ("Laptop", "Electronics", 999.99),
            ("Mouse", "Electronics", 29.99),
            ("Keyboard", "Electronics", 79.99),
            ("Monitor", "Electronics", 299.99),
            ("Headphones", "Electronics", 149.99),
            ("USB Cable", "Accessories", 9.99),
            ("Phone Case", "Accessories", 19.99),
            ("Screen Protector", "Accessories", 12.99),
            ("Desk Lamp", "Office", 45.99),
            ("Office Chair", "Office", 249.99),
        ]
        
        # Insert 10 products
        products = []
        for name, category, price in product_data:
            # Add slight randomization to prices
            randomized_price = price * random.uniform(0.9, 1.1)
            cursor.execute(
                "INSERT INTO products (name, category, price) VALUES (?, ?, ?)",
                (name, category, round(randomized_price, 2))
            )
            products.append(len(products) + 1)
        
        # Insert 30 orders
        order_statuses = ["completed", "pending", "shipped", "cancelled", "processing"]
        base_date = datetime.now() - timedelta(days=90)
        
        for i in range(30):
            customer_id = random.choice(customers)
            amount = round(random.uniform(50, 2000), 2)
            status = random.choice(order_statuses)
            days_offset = random.randint(0, 90)
            created_date = (base_date + timedelta(days=days_offset)).strftime("%Y-%m-%d")
            
            cursor.execute(
                "INSERT INTO orders (customer_id, amount, status, created_date) VALUES (?, ?, ?, ?)",
                (customer_id, amount, status, created_date)
            )
            order_id = cursor.lastrowid
            
            # Insert 1-3 order items for each order
            num_items = random.randint(1, 3)
            for _ in range(num_items):
                product_id = random.choice(products)
                quantity = random.randint(1, 5)
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
                    (order_id, product_id, quantity)
                )

    def execute_query(self, sql: str) -> tuple[list, str]:
        """
        Execute SQL query and return results.
        
        Args:
            sql: SQL query string
            
        Returns:
            Tuple of (rows, error) where rows is list of results or empty list on error,
            and error is error message or empty string on success.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return (rows, "")
        except Exception as e:
            return ([], str(e))

    def get_schema_info(self) -> str:
        """
        Get formatted information about all tables and columns.
        
        Returns:
            Formatted string describing the database schema.
        """
        cursor = self.conn.cursor()
        schema_info = "Database Schema:\n\n"
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            schema_info += f"Table: {table_name}\n"
            
            # Get columns for this table
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                schema_info += f"  - {col_name} ({col_type})\n"
            
            schema_info += "\n"
        
        return schema_info

    def reset(self):
        """Drop and recreate all tables with fresh random data."""
        cursor = self.conn.cursor()
        
        # Drop all tables
        cursor.execute("DROP TABLE IF EXISTS order_items")
        cursor.execute("DROP TABLE IF EXISTS orders")
        cursor.execute("DROP TABLE IF EXISTS products")
        cursor.execute("DROP TABLE IF EXISTS customers")
        self.conn.commit()
        
        # Recreate tables and insert fresh data
        self.setup_ecommerce_db()
