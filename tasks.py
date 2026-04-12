"""Task definitions for SQL Investigation environment."""

TASKS = [
    {
        "id": 1,
        "difficulty": "easy",
        "description": "Fix a simple SELECT query to correctly filter and order customers",
        "business_question": "Find all customers from the USA or UK, ordered by their name",
        "broken_query": """SELECT name, email, country FROM customers 
WHERE country = 'USA' AND country = 'UK' 
ORDER BY id""",
        "hint": "Check the logical operators in the WHERE clause (AND vs OR) and the ORDER BY column.",
        "expected_query_template": """SELECT name, email, country FROM customers 
WHERE country = 'USA' OR country = 'UK' 
ORDER BY name"""
    },
    {
        "id": 2,
        "difficulty": "medium",
        "description": "Fix a JOIN condition error that prevents correct customer spending calculation",
        "business_question": "Find top 5 customers by total spending",
        "broken_query": """SELECT c.customer_name, SUM(o.order_amount) as total_spending 
FROM orders o 
JOIN customers c ON o.order_id = c.cust_id 
GROUP BY c.cust_id, c.customer_name 
ORDER BY total_spending DESC 
LIMIT 5""",
        "hint": "Review the JOIN condition. What column links orders to customers? It's not the order ID.",
        "expected_query_template": """SELECT c.customer_name, SUM(o.order_amount)
FROM orders o 
JOIN customers c ON o.cust_id = c.cust_id 
GROUP BY c.cust_id, c.customer_name
ORDER BY SUM(o.order_amount) DESC
LIMIT 5"""
    },
    {
        "id": 3,
        "difficulty": "hard",
        "description": "multi-table investigation + anomaly detection",
        "business_question": "Find product categories where average order value exceeds 100 and at least 3 orders were placed",
        "broken_query": """SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count 
FROM orders o 
JOIN order_items oi ON o.order_id = oi.order_id 
JOIN products p ON oi.product_id = p.product_id 
GROUP BY p.product_id""",
        "hint": "Two issues: 1) GROUP BY should be on category, not product ID. 2) You need a HAVING clause to filter groups by aggregated values (average > 100 and count >= 3).",
        "expected_query_template": """SELECT p.product_category, AVG(o.total_amount), COUNT(o.order_id)
FROM orders o 
JOIN order_items oi ON o.order_id = oi.order_id 
JOIN products p ON oi.product_id = p.product_id 
GROUP BY p.product_category 
HAVING AVG(o.total_amount) > 100 AND COUNT(o.order_id) >= 3"""
    }
]


def get_task(task_id: int) -> dict:
    """
    Retrieve a task by ID.
    
    Args:
        task_id: The ID of the task to retrieve
        
    Returns:
        Task dictionary, or empty dict if task not found
    """
    for task in TASKS:
        if task["id"] == task_id:
            return task
    return {}
