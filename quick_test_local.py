"""
Local test script for quick_test endpoint.

Tests the evaluate_query function with a simple schema.
"""

import sys
from pathlib import Path

# Add parent directory to path to handle imports
sys.path.insert(0, str(Path(__file__).parent))

from db import DatabaseManager
from grader import evaluate_query


def test_case_1_correct_query():
    """Test Case 1: Correct SQL query should score 1.0"""
    print("\n" + "="*70)
    print("TEST CASE 1: Correct SQL Query")
    print("="*70)
    
    # Define schema with users table
    schema_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        age INTEGER NOT NULL
    );
    
    INSERT INTO users (id, name, email, age) VALUES (1, 'Alice', 'alice@example.com', 28);
    INSERT INTO users (id, name, email, age) VALUES (2, 'Bob', 'bob@example.com', 32);
    INSERT INTO users (id, name, email, age) VALUES (3, 'Charlie', 'charlie@example.com', 25);
    INSERT INTO users (id, name, email, age) VALUES (4, 'Diana', 'diana@example.com', 29);
    INSERT INTO users (id, name, email, age) VALUES (5, 'Eve', 'eve@example.com', 31);
    """
    
    # Expected query: Get all users ordered by age
    expected_sql = "SELECT id, name, email, age FROM users ORDER BY age ASC"
    
    # Generated query: Same query (should be correct)
    generated_sql = "SELECT id, name, email, age FROM users ORDER BY age ASC"
    
    # Create database and test
    db = DatabaseManager(task_id=1)
    db.reset_with_schema(schema_sql)
    
    result = evaluate_query(db, expected_sql, generated_sql)
    
    print(f"\nSchema SQL:")
    print(f"  {schema_sql.strip()[:80]}...")
    print(f"\nExpected Query: {expected_sql}")
    print(f"Generated Query: {generated_sql}")
    print(f"\nResult:")
    print(f"  Score: {result['score']}")
    print(f"  Status: {result['status']}")
    print(f"  Expected Data: {result['expected']}")
    print(f"  Actual Data: {result['actual']}")
    
    # Verify result
    assert result['score'] == 1.0, f"Expected score 1.0, got {result['score']}"
    assert result['status'] == "pass", f"Expected status 'pass', got {result['status']}"
    print("\n✓ TEST PASSED: Score = 1.0")
    return result


def test_case_2_incorrect_query():
    """Test Case 2: Incorrect SQL query should score 0.0"""
    print("\n" + "="*70)
    print("TEST CASE 2: Incorrect SQL Query")
    print("="*70)
    
    # Define schema with users table
    schema_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        age INTEGER NOT NULL
    );
    
    INSERT INTO users (id, name, email, age) VALUES (1, 'Alice', 'alice@example.com', 28);
    INSERT INTO users (id, name, email, age) VALUES (2, 'Bob', 'bob@example.com', 32);
    INSERT INTO users (id, name, email, age) VALUES (3, 'Charlie', 'charlie@example.com', 25);
    INSERT INTO users (id, name, email, age) VALUES (4, 'Diana', 'diana@example.com', 29);
    INSERT INTO users (id, name, email, age) VALUES (5, 'Eve', 'eve@example.com', 31);
    """
    
    # Expected query: Get users sorted by age ASC
    expected_sql = "SELECT id, name, email, age FROM users ORDER BY age ASC"
    
    # Generated query: Get users sorted by age DESC (wrong order)
    generated_sql = "SELECT id, name, email, age FROM users ORDER BY age DESC"
    
    # Create database and test
    db = DatabaseManager(task_id=1)
    db.reset_with_schema(schema_sql)
    
    result = evaluate_query(db, expected_sql, generated_sql)
    
    print(f"\nSchema SQL:")
    print(f"  {schema_sql.strip()[:80]}...")
    print(f"\nExpected Query: {expected_sql}")
    print(f"Generated Query: {generated_sql}")
    print(f"\nResult:")
    print(f"  Score: {result['score']}")
    print(f"  Status: {result['status']}")
    print(f"  Expected Data: {result['expected']}")
    print(f"  Actual Data: {result['actual']}")
    
    # Verify result
    assert result['score'] == 0.0, f"Expected score 0.0, got {result['score']}"
    assert result['status'] == "fail", f"Expected status 'fail', got {result['status']}"
    print("\n✓ TEST PASSED: Score = 0.0 (incorrect query detected)")
    return result


def test_case_3_aggregation_query():
    """Test Case 3: Aggregation query - count users by age group"""
    print("\n" + "="*70)
    print("TEST CASE 3: Aggregation Query (GROUP BY)")
    print("="*70)
    
    # Define schema with users table
    schema_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER NOT NULL
    );
    
    INSERT INTO users (id, name, age) VALUES (1, 'Alice', 25);
    INSERT INTO users (id, name, age) VALUES (2, 'Bob', 25);
    INSERT INTO users (id, name, age) VALUES (3, 'Charlie', 30);
    INSERT INTO users (id, name, age) VALUES (4, 'Diana', 30);
    INSERT INTO users (id, name, age) VALUES (5, 'Eve', 30);
    INSERT INTO users (id, name, age) VALUES (6, 'Frank', 35);
    """
    
    # Expected query: Count users by age
    expected_sql = "SELECT age, COUNT(*) as count FROM users GROUP BY age ORDER BY age ASC"
    
    # Generated query: Same query
    generated_sql = "SELECT age, COUNT(*) as count FROM users GROUP BY age ORDER BY age ASC"
    
    # Create database and test
    db = DatabaseManager(task_id=1)
    db.reset_with_schema(schema_sql)
    
    result = evaluate_query(db, expected_sql, generated_sql)
    
    print(f"\nSchema SQL:")
    print(f"  {schema_sql.strip()[:80]}...")
    print(f"\nExpected Query: {expected_sql}")
    print(f"Generated Query: {generated_sql}")
    print(f"\nResult:")
    print(f"  Score: {result['score']}")
    print(f"  Status: {result['status']}")
    print(f"  Expected Data: {result['expected']}")
    print(f"  Actual Data: {result['actual']}")
    
    # Verify result
    assert result['score'] == 1.0, f"Expected score 1.0, got {result['score']}"
    assert result['status'] == "pass", f"Expected status 'pass', got {result['status']}"
    print("\n✓ TEST PASSED: Aggregation query correct (Score = 1.0)")
    return result


def test_case_4_query_error():
    """Test Case 4: Query with syntax error should return 0.0"""
    print("\n" + "="*70)
    print("TEST CASE 4: Query with Syntax Error")
    print("="*70)
    
    # Define schema with users table
    schema_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER NOT NULL
    );
    
    INSERT INTO users (id, name, age) VALUES (1, 'Alice', 25);
    INSERT INTO users (id, name, age) VALUES (2, 'Bob', 30);
    """
    
    # Expected query: Valid query
    expected_sql = "SELECT * FROM users"
    
    # Generated query: Invalid syntax
    generated_sql = "SELECT * FRON users"  # Typo: FRON instead of FROM
    
    # Create database and test
    db = DatabaseManager(task_id=1)
    db.reset_with_schema(schema_sql)
    
    result = evaluate_query(db, expected_sql, generated_sql)
    
    print(f"\nSchema SQL:")
    print(f"  {schema_sql.strip()[:80]}...")
    print(f"\nExpected Query: {expected_sql}")
    print(f"Generated Query: {generated_sql}")
    print(f"\nResult:")
    print(f"  Score: {result['score']}")
    print(f"  Status: {result['status']}")
    print(f"  Error: {result.get('error', 'None')}")
    
    # Verify result
    assert result['score'] == 0.0, f"Expected score 0.0, got {result['score']}"
    assert result['status'] == "fail", f"Expected status 'fail', got {result['status']}"
    assert result.get('error') is not None, "Expected error message"
    print("\n✓ TEST PASSED: Syntax error detected (Score = 0.0)")
    return result


def main():
    """Run all test cases."""
    print("\n" + "="*70)
    print("QUICK TEST LOCAL - Running All Test Cases")
    print("="*70)
    
    try:
        # Test 1: Correct query
        result1 = test_case_1_correct_query()
        
        # Test 2: Incorrect query
        result2 = test_case_2_incorrect_query()
        
        # Test 3: Aggregation query
        result3 = test_case_3_aggregation_query()
        
        # Test 4: Query with error
        result4 = test_case_4_query_error()
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print("\n✓ All 4 test cases PASSED!")
        print(f"\n  Test 1 (Correct Query):     Score = {result1['score']} (Expected: 1.0)")
        print(f"  Test 2 (Incorrect Query):   Score = {result2['score']} (Expected: 0.0)")
        print(f"  Test 3 (Aggregation Query): Score = {result3['score']} (Expected: 1.0)")
        print(f"  Test 4 (Query Error):       Score = {result4['score']} (Expected: 0.0)")
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*70 + "\n")
        
        return True
    
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
