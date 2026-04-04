#!/usr/bin/env python3
"""
Full end-to-end system test for SQL Investigation Environment.
Tests all 3 tasks with perfect, partial, and broken queries.
"""

import requests
import json
from typing import Dict, List

BASE_URL = "https://vishwas004-sql-investigation-env.hf.space"
# Uncomment for local testing:
# BASE_URL = "http://localhost:8000"

class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.RESET}")

class TestResults:
    def __init__(self):
        self.tasks = {}
        
    def add_task(self, task_id, schema_ok, perfect_score, partial_score, broken_score):
        self.tasks[task_id] = {
            "schema_ok": schema_ok,
            "perfect_score": perfect_score,
            "partial_score": partial_score,
            "broken_score": broken_score
        }
    
    def print_report(self):
        print_header("TEST RESULTS SUMMARY")
        
        all_pass = True
        for task_id in sorted(self.tasks.keys()):
            result = self.tasks[task_id]
            schema_status = "✓" if result["schema_ok"] else "✗"
            
            print(f"TASK {task_id}:")
            print(f"  Schema:        {schema_status}")
            print(f"  Perfect Score: {result['perfect_score']:.2f} (expect 0.9-1.0)")
            print(f"  Partial Score: {result['partial_score']:.2f} (expect 0.2-0.8)")
            print(f"  Broken Score:  {result['broken_score']:.2f} (expect 0.0-0.2)")
            
            # Check validation rules
            schema_valid = result["schema_ok"]
            perfect_valid = 0.9 <= result["perfect_score"] <= 1.0
            broken_valid = result["broken_score"] <= 0.2
            
            if schema_valid and perfect_valid and broken_valid:
                print_success(f"Task {task_id} PASSED")
            else:
                print_error(f"Task {task_id} FAILED")
                if not schema_valid: print(f"    - Schema not loading properly")
                if not perfect_valid: print(f"    - Perfect score out of range")
                if not broken_valid: print(f"    - Broken score too high")
                all_pass = False
            
            print()
        
        return all_pass

def test_reset(task_id: int) -> Dict:
    """Test /reset endpoint for a task"""
    try:
        r = requests.post(f"{BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
        if r.status_code != 200:
            print_error(f"Reset failed with status {r.status_code}")
            return None
        
        data = r.json()
        # Handle both direct schema_info and nested observation
        if "observation" in data:
            obs = data["observation"]
        else:
            obs = data
        
        schema_info = obs.get("schema_info", "")
        question = obs.get("business_question", "")
        
        return {
            "schema_info": schema_info,
            "business_question": question,
            "episode_id": data.get("episode_id", "")
        }
    except Exception as e:
        print_error(f"Reset exception: {e}")
        return None

def test_grader(task_id: int, query: str) -> float:
    """Test /grader endpoint and return score"""
    try:
        r = requests.post(
            f"{BASE_URL}/grader",
            json={"query": query, "task_id": task_id},
            timeout=10
        )
        if r.status_code != 200:
            print_warning(f"Grader failed with status {r.status_code}")
            return None
        
        data = r.json()
        score = data.get("score", 0.0)
        return score
    except Exception as e:
        print_warning(f"Grader exception: {e}")
        return None

def test_baseline() -> Dict:
    """Test /baseline endpoint"""
    try:
        r = requests.post(f"{BASE_URL}/baseline", timeout=10)
        if r.status_code != 200:
            print_error(f"Baseline failed with status {r.status_code}")
            return None
        
        return r.json()
    except Exception as e:
        print_error(f"Baseline exception: {e}")
        return None

# Perfect queries (should score 0.9-1.0)
PERFECT_QUERIES = {
    1: """SELECT c.country, COUNT(*) 
FROM customers c 
JOIN orders o ON c.id = o.customer_id 
GROUP BY c.country""",
    
    2: """SELECT c.customer_name, SUM(o.order_amount) 
FROM orders o 
JOIN customers c ON o.cust_id = c.cust_id 
GROUP BY c.cust_id, c.customer_name 
ORDER BY SUM(o.order_amount) DESC 
LIMIT 5""",
    
    3: """SELECT p.product_category, AVG(o.total_amount), COUNT(o.order_id)
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_category
HAVING AVG(o.total_amount) > 100 AND COUNT(o.order_id) >= 3"""
}

# Partial queries (should score 0.2-0.8)
PARTIAL_QUERIES = {
    1: """SELECT c.country, COUNT(*) 
FROM customers c 
JOIN orders o ON c.id = o.customer_id 
GROUP BY c.country
LIMIT 3""",
    
    2: """SELECT c.customer_name, SUM(o.order_amount) 
FROM orders o 
JOIN customers c ON o.cust_id = c.cust_id 
GROUP BY c.cust_id"""",
    
    3: """SELECT p.product_category, AVG(o.total_amount), COUNT(o.order_id)
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_category"""
}

# Broken queries (should score 0.0-0.2)
BROKEN_QUERIES = {
    1: "SELECT country COUNT(*) FROM customers WHERE country = 'USA'",
    2: "SELECT c.customer_name SUM(o.order_amount) FROM orders o",
    3: "SELECT p.product_id FROM orders o JOIN products p"
}

def main():
    print_header("SQL INVESTIGATION ENVIRONMENT - FULL SYSTEM TEST")
    
    results = TestResults()
    
    # Test each task
    for task_id in [1, 2, 3]:
        print_info(f"Testing Task {task_id}...")
        
        # Test reset
        reset_data = test_reset(task_id)
        if not reset_data:
            print_error(f"Cannot proceed with Task {task_id} - reset failed")
            continue
        
        schema_info = reset_data["schema_info"]
        question = reset_data["business_question"]
        
        # Validate schema
        schema_ok = len(schema_info) > 100
        if schema_ok:
            print_success(f"Schema loaded ({len(schema_info)} chars)")
            print(f"\nSchema Preview:")
            for line in schema_info.split('\n')[:8]:
                if line.strip():
                    print(f"  {line}")
        else:
            print_error(f"Schema empty or too short ({len(schema_info)} chars)")
        
        print(f"\nBusiness Question: {question}")
        
        # Test queries
        print(f"\n--- Testing Queries for Task {task_id} ---\n")
        
        perfect_query = PERFECT_QUERIES[task_id]
        perfect_score = test_grader(task_id, perfect_query)
        if perfect_score is not None:
            print_info(f"Perfect Query Score: {perfect_score:.2f}")
        else:
            perfect_score = 0.0
        
        partial_query = PARTIAL_QUERIES[task_id]
        partial_score = test_grader(task_id, partial_query)
        if partial_score is not None:
            print_info(f"Partial Query Score: {partial_score:.2f}")
        else:
            partial_score = 0.0
        
        broken_query = BROKEN_QUERIES[task_id]
        broken_score = test_grader(task_id, broken_query)
        if broken_score is not None:
            print_info(f"Broken Query Score: {broken_score:.2f}")
        else:
            broken_score = 0.0
        
        results.add_task(task_id, schema_ok, perfect_score, partial_score, broken_score)
        print()
    
    # Test baseline
    print_info("Testing /baseline endpoint...")
    baseline = test_baseline()
    if baseline:
        print_success("Baseline Results:")
        print(f"  Task 1: {baseline.get('task_1', 0):.2f}")
        print(f"  Task 2: {baseline.get('task_2', 0):.2f}")
        print(f"  Task 3: {baseline.get('task_3', 0):.2f}")
        print(f"  Average: {baseline.get('average', 0):.2f}")
    else:
        print_error("Baseline test failed")
    
    # Print summary
    all_pass = results.print_report()
    
    if all_pass:
        print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 ALL TESTS PASSED - SYSTEM READY FOR SUBMISSION{Colors.RESET}")
    else:
        print(f"\n{Colors.BOLD}{Colors.RED}❌ SOME TESTS FAILED - PLEASE FIX ISSUES{Colors.RESET}")
    
    return all_pass

if __name__ == "__main__":
    main()
