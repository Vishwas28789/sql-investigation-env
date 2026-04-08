"""Task definitions for SQL Investigation environment."""

TASKS = [
    {
        "id": 1,
        "difficulty": "easy",
        "description": "Fix a syntax error in a query that groups orders by country",
        "business_question": "Find the total number of orders per country",
        "broken_query": """SELECT c.country, COUNT(*) as order_count FROM customers c 
JOIN orders o ON c.id = o.customer_id 
GROUP BY c.email""",
        "hint": "Check if all columns in the SELECT clause are separated properly. Missing a comma between columns?",
        "expected_query_template": """SELECT customers.country, COUNT(*)
FROM customers
JOIN orders ON customers.id = orders.customer_id
GROUP BY customers.country"""
    },
    {
        "id": 2,
        "difficulty": "medium",
        "description": "Fix a JOIN condition error that prevents correct customer spending calculation",
        "business_question": "Find top 5 customers by total spending",
        "broken_query": """SELECT c.customer_name, SUM(o.order_amount) as total_spending 
FROM orders o 
JOIN customers c ON o.cust_id = c.cust_id 
GROUP BY c.cust_id, c.customer_name 
ORDER BY total_spending DESC 
LIMIT 3""",
        "hint": "Review the JOIN condition. What column links orders to customers? It's not the order ID.",
        "expected_query_template": """SELECT c.customer_name, SUM(o.order_amount)
FROM orders o 
JOIN customers c ON o.cust_id = c.cust_id 
GROUP BY c.cust_id, c.customer_name"""
    },
    {
        "id": 3,
        "difficulty": "hard",
        "description": "Fix GROUP BY scope and add missing filter conditions for category-level analysis",
        "business_question": "Find product categories where average order value exceeds 100 and at least 3 orders were placed",
        "broken_query": """SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count 
FROM orders o 
JOIN order_items oi ON o.order_id = oi.order_id 
JOIN products p ON oi.product_id = p.product_id 
GROUP BY p.product_category""",
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
