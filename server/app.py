"""FastAPI app for SQL Investigation OpenEnv environment."""

import sys
import os
from pathlib import Path

# Add parent directory to path to handle imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

from models import SQLAction, SQLObservation, SQLState
from environment import SQLInvestigationEnvironment
from tasks import TASKS, get_task
from grader import Grader
from db import DatabaseManager


# Initialize per-task environments
# This ensures each task has independent state with different database schemas
task_environments: Dict[int, SQLInvestigationEnvironment] = {}

def get_or_create_environment(task_id: int) -> SQLInvestigationEnvironment:
    """Get or create an environment for a specific task with its own database schema."""
    if task_id not in task_environments:
        # Create new environment with task-specific database
        task_environments[task_id] = SQLInvestigationEnvironment(task_id=task_id)
    return task_environments[task_id]

grader = Grader()

# Create FastAPI app
app = FastAPI(
    title="SQL Investigation OpenEnv",
    description="Environment for SQL query debugging and optimization",
    version="1.0.0"
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


class GraderRequest(BaseModel):
    query: str
    task_id: int


class GraderResponse(BaseModel):
    score: float
    feedback: str


class StepResponse(BaseModel):
    observation: SQLObservation
    reward: float
    done: bool
    info: Dict[str, Any]


class BaselineResponse(BaseModel):
    task_1: float
    task_2: float
    task_3: float
    average: float


class HealthResponse(BaseModel):
    status: str


class TaskSchema(BaseModel):
    id: int
    difficulty: str
    description: str
    business_question: str
    hint: str
    action_schema: Dict[str, str]


# Endpoints
@app.post("/reset", response_model=SQLObservation)
async def reset_environment(request: ResetRequest):
    """Reset the environment and start a new episode for a specific task."""
    try:
        task_id = request.task_id if request.task_id else 1
        # Get or create independent environment for this task
        environment = get_or_create_environment(task_id)
        # Reset the environment for this specific task
        return environment.reset(task_id=task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/step", response_model=StepResponse)
async def step_environment(request: StepRequest):
    """Execute one step in the environment."""
    try:
        # Get the environment for this specific task
        environment = get_or_create_environment(request.task_id)
        
        action = SQLAction(query=request.query, task_id=request.task_id)
        observation, _, _, info = environment.step(action)
        # Return observation with all fields including reward, done, feedback
        # Reward is taken ONLY from observation.reward (single source of truth)
        return StepResponse(
            observation=observation,
            reward=observation.reward,
            done=observation.done,
            info=info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state", response_model=SQLState)
async def get_state():
    """Get the current state of the environment."""
    try:
        # Return state from the most recently used environment
        # Default to task 1 if no environment exists
        if 1 in task_environments:
            return task_environments[1].state()
        else:
            # Create a fresh environment for task 1
            environment = get_or_create_environment(1)
            return environment.state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks")
async def get_tasks():
    """Get list of all available tasks with action schema."""
    try:
        task_list = []
        for task in TASKS:
            task_schema = TaskSchema(
                id=task["id"],
                difficulty=task["difficulty"],
                description=task["description"],
                business_question=task["business_question"],
                hint=task["hint"],
                action_schema={
                    "query": "string - SQL query to execute",
                    "task_id": "integer - task ID (1, 2, or 3)"
                }
            )
            task_list.append(task_schema)
        return {
            "tasks": task_list,
            "action_schema": {
                "query": "string - SQL query to execute",
                "task_id": "integer - task ID (1, 2, or 3)"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/grader", response_model=GraderResponse)
async def grade_query(request: GraderRequest):
    """Grade a SQL query for a specific task."""
    try:
        # Validate task exists
        task = get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {request.task_id} not found")
        
        # Get the environment for this task to access the database
        environment = get_or_create_environment(request.task_id)
        
        # Grade the query using the task-specific environment's database
        score = grader.grade(environment.db, request.query, request.task_id)
        
        # Get feedback (use empty string for error since we're just grading)
        feedback = grader.get_feedback(score, "")
        
        return GraderResponse(score=score, feedback=feedback)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/baseline", response_model=BaselineResponse)
async def run_baseline():
    """
    Run baseline evaluation using broken queries from each task.
    
    For each task (1, 2, 3):
    1. Reset the environment with that specific task_id
    2. Get the broken_query from task definition
    3. Grade the broken query
    4. Store score as task_N
    
    Returns reproducible scores without randomness.
    """
    try:
        scores = {}
        
        # Evaluate each task's broken query (deterministic: task 1, 2, 3)
        for task in TASKS:
            task_id = task["id"]
            broken_query = task["broken_query"]
            
            # Get or create environment for this specific task
            environment = get_or_create_environment(task_id)
            
            # Reset environment for this specific task
            # This ensures fresh database state for each task evaluation
            environment.reset(task_id=task_id)
            
            # Grade the broken query using the task-specific environment's fresh database
            score = grader.grade(environment.db, broken_query, task_id)
            
            # Store score with key task_1, task_2, task_3
            task_key = f"task_{task_id}"
            scores[task_key] = score
        
        # Calculate average score (guaranteed to have exactly 3 scores)
        average_score = sum(scores.values()) / len(scores)
        
        # Return baseline response with deterministic order
        return BaselineResponse(
            task_1=scores.get("task_1", 0.0),
            task_2=scores.get("task_2", 0.0),
            task_3=scores.get("task_3", 0.0),
            average=average_score
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")
