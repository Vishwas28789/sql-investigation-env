#!/usr/bin/env python3
"""
FINAL COMPREHENSIVE QA TEST 
With proper partial queries that have REAL logical errors
"""

import requests
import json
from typing import Tuple

BASE_URL = "http://localhost:7860"

def test(label: str, task_id: int, query: str, expected_range: Tuple[float, float]) -> bool:
    """Test a query and check score is in expected range"""
    try:
        r = requests.post(f"{BASE_URL}/grader", json={"query": query, "task_id": task_id}, timeout=10)
        score = r.json().get("score", 0)
        in_range = expected_range[0] <= score <= expected_range[1]
        status = "✅" if in_range else "❌"
        print(f"  {status} {label:40} Task {task_id}: {score:.2f} (expect {expected_range[0]:.1f}-{expected_range[1]:.1f})")
        return in_range
    except Exception as e:
        print(f"  ❌ {label:40} Task {task_id}: ERROR - {e}")
        return False

print("\n" + "="*90)
print("FINAL QA VERIFICATION: DETERMINISTIC SCORING & GRADER LOGIC CHECK")
print("="*90 + "\n")

passed = 0
total = 0

# ------- TASK 1 -------
print("TASK 1: SELECT with COUNT aggregation")
print("-" * 90)

total += 1
if test("Perfect query", 1,
        "SELECT customers.country, COUNT(*) FROM customers JOIN orders ON customers.id = orders.customer_id GROUP BY customers.country",
        (0.95, 1.05)):
    passed += 1

total += 1
if test("Broken (syntax error)", 1,
        "SELECT country COUNT(*) as order_count FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.country",
        (0.0, 0.3)):
    passed += 1

total += 1
if test("Wrong aggregate (COUNT instead of COUNT(*))", 1,
        "SELECT customers.country, COUNT(id) FROM customers JOIN orders ON customers.id = orders.customer_id GROUP BY customers.country",
        (0.3, 0.8)):
    passed += 1

# ------- TASK 2 -------
print("\nTASK 2: SUM aggregation with LIMIT")
print("-" * 90)

total += 1
if test("Perfect query", 2,
        "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name ORDER BY total_spending DESC LIMIT 5",
        (0.95, 1.05)):
    passed += 1

total += 1
if test("Broken (wrong JOIN condition)", 2,
        "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.order_id = c.cust_id GROUP BY c.cust_id, c.customer_name ORDER BY total_spending DESC LIMIT 5",
        (0.0, 0.3)):
    passed += 1

total += 1
if test("Wrong column (email instead of name)", 2,
        "SELECT c.email, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name ORDER BY total_spending DESC LIMIT 5",
        (0.0, 0.3)):
    passed += 1

# ------- TASK 3 -------
print("\nTASK 3: Multiple JOINs with HAVING clause")
print("-" * 90)

total += 1
if test("Perfect query", 3,
        "SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category HAVING AVG(o.total_amount) > 100 AND COUNT(o.order_id) >= 3 ORDER BY avg_order_value DESC",
        (0.95, 1.05)):
    passed += 1

total += 1
if test("Broken (wrong HAVING condition)", 3,
        "SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category HAVING AVG(o.total_amount) > 500 AND COUNT(o.order_id) >= 10 ORDER BY avg_order_value DESC",
        (0.0, 0.3)):
    passed += 1

total += 1
if test("Partial (missing join to order_items)", 3,
        "SELECT p.product_category, AVG(o.total_amount) as avg_order_value, COUNT(o.order_id) as order_count FROM orders o JOIN products p ON o.order_id = p.product_id GROUP BY p.product_category HAVING AVG(o.total_amount) > 100 AND COUNT(o.order_id) >= 3 ORDER BY avg_order_value DESC",
        (0.0, 0.8)):
    passed += 1

# ------- DETERMINISM TEST -------
print("\nDETERMINISM: 3 runs of perfect queries")
print("-" * 90)

scores_t1 = []
scores_t2 = []
scores_t3 = []

for run in range(3):
    total += 1
    r = requests.post(f"{BASE_URL}/grader", json={"query": "SELECT customers.country, COUNT(*) FROM customers JOIN orders ON customers.id = orders.customer_id GROUP BY customers.country", "task_id": 1}, timeout=10)
    s = r.json().get("score")
    scores_t1.append(s)
    if 0.95 <= s <= 1.05:
        passed += 1

det_pass = len(set(scores_t1)) == 1
status = "✅" if det_pass else "❌"
print(f"  {status} Task 1 Determinism: {scores_t1}")
total += 1
if det_pass:
    passed += 1

# ------- FINAL SUMMARY -------
print("\n" + "="*90)
print(f"FINAL RESULT: {passed}/{total} tests passed")
if passed == total:
    print("✅ ALL TESTS PASSED - SYSTEM READY FOR HACKATHON")
else:
    print(f"❌ {total - passed} tests failed - review system")
print("="*90 + "\n")
