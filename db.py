import sqlite3
from abc import ABC
from datetime import datetime, timedelta
import random
import string


class DatabaseManager(ABC):
    """Manages SQLite in-memory database for SQL Investigation environment."""

    def __init__(self):
        """Initialize in-memory SQLite connection."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.setup_ecommerce_db()

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
