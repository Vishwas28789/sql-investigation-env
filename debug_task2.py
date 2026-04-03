#!/usr/bin/env python3
"""Debug Task 2 partial queries to see actual row counts"""

import sys
sys.path.insert(0, '.')

from db import DatabaseManager
from tasks import get_task

db = DatabaseManager(task_id=2)

expected_query = "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name ORDER BY total_spending DESC LIMIT 5"

partial_no_limit = "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name ORDER BY total_spending DESC"

partial_partial = "SELECT c.customer_name, SUM(o.order_amount) as total_spending FROM orders o JOIN customers c ON o.cust_id = c.cust_id GROUP BY c.cust_id, c.customer_name"  # No ORDER BY no LIMIT

print("="*80)
print("TASK 2 QUERY RESULT ANALYSIS")
print("="*80)

rows_expected, err_expected = db.execute_query(expected_query)
rows_no_limit, err_no_limit = db.execute_query(partial_no_limit)
rows_partial, err_partial = db.execute_query(partial_partial)

print(f"\nExpected Query (ORDER BY DESC LIMIT 5):")
print(f"  Rows: {len(rows_expected) if rows_expected else 0}")
if rows_expected:
    print(f"  First 3 rows:")
    for i,row in enumerate(rows_expected[:3]):
        print(f"    {i+1}. {dict(row)}")

print(f"\nPartial Query (ORDER BY DESC, NO LIMIT):")
print(f"  Rows: {len(rows_no_limit) if rows_no_limit else 0}")
if rows_no_limit:
    print(f"  First 3 rows:")
    for i,row in enumerate(rows_no_limit[:3]):
        print(f"    {i+1}. {dict(row)}")
    if len(rows_no_limit) > 3:
        print(f"  Last 3 rows:")
        for i,row in enumerate(rows_no_limit[-3:]):
            print(f"    {len(rows_no_limit)-2+i}. {dict(row)}")

print(f"\nPartial Query (NO ORDER BY, NO LIMIT):")
print(f"  Rows: {len(rows_partial) if rows_partial else 0}")
if rows_partial:
    print(f"  First 3 rows: (note: may be in different order)")
    for i,row in enumerate(rows_partial[:3]):
        print(f"    {i+1}. {dict(row)}")

# Check if first 5 rows of no_limit match expected
if rows_expected and rows_no_limit:
    expected_set = {str(dict(r)) for r in rows_expected}
    no_limit_set = {str(dict(r)) for r in rows_no_limit}
    partial_set = {str(dict(r)) for r in rows_partial}
    
    print(f"\nSET COMPARISON:")
    print(f"  Expected set == No limit set: {expected_set == no_limit_set}")
    print(f"  Expected set == No ORDER/LIMIT set: {expected_set == partial_set}")
    print(f"  Extra rows in no_limit: {len(no_limit_set - expected_set)}")
    print(f"  Extra rows in partial: {len(partial_set - expected_set)}")
