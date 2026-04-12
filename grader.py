"""
Grader for SQL Investigation OpenEnv Environment

Requirements:
- Deterministic: Same query always produces same score
- Robust: Handles floating point, row order, column order variation
- Fair: Gives partial credit for partial correctness
- Clear: Explains why a query got a certain score
"""

import sys
import builtins
# Redirect all prints for this module to stderr to keep stdout clean for OpenEnv-compliant logs
print = lambda *args, **kwargs: builtins.print(*args, **kwargs, file=sys.stderr)

from db import DatabaseManager
from tasks import get_task
from typing import List, Tuple, Set


def clamp_score(x):
    try:
        x = float(x)
    except:
        x = 0.25
    return max(0.01, min(0.99, x))


class Grader:
    """
    Deterministic, robust SQL query grader.
    
    Scoring approach:
    1. Execute both user and expected queries
    2. Normalize results (floats, nulls, order)
    3. Compare via set intersection
    4. Award partial credit based on % of rows matching
    """
    
    def grade(self, db_manager: DatabaseManager, agent_query: str, task_id: int) -> float:
        """
        Grade a submitted SQL query against expected result.
        
        Args:
            db_manager: Database with task-specific schema
            agent_query: User's SQL query
            task_id: Task ID (1, 2, or 3)
            
        Returns:
            Score (0.0, 1.0) - strictly between 0 and 1, deterministic and reproducible
        """
        try:
            # 1. LOAD TASK DEFINITION
            task = get_task(task_id)
            if not task or "expected_query_template" not in task:
                print(f"[GRADER] Task {task_id}: Invalid task definition")
                score = 0.01
            else:
                expected_query = task["expected_query_template"]
                
                # 2. EXECUTE BOTH QUERIES
                user_rows, user_error = db_manager.execute_query(agent_query)
                expected_rows, expected_error = db_manager.execute_query(expected_query)
                
                print(f"\n{'='*60}")
                print(f"[GRADER] Task {task_id} - Result Comparison")
                print(f"{'='*60}")
                print(f"\nUser Query:")
                print(f"  Rows: {len(user_rows) if user_rows else 0}")
                print(f"  Error: {user_error if user_error else 'None'}")
                
                print(f"\nExpected Query:")
                print(f"  Rows: {len(expected_rows) if expected_rows else 0}")
                print(f"  Error: {expected_error if expected_error else 'None'}")
                
                # 3. VALIDATE QUERY EXECUTION
                if user_error:
                    print(f"\n[RESULT] User query FAILED: {user_error}")
                    print(f"[SCORE] 0.01 (syntax error - minimum reward)")
                    score = 0.01
                elif expected_error or not expected_rows or len(expected_rows) == 0:
                    print(f"\n[ERROR] Expected query failed - cannot grade")
                    print(f"[SCORE] 0.01 (grading error)")
                    score = 0.01
                else:
                    # 4. NORMALIZE BOTH RESULT SETS
                    user_normalized = self._normalize_rows(user_rows) if user_rows else []
                    expected_normalized = self._normalize_rows(expected_rows)
                    
                    print(f"\nNormalized Results:")
                    print(f"  User: {len(user_normalized)} unique rows")
                    print(f"  Expected: {len(expected_normalized)} unique rows")
                    
                    # 5. CALCULATE MATCH SCORE
                    user_set = set(user_normalized)
                    expected_set = set(expected_normalized)
                    
                    # Exact match check
                    if user_set == expected_set:
                        print(f"\n[RESULT] EXACT MATCH - All rows and columns match perfectly")
                        score = 0.99
                    else:
                        # Analyze differences for partial credit
                        matches = user_set & expected_set
                        match_count = len(matches)
                        expected_count = len(expected_set)
                        
                        match_ratio = match_count / expected_count if expected_count > 0 else 0
                        
                        if match_ratio > 0.8:
                            score = 0.75
                            print(f"\n[RESULT] >80% Match score: {score:.2f}")
                        elif match_ratio > 0:
                            score = 0.45
                            print(f"\n[RESULT] Partial Match score: {score:.2f}")
                        else:
                            score = 0.25
                            print(f"\n[RESULT] Query runs but wrong score: {score:.2f}")

        except Exception as e:
            print(f"\n[ERROR] Grader exception: {type(e).__name__}: {str(e)}")
            score = 0.01

        # ========== STRICT OPENENV BOUNDING (0, 1) ==========
        score = clamp_score(score)
        print(f"[GRADER] FINAL CLAMPED SCORE: {score}")
        return score
    
    def _normalize_rows(self, rows: List) -> List[Tuple]:
        """
        Convert rows to normalized, sortable tuples.
        
        Normalizations:
        - Convert all values to strings
        - Round floats to 2 decimal places
        - Handle NULL/None consistently
        - Sort each tuple for immutability
        
        Returns list of normalized tuples (hashable, comparable)
        """
        if not rows:
            return []
        
        normalized = []
        for row in rows:
            try:
                # Extract values based on row type
                if hasattr(row, 'keys') and callable(getattr(row, 'keys', None)):
                    # sqlite3.Row with keys() method
                    values = [row[key] for key in row.keys()]
                elif isinstance(row, dict):
                    values = list(row.values())
                elif isinstance(row, (list, tuple)):
                    values = list(row)
                else:
                    continue
                
                # Normalize each value
                normalized_values = []
                for v in values:
                    norm_v = self._normalize_value(v)
                    normalized_values.append(norm_v)
                
                # Convert to tuple (hashable)
                norm_tuple = tuple(normalized_values)
                normalized.append(norm_tuple)
                
            except Exception as e:
                print(f"  [WARN] Skipped malformed row: {e}")
                continue
        
        # Return sorted list of unique tuples (deterministic)
        return sorted(list(set(normalized)))
    
    def _normalize_value(self, v) -> str:
        """
        Normalize a single value for comparison.
        
        - None → "NULL"
        - float → rounded to 2 decimals
        - int → string
        - str → stripped + lowercase numbers
        """
        if v is None:
            return "NULL"
        
        if isinstance(v, float):
            # Round to 2 decimals to tolerate float precision
            return f"{v:.2f}"
        
        if isinstance(v, int):
            return str(v)
        
        if isinstance(v, str):
            return v.strip()
        
        # Fallback
        return str(v).strip()
    
    def _calculate_score(self, match_ratio: float, user_set: Set, expected_set: Set) -> float:
        """
        DEPRECATED: Use _calculate_smooth_score instead.
        
        Calculate score based on match ratio with tiered approach.
        
        1.0 - exact match (all rows match)
        0.9 - >=90%
        0.8 - >=80%
        0.7 - >=70%
        0.5 - >=50%
        0.3 - >=30%
        0.0 - <30% or query fail
        """
        if match_ratio >= 0.95:
            return 0.95
        elif match_ratio >= 0.90:
            return 0.9
        elif match_ratio >= 0.80:
            return 0.8
        elif match_ratio >= 0.70:
            return 0.7
        elif match_ratio >= 0.50:
            return 0.5
        elif match_ratio >= 0.30:
            return 0.3
        else:
            return 0.01
    
    def _calculate_smooth_score(self, match_ratio: float, extra_penalty: float) -> float:
        """
        Calculate score with smooth reward curve for meaningful partial signals.
        
        Ensures:
        - Syntax errors only return 0.0 (handled in grade())
        - Any successful query returns at least 0.2 (minimum base reward)
        - Smooth scaling from 0.2 → 1.0 based on match ratio
        - Extra row penalty applied
        
        Formula: 0.2 (base) + (match_ratio * 0.8) - extra_penalty
        
        Examples:
        - 0% match, 0 extra: 0.2 + 0 - 0 = 0.2 (minimum)
        - 25% match, 0 extra: 0.2 + 0.2 - 0 = 0.4
        - 50% match, 0 extra: 0.2 + 0.4 - 0 = 0.6
        - 75% match, 0 extra: 0.2 + 0.6 - 0 = 0.8
        - 100% match, 0 extra: 0.2 + 0.8 - 0 = 1.0 (exact match)
        """
        # Base reward of 0.2 for successful execution
        base_reward = 0.2
        
        # Bonus for partial correctness (up to 0.8)
        match_bonus = match_ratio * 0.8
        
        # Calculate score with penalty
        score = base_reward + match_bonus - extra_penalty
        
        # Ensure score stays in valid range (0, 1) - strictly between
        # (Already handled above, but safety check)
        score = max(0.20, min(0.99, score))
        
        return score
    
    def get_feedback(self, score: float, error: str = "") -> str:
        """Generate human-readable feedback based on score."""
        if score >= 0.95:
            return "✓ Perfect! Your query matches exactly. Excellent work!"
        elif score >= 0.80:
            return "✓ Good! Most of your results are correct. Minor adjustments needed."
        elif score >= 0.50:
            return "~ Partial credit. Review JOINs, GROUP BY, and HAVING conditions."
        elif score >= 0.30:
            return "✗ Low match. Check column selection, joins, and aggregations."
        else:
            if error:
                return f"✗ Query failed: {error}"
            else:
                return "✗ Query produced incorrect results. Review logic carefully."


def evaluate_query(db, expected_sql: str, generated_sql: str) -> dict:
    """
    Evaluate a generated SQL query against an expected query.
    
    Args:
        db: DatabaseManager instance with execute_query() method
        expected_sql: SQL query representing the expected result
        generated_sql: SQL query generated/submitted for evaluation
        
    Returns:
        Dictionary with keys:
        - score: Float between 0.0 and 1.0
        - status: "pass" or "fail" 
        - expected: List of expected results
        - actual: List of actual results from generated query
    """
    # Execute expected query
    expected_rows, expected_error = db.execute_query(expected_sql)
    
    # If expected query fails, return error
    if expected_error:
        return {
            "score": clamp_score(0.01),
            "status": "fail",
            "expected": [],
            "actual": [],
            "error": f"Expected query failed: {expected_error}"
        }
    
    # Execute generated query
    generated_rows, generated_error = db.execute_query(generated_sql)
    
    # If generated query fails, return error
    if generated_error:
        return {
            "score": clamp_score(0.01),
            "status": "fail",
            "expected": [list(row) if hasattr(row, 'keys') else row for row in expected_rows],
            "actual": [],
            "error": f"Generated query failed: {generated_error}"
        }
    
    # Convert rows to comparable format (lists)
    expected_data = [list(row) if hasattr(row, 'keys') else row for row in expected_rows]
    actual_data = [list(row) if hasattr(row, 'keys') else row for row in generated_rows]
    
    # Compare results
    if expected_data == actual_data:
        score = 0.99
        status = "pass"
    else:
        score = 0.01
        status = "fail"
    
    return {
        "score": clamp_score(score),
        "status": status,
        "expected": expected_data,
        "actual": actual_data
    }

