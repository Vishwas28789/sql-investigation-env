"""SQL Investigation OpenEnv environment."""

import uuid
import random
from typing import Tuple

from models import SQLAction, SQLObservation, SQLState
from db import DatabaseManager
from tasks import TASKS, get_task
from grader import Grader


class SQLInvestigationEnvironment:
    """OpenEnv environment for SQL query debugging and optimization."""
    
    def __init__(self):
        """Initialize the environment."""
        self.db = DatabaseManager()
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
            task_id: Specific task to load. If None, picks a random task.
            
        Returns:
            Initial SQLObservation with schema info and business question.
        """
        # Pick random task if task_id not specified
        if task_id is None:
            self.current_task = random.choice(TASKS)
        else:
            task = get_task(task_id)
            if task:
                self.current_task = task
            else:
                self.current_task = TASKS[0]
        
        # Reset database and environment state
        self.db.reset()
        self.episode_id = str(uuid.uuid4())
        self.step_count = 0
        self.done = False
        
        # Return initial observation
        schema_info = self.db.get_schema_info()
        
        return SQLObservation(
            schema_info=schema_info,
            business_question=self.current_task["business_question"],
            query_result=self.current_task["description"],
            error_message="",
            reward=0.0,
            done=False,
            feedback="Task loaded. Begin by examining the schema and submitting your SQL query."
        )
    
    def step(self, action: SQLAction) -> Tuple[SQLObservation, float, bool, dict]:
        """
        Execute one step of the environment.
        
        Args:
            action: SQLAction containing the query to execute
            
        Returns:
            Tuple of (observation, reward, done, info_dict)
        """
        # If already done, return terminal observation
        if self.done:
            return (
                SQLObservation(
                    schema_info="",
                    business_question="",
                    query_result="",
                    error_message="Episode already finished",
                    reward=0.0,
                    done=True,
                    feedback="Episode complete"
                ),
                0.0,
                True,
                {"step": self.step_count, "episode_id": self.episode_id}
            )
        
        # Increment step counter
        self.step_count += 1
        
        # Execute query
        query_result, error = self.db.execute_query(action.query)
        
        # Grade the query
        score = self.grader.grade(self.db, action.query, self.current_task["id"])
        
        # Convert query result to string for observation
        result_str = self._format_query_result(query_result)
        
        # Calculate reward: use grader score directly with minimal step penalty
        reward = score - (0.01 * self.step_count)
        reward = max(-1.0, min(1.0, reward))  # Clamp between -1 and 1
        
        # Determine if episode is done
        if score >= 0.9 or self.step_count >= self.max_steps:
            self.done = True
        
        # Generate feedback
        feedback = self.grader.get_feedback(score, error)
        
        # Build observation
        observation = SQLObservation(
            schema_info="",
            business_question=self.current_task["business_question"],
            query_result=result_str,
            error_message=error,
            reward=reward,
            done=self.done,
            feedback=feedback
        )
        
        # Build info dict
        info = {
            "step": self.step_count,
            "episode_id": self.episode_id,
            "score": score,
            "task_id": self.current_task["id"],
            "max_steps": self.max_steps
        }
        
        return (observation, reward, self.done, info)
    
    def state(self) -> SQLState:
        """
        Get the current state of the environment.
        
        Returns:
            SQLState object representing current state.
        """
        return SQLState(
            episode_id=self.episode_id,
            step_count=self.step_count,
            task_id=self.current_task["id"] if self.current_task else 0,
            current_task_description=self.current_task["description"] if self.current_task else "",
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
