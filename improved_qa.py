#!/usr/bin/env python3
"""
IMPROVED QA Testing for SQL Investigation OpenEnv Environment
With better test cases for partial queries
"""

import requests
import json
import time
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:7860"

def test_grader(query: str, task_id: int) -> Dict:
    """Test grader endpoint"""
    try:
        response = requests.post(
            f"{BASE_URL}/grader",
            json={"query": query, "task_id": task_id},
            timeout=5
        )
        return response.json()
    except Exception as e:
        return {"error": str(e), "score": None}

def print_result(label: str, task_id: int, actual_score: float, expected_range: Tuple[float, float]):
    """Print test result with pass/fail"""
    min_score, max_score = expected_range
    in_range = min_score <= actual_score <= max_score
    status = "✅" if in_range else "❌"
    print(f"  {status} {label:30} Task {task_id}: Score={actual_score:.2f} (expected {min_score:.1f}-{max_score:.1f})")
    return in_range

print("\n╔" + "=" * 78 + "╗")
print("║" + " " * 15 + "IMPROVED QA TEST: PARTIAL QUERIES & EDGE CASES" + " " * 17 + "║")
print("╚" + "=" * 78 + "╝\n")

# Better partial queries that will actually score differently
test_cases = {
    "TASK 1": {
        "perfect": "SELECT customers.country, COUNT(*) FROM customers JOIN orders ON customers.id = orders.customer_id GROUP BY customers.country",
        "partial_missing_groupby": "SELECT customers.country, COUNT(*) FROM customers JOIN orders ON customers.id = orders.customer_id",  # Missing GROUP BY
        "partial_wrong_column": "SELECT customers.id, COUNT(*) FROM customers JOIN orders ON customers.id = orders.customer_id GROUP BY customers.country",  # Wrong column in SELECT
        "partial_incomplete_join": "SELECT customers.country FROM customers GROUP BY customers.country",  # Missing orders JOIN
    },
    "TASK 2": {
        "perfect": "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name ORDER BY total_spending DESC LIMIT 5",
        "partial_no_limit": "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name ORDER BY total_spending DESC",  # Missing LIMIT (returns 10 instead of 5)
        "partial_wrong_column": "SELECT c.email, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name ORDER BY total_spending DESC LIMIT 5",  # Wrong column
        "partial_missing_groupby_col": "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id ORDER BY total_spending DESC LIMIT 5",  # Missing customer_name in GROUP BY
    },
    "TASK 3": {
        "perfect": "SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category HAVING AVG(o.total_amount) > 100 AND COUNT(o.order_id) >= 3 ORDER BY avg_order_value DESC",
        "partial_no_having": "SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category ORDER BY avg_order_value DESC",  # Missing HAVING filters
        "partial_wrong_having": "SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category HAVING AVG(o.total_amount) > 50 AND COUNT(o.order_id) >= 2 ORDER BY avg_order_value DESC",  # Wrong HAVING condition
        "partial_missing_join": "SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count FROM orders o JOIN products p ON o.order_id = p.product_id GROUP BY p.product_category HAVING AVG(o.total_amount) > 100 AND COUNT(o.order_id) >= 3 ORDER BY avg_order_value DESC",  # Wrong/missing join
    }
}

all_passed = True

for task_label, queries in test_cases.items():
    task_id = int(task_label.split()[1])
    print(f"\n{task_label}")
    print("=" * 80)
    
    # Perfect query baseline
    perfect_result = test_grader(queries["perfect"], task_id)
    perfect_score = perfect_result.get("score", 0)
    
    passed = print_result("Perfect query", task_id, perfect_score, (0.95, 1.05))
    all_passed = all_passed and passed
    
    # Partial queries
    for query_name, query in queries.items():
        if query_name == "perfect":
            continue
        
        result = test_grader(query, task_id)
        score = result.get("score", 0)
        
        # Partial queries should score between 0.3-0.9 (not 0, not 1)
        passed = print_result(query_name, task_id, score, (0.3, 0.9))
        all_passed = all_passed and passed

print("\n" + "=" * 80)
if all_passed:
    print("✅ ALL TESTS PASSED!")
else:
    print("⚠️ SOME TESTS FAILED - Review partial query definitions")
print("=" * 80 + "\n")
