#!/usr/bin/env python3
"""Debug script to investigate partial query scoring"""

import requests
import json

# Task 2 Test
print("="*80)
print("TASK 2 INVESTIGATION")
print("="*80)

# Expected query (with ORDER BY and LIMIT)
expected = "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name ORDER BY total_spending DESC LIMIT 5"

# Partial query (without ORDER BY and LIMIT)
partial = "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name"

# Different partial: missing GROUP BY customer_name
partial_wrong_groupby = "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id"

resp_expected = requests.post('http://localhost:7860/grader', json={'query': expected, 'task_id': 2}, timeout=5).json()
resp_partial = requests.post('http://localhost:7860/grader', json={'query': partial, 'task_id': 2}, timeout=5).json()
resp_wrong_groupby = requests.post('http://localhost:7860/grader', json={'query': partial_wrong_groupby, 'task_id': 2}, timeout=5).json()

print(f"Expected Query Score: {resp_expected.get('score', 'N/A')}")
print(f"Partial Query (no LIMIT) Score: {resp_partial.get('score', 'N/A')}")
print(f"Partial Query (wrong GROUP BY) Score: {resp_wrong_groupby.get('score', 'N/A')}")

print("\n" + "="*80)
print("TASK 3 INVESTIGATION")
print("="*80)

# Expected query (with HAVING and ORDER BY)
expected3 = "SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category HAVING AVG(o.total_amount) > 100 AND COUNT(o.order_id) >= 3 ORDER BY avg_order_value DESC"

# Partial query (without HAVING or ORDER BY)
partial3 = "SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category"

resp_expected3 = requests.post('http://localhost:7860/grader', json={'query': expected3, 'task_id': 3}, timeout=5).json()
resp_partial3 = requests.post('http://localhost:7860/grader', json={'query': partial3, 'task_id': 3}, timeout=5).json()

print(f"Expected Query Score: {resp_expected3.get('score', 'N/A')}")
print(f"Partial Query (no HAVING) Score: {resp_partial3.get('score', 'N/A')}")
print(f"Expected Feedback: {resp_expected3.get('feedback', 'N/A')[:80]}")
print(f"Partial Feedback: {resp_partial3.get('feedback', 'N/A')[:80]}")

print("\nNote: If partial scores same as expected, it means:")
print("  - ORDER BY doesn't affect result comparison")
print("  - LIMIT doesn't affect result comparison")
print("  - This might be CORRECT if we're comparing result *sets*, not *sequences*")
