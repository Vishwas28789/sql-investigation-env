"""Grader for evaluating SQL query correctness in SQL Investigation environment."""

import json
from db import DatabaseManager
from tasks import get_task


class Grader:
    """Grades SQL queries based on correctness and accuracy."""
    
    def grade(self, db_manager: DatabaseManager, agent_query: str, task_id: int) -> float:
        """
        Grade an agent's SQL query against the expected result.
        
        Scoring logic:
        - 1.0: Exact semantic match (same rows, any order)
        - 0.7: ≥80% rows match
        - 0.3: Query executes but <80% match
        - 0.0: Query fails or invalid task
        
        IMPORTANT: Compares RESULT OUTPUT, not query strings.
        
        Args:
            db_manager: DatabaseManager instance with initialized database
            agent_query: SQL query submitted by the agent
            task_id: ID of the task being graded
            
        Returns:
            Score between 0.0 and 1.0
        """
        try:
            # Get the task definition
            task = get_task(task_id)
            if not task or "expected_query_template" not in task:
                print(f"[GRADER] Task {task_id}: Invalid task definition")
                return 0.0
            
            expected_query = task["expected_query_template"]
            
            # Execute both queries
            agent_rows, agent_error = db_manager.execute_query(agent_query)
            expected_rows, expected_error = db_manager.execute_query(expected_query)
            
            print(f"\n[GRADER] Task {task_id} - Agent Query:")
            print(f"  Query: {agent_query[:100]}")
            print(f"  Rows returned: {len(agent_rows) if agent_rows and not agent_error else 0}")
            if agent_error:
                print(f"  ERROR: {agent_error}")
            
            print(f"\n[GRADER] Task {task_id} - Expected Query:")
            print(f"  Query: {expected_query[:100]}")
            print(f"  Rows returned: {len(expected_rows) if expected_rows and not expected_error else 0}")
            if expected_error:
                print(f"  ERROR: {expected_error}")
            
            # If agent query fails, return 0.0
            if agent_error or agent_rows is None:
                print(f"[GRADER] Task {task_id}: Agent query FAILED → Score 0.0")
                return 0.0
            
            # If expected query fails, cannot grade
            if expected_error or expected_rows is None:
                print(f"[GRADER] Task {task_id}: Expected query FAILED → Cannot grade")
                return 0.0
            
            # Normalize both result sets
            agent_norm = self._normalize_simple(agent_rows)
            expected_norm = self._normalize_simple(expected_rows)
            
            print(f"\n[GRADER] Task {task_id} - Normalized Results:")
            print(f"  Agent: {agent_norm}")
            print(f"  Expected: {expected_norm}")
            
            # Check for EXACT MATCH
            if agent_norm == expected_norm:
                print(f"[GRADER] Task {task_id}: EXACT MATCH → Score 1.0")
                return 1.0
            
            # Calculate partial match
            match_count = sum(1 for row in agent_norm if row in expected_norm)
            total = len(expected_norm) if expected_norm else 1
            match_ratio = match_count / total
            
            print(f"  Match ratio: {match_count}/{total} = {match_ratio:.1%}")
            
            if match_ratio >= 0.8:
                print(f"[GRADER] Task {task_id}: PARTIAL MATCH (≥80%) → Score 0.7")
                return 0.7
            else:
                print(f"[GRADER] Task {task_id}: LOW MATCH (<80%) → Score 0.3")
                return 0.3
                
        except Exception as e:
            print(f"[GRADER] Task {task_id}: EXCEPTION - {type(e).__name__}: {str(e)}")
            return 0.0
    
    def _normalize_simple(self, rows: list) -> list:
        """
        Simple normalization: convert all row values to strings, sort for comparison.
        
        Args:
            rows: List of row data (sqlite3.Row, dict, tuple, etc.)
            
        Returns:
            Sorted list of normalized row tuples
        """
        if not rows:
            return []
        
        normalized = []
        for row in rows:
            try:
                # Handle different row types
                if isinstance(row, dict) or hasattr(row, 'keys'):
                    # Dict or sqlite3.Row: convert values to strings
                    values = tuple(str(v).strip() if v is not None else "NULL" for v in row.values())
                elif isinstance(row, (list, tuple)):
                    # List/tuple: convert values to strings
                    values = tuple(str(v).strip() if v is not None else "NULL" for v in row)
                else:
                    # Unknown type: skip
                    continue
                
                normalized.append(values)
            except Exception:
                # Skip problematic rows
                pass
        
        # Return sorted for order-independent comparison
        return sorted(normalized)
    
    def _get_column_names(self, rows: list) -> list:
        """
        Extract column names from result rows (order-independent).
        
        Extracts column names from the first row and returns them sorted
        for consistent order-independent comparison.
        
        Args:
            rows: List of result rows (sqlite3.Row, dict, tuple, or other)
            
        Returns:
            Sorted list of column names (empty list if no rows)
        """
        if not rows:
            return []
        
        first_row = rows[0]
        
        try:
            # Try to get column names from row object
            if hasattr(first_row, 'keys'):
                # sqlite3.Row object or dict with keys() method
                col_names = list(first_row.keys())
            elif isinstance(first_row, dict):
                # Plain dictionary
                col_names = list(first_row.keys())
            elif isinstance(first_row, (list, tuple)):
                # Tuple/list - can't extract column names reliably
                col_names = []
            else:
                col_names = []
        except Exception:
            col_names = []
        
        # Return sorted for order-independent comparison
        return sorted(col_names) if col_names else []
    
    def get_feedback(self, score: float, error: str = "") -> str:
        """
        Generate human-readable feedback based on score.
        
        Args:
            score: Grade score between 0.0 and 1.0
            error: Optional error message if query failed
            
        Returns:
            Human-readable feedback string
        """
        try:
            if score >= 0.95:  # ~1.0, exact match
                return "✓ Perfect! Your query matches the expected results exactly. Excellent work!"
            elif score >= 0.65:  # ~0.7, good match
                return "✓ Good! Column structure is correct. Some rows don't match expected results. Review WHERE conditions, JOINs, or aggregations."
            elif score >= 0.25:  # ~0.3, partial match
                if error:
                    return f"⚠ Query executed but produced incorrect results: {error}"
                else:
                    return "⚠ Query executed but produced incorrect results. Check SQL logic, column selection, and filtering conditions."
            else:  # ~0.0, failed
                if error:
                    return f"✗ Query failed to execute. Error: {error}"
                else:
                    return "✗ Query could not be executed. Check SQL syntax and ensure all column/table names are correct."
        except Exception:
            return "Unable to generate feedback"
