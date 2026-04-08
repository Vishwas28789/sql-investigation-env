"""SQL Investigation OpenEnv environment."""

import uuid
import random
from typing import Tuple

from models import SQLAction, SQLObservation, SQLState
from db import DatabaseManager
from tasks import TASKS, get_task
from grader import Grader


def clamp_score(x):
    """Clamp score to strictly between 0.01 and 0.99."""
    try:
        x = float(x)
    except (ValueError, TypeError):
        x = 0.25
    return max(0.01, min(0.99, x))


class SQLInvestigationEnvironment:
    """OpenEnv environment for SQL query debugging and optimization."""
    
    def __init__(self, task_id: int = 1):
        """Initialize the environment for a specific task."""
        self.current_task_id = task_id
        self.db = DatabaseManager(task_id=task_id)
        self.grader = Grader()
        self.current_task = None
        self.episode_id = ""
        self.step_count = 0
        self.max_steps = 10
        self.done = False
    
    def reset(self, task_id: int = None) -> SQLObservation:
        """
        Reset the environment and start a new episode.
        
        Args:
            task_id: Specific task to load. If None, uses current task or defaults to 1.
            
        Returns:
            Initial SQLObservation with schema info and business question.
        """
        # Update task_id if provided
        if task_id is not None:
            self.current_task_id = task_id
        
        # If still no task_id, default to 1
        if self.current_task_id is None:
            self.current_task_id = 1
        
        # Get the task definition
        self.current_task = get_task(self.current_task_id)
        if not self.current_task:
            self.current_task = TASKS[0]
            self.current_task_id = self.current_task["id"]
        
        # Recreate database with task-specific schema
        self.db = DatabaseManager(task_id=self.current_task_id)
        
        # Reset environment state
        self.episode_id = str(uuid.uuid4())
        self.step_count = 0
        self.done = False
        
        # Get schema info for observation
        schema_info = self.db.get_schema_info()
        
        # Return initial observation with reward=0.5 for reset
        return SQLObservation(
            schema_info=schema_info,
            business_question=self.current_task["business_question"],
            query_result=self.current_task["description"],
            error_message="",
            reward=0.5,
            done=False,
            feedback="Task loaded. Examine the schema and submit your SQL query."
        )
    
    def step(self, action: SQLAction) -> Tuple[SQLObservation, float, bool, dict]:
        """
        Execute one step of the environment.
        
        Args:
            action: SQLAction containing the query to execute
            
        Returns:
            Tuple of (observation, reward, done, info_dict)
        """
        # Safety check: ensure current_task is initialized
        if self.current_task is None:
            safe_reward = clamp_score(0.25)
            error_obs = SQLObservation(
                schema_info="",
                business_question="",
                query_result="",
                error_message="No task initialized",
                reward=safe_reward,
                done=True,
                feedback="Error: Reset the environment first with reset(task_id)"
            )
            return (error_obs, safe_reward, True, {
                "step": self.step_count,
                "episode_id": self.episode_id,
                "error": "No task initialized"
            })
        
        # If already done, return terminal observation
        if self.done:
            safe_reward = clamp_score(0.25)
            done_obs = SQLObservation(
                schema_info="",
                business_question="",
                query_result="",
                error_message="Episode already finished",
                reward=safe_reward,
                done=True,
                feedback="Episode complete. Start a new episode with reset()"
            )
            return (
                done_obs,
                safe_reward,
                True,
                {"step": self.step_count, "episode_id": self.episode_id, "error": "Episode finished"}
            )
        
        # Validate action.task_id - must match current task or be None
        if action.task_id is not None and action.task_id != self.current_task_id:
            # Task ID mismatch, use current task ID
            action.task_id = self.current_task_id
        
        # Increment step counter
        self.step_count += 1
        
        # Execute query
        query_result, error = self.db.execute_query(action.query)
        
        # Grade the query using current_task["id"]
        score = self.grader.grade(self.db, action.query, self.current_task["id"])
        
        # Convert query result to string for observation
        result_str = self._format_query_result(query_result)
        
        # Calculate reward: use grader score directly
        reward = clamp_score(score)
        
        # Determine if episode is done
        if score >= 0.9 or self.step_count >= self.max_steps:
            self.done = True
        
        # Generate feedback
        feedback = self.grader.get_feedback(score, error)
        
        # Get current schema info
        schema_info = self.db.get_schema_info()
        
        # Build observation with all required fields
        observation = SQLObservation(
            schema_info=schema_info,
            business_question=self.current_task["business_question"],
            query_result=result_str,
            error_message=error,
            reward=reward,
            done=self.done,
            feedback=feedback
        )
        
        # CRITICAL: Double-check reward is strictly between 0.01 and 0.99
        observation.reward = clamp_score(observation.reward)
        
        # Build info dict with debugging context
        info = {
            "step": self.step_count,
            "episode_id": self.episode_id,
            "score": score,
            "task_id": self.current_task["id"],
            "current_task_id": self.current_task_id,
            "max_steps": self.max_steps
        }
        
        return (observation, reward, self.done, info)
    
    def state(self) -> SQLState:
        """
        Get the current state of the environment.
        
        Returns:
            SQLState object representing current state.
        """
        # Safety checks for None task
        task_id = self.current_task_id if self.current_task_id is not None else 0
        task_desc = self.current_task["description"] if self.current_task else "No task loaded"
        
        return SQLState(
            episode_id=self.episode_id,
            step_count=self.step_count,
            task_id=task_id,
            current_task_description=task_desc,
            max_steps=self.max_steps
        )
    
    def _format_query_result(self, rows: list) -> str:
        """
        Format query result rows into a readable string.
        
        Args:
            rows: List of sqlite3.Row objects
            
        Returns:
            Formatted string representation of results.
        """
        if not rows:
            return "(No results)"
        
        try:
            # Get column names from first row
            first_row = rows[0]
            if isinstance(first_row, dict) or hasattr(first_row, 'keys'):
                columns = list(first_row.keys())
            else:
                return f"({len(rows)} rows returned)"
            
            # Build header
            lines = [" | ".join(str(col) for col in columns)]
            lines.append("-" * len(lines[0]))
            
            # Add up to 10 rows
            for i, row in enumerate(rows[:10]):
                if isinstance(row, dict):
                    values = [str(row[col]) for col in columns]
                else:
                    values = [str(val) for val in row]
                lines.append(" | ".join(values))
            
            # Add truncation notice if needed
            if len(rows) > 10:
                lines.append(f"... ({len(rows) - 10} more rows)")
            
            return "\n".join(lines)
        except Exception:
            return f"({len(rows)} rows returned)"
