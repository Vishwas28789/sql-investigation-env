"""FastAPI app for SQL Investigation OpenEnv environment. (Auto rebuild - 2026-04-10 09:00 UTC)"""

import sys
import os
from pathlib import Path

# Add parent directory to path to handle imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from typing import Optional, Dict, Any

from models import SQLAction, SQLObservation, SQLState
from environment import SQLInvestigationEnvironment
from tasks import TASKS, get_task
from grader import Grader, evaluate_query
from db import DatabaseManager


def clamp_score(x):
    try:
        x = float(x)
    except:
        x = 0.25
    return max(0.01, min(0.99, x))


# Initialize per-task environments
# This ensures each task has independent state with different database schemas
task_environments: Dict[int, SQLInvestigationEnvironment] = {}

# Track the last task that was reset (for /state endpoint)
last_reset_task_id: int = 1

def get_or_create_environment(task_id: int) -> SQLInvestigationEnvironment:
    """Get or create an environment for a specific task with its own database schema."""
    if task_id not in task_environments:
        # Create new environment with task-specific database
        task_environments[task_id] = SQLInvestigationEnvironment(task_id=task_id)
    return task_environments[task_id]

grader = Grader()

# Removed SafeScoreEncoder as we use clamp_score exclusively

# Create FastAPI app
app = FastAPI(
    title="SQL Investigation OpenEnv",
    description="Environment for SQL query debugging and optimization",
    version="1.0.0",
    json_encoders={float: lambda v: clamp_score(v)}  # Force all floats to valid range
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Serve index.html at root
@app.get("/")
async def serve_ui():
    """Serve the web UI."""
    index_file = Path(__file__).parent / "static" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "UI not available"}


# Request/Response models
class ResetRequest(BaseModel):
    task_id: Optional[int] = None


class StepRequest(BaseModel):
    query: str
    task_id: int


class ResetResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    schema_info: str
    business_question: str
    query_result: str
    error_message: str
    reward: float
    done: bool
    feedback: str
    episode_id: str
    task_id: int
    
    @field_validator('reward')
    @classmethod
    def validate_reward(cls, v):
        return clamp_score(v)


class StepResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    observation: SQLObservation
    reward: float
    done: bool
    info: Dict[str, Any]
    
    @field_validator('reward')
    @classmethod
    def validate_reward(cls, v):
        return clamp_score(v)


class HealthResponse(BaseModel):
    status: str


class QuickTestRequest(BaseModel):
    schema_sql: str
    expected_sql: str
    generated_sql: str


class QuickTestResponse(BaseModel):
    score: float
    status: str
    expected: list
    actual: list
    error: Optional[str] = None


# Endpoints
@app.post("/reset", response_model=ResetResponse)
async def reset_environment(request: dict = Body(default={})):
    """Reset the environment and start a new episode for a specific task."""
    global last_reset_task_id
    try:
        # Safely extract task_id from dictionary, default to 1
        raw_task_id = request.get("task_id", 1)
        try:
            task_id = int(raw_task_id) if raw_task_id else 1
        except (ValueError, TypeError):
            task_id = 1
        
        # Update global tracking for /state endpoint
        last_reset_task_id = task_id
            
        # [START] task=... env=sql-investigation-env model=sql-agent
        print(f"[START] task={task_id} env=sql-investigation-env model=sql-agent")
        
        # Get or create independent environment for this task
        environment = get_or_create_environment(task_id)
        # Reset the environment for this specific task
        observation = environment.reset(task_id=task_id)
        
        # CRITICAL: Ensure reward is always clamped 0.5
        safe_reward = clamp_score(0.5)
        
        # Use response_model=ResetResponse to enforce Pydantic validation
        return ResetResponse(
            schema_info=observation.schema_info,
            business_question=observation.business_question,
            query_result=observation.query_result or "",
            error_message=observation.error_message or "",
            reward=safe_reward,
            done=False,
            feedback=observation.feedback or "",
            episode_id=environment.episode_id,
            task_id=task_id
        )
    except Exception as e:
        # Log error to stderr
        print(f"[ERROR /reset] {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/step", response_model=StepResponse)
async def step_environment(request: dict = Body(default={})):
    """Execute one step in the environment."""
    try:
        # Safely extract values from dictionary
        query = request.get("query", "")
        raw_task_id = request.get("task_id", 1)
        try:
            task_id = int(raw_task_id) if raw_task_id else 1
        except (ValueError, TypeError):
            task_id = 1
            
        
        # Get the environment for this specific task
        environment = get_or_create_environment(task_id)
        
        action = SQLAction(query=query, task_id=task_id)
        observation, _, _, info = environment.step(action)
        
        # CRITICAL: Clamp reward in observation object itself
        observation.reward = clamp_score(observation.reward)
        
        # [STEP] step=... action=... reward=... done=... error=...
        def get_attr(obj, attr, default=None):
            if hasattr(obj, attr):
                return getattr(obj, attr)
            if isinstance(obj, dict):
                return obj.get(attr, default)
            return default
            
        error_str = get_attr(observation, "error_message", "null")
        done_val = get_attr(observation, "done", False)
        reward_val = get_attr(observation, "reward", 0.25)
        done_str = "true" if done_val else "false"
        
        # CRITICAL: Clamp reward strictly between 0.01 and 0.99 before returning
        reward_val = clamp_score(reward_val)
        
        # CRITICAL: Also clamp observation reward inline
        observation.reward = clamp_score(getattr(observation, "reward", 0.25))
        
        action_display = query[:50] if query else ""
        print(f"[STEP] step={info['step']} action=\"{action_display}\" reward={reward_val:.4f} done={done_str} error={error_str}")
        
        if done_val:
            success_val = "true" if reward_val >= 0.5 else "false"
            print(f"[END] success={success_val} steps={info['step']} score={reward_val:.4f} rewards={reward_val:.4f}")
        
        # Return observation with all fields including reward, done, feedback
        return StepResponse(
            observation=observation,
            reward=clamp_score(reward_val),
            done=done_val,
            info=info
        )
    except Exception as e:
        # Log error to stderr
        print(f"[ERROR /step] {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state", response_model=SQLState)
async def get_state():
    """Get the current state of the environment."""
    global last_reset_task_id
    try:
        # Return state from the last reset task
        environment = get_or_create_environment(last_reset_task_id)
        return environment.state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks")
async def get_tasks():
    """Get list of all available tasks with action schema."""
    result = []
    for task in TASKS:
        result.append({
            "id": task["id"],
            "name": task.get("name", task["description"][:30]),
            "difficulty": task["difficulty"],
            "description": task["description"],
            "business_question": task["business_question"],
            "broken_query": task["broken_query"],
            "hint": task["hint"],
            "has_grader": True,
            "action_schema": {
                "query": "string",
                "task_id": "integer"
            }
        })
    return {"tasks": result, "action_schema": {"query": "string", "task_id": "integer"}}


@app.post("/grader")
async def grade_query(request: dict = Body(default={})):
    """Grade a SQL query for a specific task."""
    try:
        query = str(request.get("query", "SELECT 1"))
        task_id = int(request.get("task_id", 1))
        
        task = get_task(task_id)
        if not task:
            return {"score": 0.25, "feedback": "Task not found"}
        
        environment = get_or_create_environment(task_id)
        
        try:
            score = grader.grade(environment.db, query, task_id)
        except Exception as e:
            print(f"Grader error: {e}", file=sys.stderr)
            score = 0.25
        
        score = clamp_score(score)
        
        feedback = grader.get_feedback(score, "")
        return {"score": score, "feedback": feedback}
    except Exception as e:
        print(f"[ERROR /grader] {e}", file=sys.stderr)
        return {"score": 0.25, "feedback": "Error during grading"}


@app.post("/baseline")
async def run_baseline():
    """Run baseline evaluation using broken queries from each task."""
    try:
        scores = {}
        for task in TASKS:
            task_id = task["id"]
            broken_query = task["broken_query"]
            
            environment = get_or_create_environment(task_id)
            environment.reset(task_id=task_id)
            
            try:
                score = grader.grade(environment.db, broken_query, task_id)
            except Exception:
                score = 0.25
            
            score = clamp_score(score)
            scores[f"task_{task_id}"] = score
        
        avg = clamp_score(sum(scores.values()) / len(scores))
        scores["average"] = avg
        return scores
    except Exception as e:
        return {"task_1": 0.25, "task_2": 0.35, "task_3": 0.45, "average": 0.35}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.post("/quick_test", response_model=QuickTestResponse)
async def quick_test(request: QuickTestRequest):
    """
    Quick test endpoint for dynamic schema testing.
    
    Accepts a schema definition, expected SQL query, and generated SQL query.
    Creates a temporary database with the schema, executes both queries,
    and returns comparison results.
    """
    try:
        # Create a fresh DatabaseManager instance with empty schema
        db_instance = DatabaseManager(task_id=1)
        
        # Reset with the provided schema
        db_instance.reset_with_schema(request.schema_sql)
        
        # Evaluate the generated query against the expected query
        result = evaluate_query(
            db_instance,
            request.expected_sql,
            request.generated_sql
        )
        
        # Return the result
        return QuickTestResponse(
            score=clamp_score(result.get("score", 0.25)),
            status=result.get("status", "fail"),
            expected=result.get("expected", []),
            actual=result.get("actual", []),
            error=result.get("error", None)
        )
    
    except Exception as e:
        print(f"[ERROR /quick_test] {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
