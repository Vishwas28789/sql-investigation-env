#!/usr/bin/env python3
"""Test grader with FRESH databases to isolate caching issue"""

import sys
sys.path.insert(0, '.')

from db import DatabaseManager
from grader import Grader
from tasks import get_task

print("="*80)
print("TESTING GRADER WITH FRESH DATABASES")
print("="*80)

# Create FRESH database for Task 2 - first one
db_fresh_1 = DatabaseManager(task_id=2)

# Get expected query from tasks
task = get_task(2)
expected_query = task["expected_query_template"]

print(f"\nTEST 1: Fresh DB #1 - Perfect query (WITH LIMIT)")
perfect_query = expected_query
grader = Grader()
print(f"Query: {perfect_query[:80]}...")

rows_perf, _ = db_fresh_1.execute_query(perfect_query)
print(f"Rows returned: {len(rows_perf) if rows_perf else 0}")

score_perf = grader.grade(db_fresh_1, perfect_query, 2)
print(f"Score: {score_perf}\n")


# Create ANOTHER fresh database for Task 2 - clean slate
db_fresh_2 = DatabaseManager(task_id=2)

print(f"TEST 2: Fresh DB #2 - Partial query (NO LIMIT)")  
partial_query = expected_query.replace(" ORDER BY total_spending DESC LIMIT 5", " ORDER BY total_spending DESC")
print(f"Query: {partial_query[:80]}...")

rows_part, _ = db_fresh_2.execute_query(partial_query)
print(f"Rows returned: {len(rows_part) if rows_part else 0}")

grader = Grader()  # Fresh grader
score_part = grader.grade(db_fresh_2, partial_query, 2)
print(f"Score: {score_part}\n")

print(f"Result: Perfect={score_perf:.2f}, Partial={score_part:.2f}")
if score_part < score_perf:
    print("✅ Penalty applied correctly!")
else:
    print("❌ NO PENALTY - Bug detected")
