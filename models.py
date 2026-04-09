from pydantic import BaseModel, field_validator, ConfigDict


class SQLAction(BaseModel):
    """Represents an SQL action taken by the agent."""
    model_config = ConfigDict(validate_assignment=True)
    query: str = ""
    task_id: int = 0


class SQLObservation(BaseModel):
    """Represents the observation returned from executing an SQL action."""
    model_config = ConfigDict(validate_assignment=True)
    schema_info: str = ""
    business_question: str = ""
    query_result: str = ""
    error_message: str = ""
    reward: float = 0.25  # CRITICAL: Default must be SAFE (0.01-0.99), NOT 0.0!
    done: bool = False
    feedback: str = ""
    
    @field_validator('reward')
    @classmethod
    def validate_reward(cls, v):
        """Ensure reward is ALWAYS strictly between 0.01 and 0.99."""
        v = float(v)
        # Auto-fix out-of-range values
        if v <= 0.0:
            return 0.01
        if v >= 1.0:
            return 0.99
        return max(0.01, min(0.99, v))


class SQLState(BaseModel):
    """Represents the current state of the SQL investigation environment."""
    model_config = ConfigDict(validate_assignment=True)
    episode_id: str = ""
    step_count: int = 0
    task_id: int = 0
    current_task_description: str = ""
    max_steps: int = 0
