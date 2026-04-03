from pydantic import BaseModel


class SQLAction(BaseModel):
    """Represents an SQL action taken by the agent."""
    query: str = ""
    task_id: int = 0


class SQLObservation(BaseModel):
    """Represents the observation returned from executing an SQL action."""
    schema_info: str = ""
    business_question: str = ""
    query_result: str = ""
    error_message: str = ""
    reward: float = 0.0
    done: bool = False
    feedback: str = ""


class SQLState(BaseModel):
    """Represents the current state of the SQL investigation environment."""
    episode_id: str = ""
    step_count: int = 0
    task_id: int = 0
    current_task_description: str = ""
    max_steps: int = 0
