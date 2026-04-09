"""FastAPI app for SQL Investigation OpenEnv environment. (Redeploy trigger)"""

import sys
import os
from pathlib import Path

# Add parent directory to path to handle imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Dict, Any

from models import SQLAction, SQLObservation, SQLState
from environment import SQLInvestigationEnvironment
from tasks import TASKS, get_task
from grader import Grader
from db import DatabaseManager


def clamp_score(x):
    """Clamp score to strictly between 0.01 and 0.99."""
    try:
        x = float(x)
    except (ValueError, TypeError):
        x = 0.25
    return max(0.01, min(0.99, x))


def safe_score(x):
    """Force score to safe range (0.01-0.99), never 0.0 or 1.0."""
    try:
        x = float(x)
    except:
        x = 0.25
    if x <= 0.0:
        return 0.01
    if x >= 1.0:
        return 0.99
    return x


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

# Custom JSON encoder to force score boundaries at serialization
from json import JSONEncoder
from fastapi.responses import JSONResponse

class SafeScoreEncoder(JSONEncoder):
    """JSON encoder that forces all scores to be strictly in (0, 1)."""
    def encode(self, o):
        result = super().encode(o)
        # Extra safety: scan for 0.0 and 1.0 in JSON output and convert them
        # This prevents any floating-point edge cases
        result = result.replace('"reward": 0.0,', '"reward": 0.01,')
        result = result.replace('"reward": 1.0,', '"reward": 0.99,')
        result = result.replace('"reward": 0.0}', '"reward": 0.01}')
        result = result.replace('"reward": 1.0}', '"reward": 0.99}')
        result = result.replace('"score": 0.0,', '"score": 0.01,')
        result = result.replace('"score": 1.0,', '"score": 0.99,')
        result = result.replace('"score": 0.0}', '"score": 0.01}')
        result = result.replace('"score": 1.0}', '"score": 0.99}')
        result = result.replace('"task_1": 0.0,', '"task_1": 0.01,')
        result = result.replace('"task_1": 1.0,', '"task_1": 0.99,')
        result = result.replace('"task_2": 0.0,', '"task_2": 0.01,')
        result = result.replace('"task_2": 1.0,', '"task_2": 0.99,')
        result = result.replace('"task_3": 0.0,', '"task_3": 0.01,')
        result = result.replace('"task_3": 1.0,', '"task_3": 0.99,')
        result = result.replace('"average": 0.0,', '"average": 0.01,')
        result = result.replace('"average": 1.0,', '"average": 0.99,')
        result = result.replace('"average": 0.0}', '"average": 0.01}')
        result = result.replace('"average": 1.0}', '"average": 0.99}')
        return result

# Create FastAPI app
app = FastAPI(
    title="SQL Investigation OpenEnv",
    description="Environment for SQL query debugging and optimization",
    version="1.0.0",
    json_encoders={float: lambda v: max(0.01, min(0.99, float(v)))}  # Force all floats to valid range
)

# ============ ULTRA-DEFENSIVE MIDDLEWARE ============
# Post-process ALL responses to ensure no 0.0 or 1.0 slips through
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import json

class SafeScoreMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure all score/reward values are strictly between 0.01 and 0.99."""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Only process JSON responses
        if "application/json" in response.headers.get("content-type", ""):
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                # Parse and fix JSON
                json_data = json.loads(body)
                body_str = json.dumps(json_data)
                
                # Global string replacements for any 0.0 or 1.0
                body_str = body_str.replace('"score": 0.0,', '"score": 0.01,')
                body_str = body_str.replace('"score": 1.0,', '"score": 0.99,')
                body_str = body_str.replace('"score":0.0,', '"score":0.01,')
                body_str = body_str.replace('"score":1.0,', '"score":0.99,')
                body_str = body_str.replace('"reward": 0.0,', '"reward": 0.01,')
                body_str = body_str.replace('"reward": 1.0,', '"reward": 0.99,')
                body_str = body_str.replace('"reward":0.0,', '"reward":0.01,')
                body_str = body_str.replace('"reward":1.0,', '"reward":0.99,')
                body_str = body_str.replace('"task_1": 0.0,', '"task_1": 0.01,')
                body_str = body_str.replace('"task_1": 1.0,', '"task_1": 0.99,')
                body_str = body_str.replace('"task_1":0.0,', '"task_1":0.01,')
                body_str = body_str.replace('"task_1":1.0,', '"task_1":0.99,')
                body_str = body_str.replace('"task_2": 0.0,', '"task_2": 0.01,')
                body_str = body_str.replace('"task_2": 1.0,', '"task_2": 0.99,')
                body_str = body_str.replace('"task_2":0.0,', '"task_2":0.01,')
                body_str = body_str.replace('"task_2":1.0,', '"task_2":0.99,')
                body_str = body_str.replace('"task_3": 0.0,', '"task_3": 0.01,')
                body_str = body_str.replace('"task_3": 1.0,', '"task_3": 0.99,')
                body_str = body_str.replace('"task_3":0.0,', '"task_3":0.01,')
                body_str = body_str.replace('"task_3":1.0,', '"task_3":0.99,')
                body_str = body_str.replace('"average": 0.0,', '"average": 0.01,')
                body_str = body_str.replace('"average": 1.0,', '"average":0.99,')
                body_str = body_str.replace('"average":0.0,', '"average":0.01,')
                body_str = body_str.replace('"average":1.0,', '"average":0.99,')
                
                # Handle closing braces/brackets
                body_str = body_str.replace('"score": 0.0}', '"score": 0.01}')
                body_str = body_str.replace('"score": 1.0}', '"score": 0.99}')
                body_str = body_str.replace('"reward": 0.0}', '"reward": 0.01}')
                body_str = body_str.replace('"reward": 1.0}', '"reward": 0.99}')
                body_str = body_str.replace('"task_1": 0.0}', '"task_1": 0.01}')
                body_str = body_str.replace('"task_1": 1.0}', '"task_1": 0.99}')
                body_str = body_str.replace('"task_2": 0.0}', '"task_2": 0.01}')
                body_str = body_str.replace('"task_2": 1.0}', '"task_2": 0.99}')
                body_str = body_str.replace('"task_3": 0.0}', '"task_3": 0.01}')
                body_str = body_str.replace('"task_3": 1.0}', '"task_3": 0.99}')
                body_str = body_str.replace('"average": 0.0}', '"average": 0.01}')
                body_str = body_str.replace('"average": 1.0}', '"average": 0.99}')
                
                # Return new response with cleaned JSON
                return Response(
                    content=body_str,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            except Exception:
                # If parsing fails, just return original response
                pass
        
        return response

app.add_middleware(SafeScoreMiddleware)

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
    
    @field_validator('score')
    @classmethod
    def validate_score(cls, v):
        """Ensure score is ALWAYS strictly between 0.01 and 0.99."""
        v = float(v)
        if v <= 0.0:
            return 0.01
        if v >= 1.0:
            return 0.99
        return max(0.01, min(0.99, v))
    
    @model_validator(mode='after')
    def final_score_check(self):
        """Final check: ensure score never escaped validation"""
        if self.score <= 0.0 or self.score >= 1.0:
            self.score = 0.25
        return self


class ResetResponse(BaseModel):
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
        """Ensure reward is ALWAYS strictly between 0.01 and 0.99."""
        v = float(v)
        if v <= 0.0:
            return 0.01
        if v >= 1.0:
            return 0.99
        return max(0.01, min(0.99, v))
    
    @model_validator(mode='after')
    def final_reward_check(self):
        """Final check: ensure reward never escaped validation"""
        if self.reward <= 0.0 or self.reward >= 1.0:
            self.reward = 0.5
        return self


class StepResponse(BaseModel):
    observation: SQLObservation
    reward: float
    done: bool
    info: Dict[str, Any]
    
    @field_validator('reward')
    @classmethod
    def validate_reward(cls, v):
        """Ensure reward is ALWAYS strictly between 0.01 and 0.99."""
        v = float(v)
        if v <= 0.0:
            return 0.01
        if v >= 1.0:
            return 0.99
        return max(0.01, min(0.99, v))
    
    @model_validator(mode='after')
    def final_reward_check(self):
        """Final check: ensure all rewards are valid"""
        if self.reward <= 0.0 or self.reward >= 1.0:
            self.reward = 0.25
        # Also check observation reward
        if self.observation and (self.observation.reward <= 0.0 or self.observation.reward >= 1.0):
            self.observation.reward = 0.25
        return self


class BaselineResponse(BaseModel):
    task_1: float
    task_2: float
    task_3: float
    average: float
    
    @field_validator('task_1', 'task_2', 'task_3', 'average')
    @classmethod
    def validate_scores(cls, v):
        """Ensure all scores are ALWAYS strictly between 0.01 and 0.99."""
        v = float(v)
        if v <= 0.0:
            return 0.01
        if v >= 1.0:
            return 0.99
        return max(0.01, min(0.99, v))
    
    @model_validator(mode='after')
    def final_scores_check(self):
        """Final check: ensure NO score escaped validation"""
        for field_name in ['task_1', 'task_2', 'task_3', 'average']:
            val = getattr(self, field_name, 0.5)
            if val <= 0.0 or val >= 1.0:
                setattr(self, field_name, 0.5)
        return self


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
@app.post("/reset", response_model=ResetResponse)
async def reset_environment(request: dict = Body(default={})):
    """Reset the environment and start a new episode for a specific task."""
    try:
        # Safely extract task_id from dictionary, default to 1
        raw_task_id = request.get("task_id", 1)
        try:
            task_id = int(raw_task_id) if raw_task_id else 1
        except (ValueError, TypeError):
            task_id = 1
            
        # [START] task=... env=sql-investigation-env model=sql-agent
        print(f"[START] task={task_id} env=sql-investigation-env model=sql-agent")
        
        # Get or create independent environment for this task
        environment = get_or_create_environment(task_id)
        # Reset the environment for this specific task
        observation = environment.reset(task_id=task_id)
        
        # CRITICAL: Ensure reward is always 0.5, clamped to valid range
        safe_reward = clamp_score(0.5)
        safe_reward = safe_score(safe_reward)  # TRIPLE safety
        safe_reward = max(0.01, min(0.99, float(safe_reward or 0.25)))
        
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
        reward_val = safe_score(reward_val)  # TRIPLE safety
        reward_val = max(0.01, min(0.99, float(reward_val or 0.25)))
        
        # CRITICAL: Also clamp observation reward inline
        observation.reward = safe_score(max(0.01, min(0.99, float(observation.reward or 0.25))))
        
        action_display = query[:50] if query else ""
        print(f"[STEP] step={info['step']} action=\"{action_display}\" reward={reward_val:.4f} done={done_str} error={error_str}")
        
        if done_val:
            success_val = "true" if reward_val >= 0.5 else "false"
            print(f"[END] success={success_val} steps={info['step']} score={reward_val:.4f} rewards={reward_val:.4f}")
        
        # Return observation with all fields including reward, done, feedback
        return StepResponse(
            observation=observation,
            reward=safe_score(max(0.01, min(0.99, float(reward_val or 0.25)))),
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
        print("START")
        print(f"STEP: Grading query for task {request.task_id}")
        
        # Validate task exists
        task = get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {request.task_id} not found")
        
        # Get the environment for this task to access the database
        environment = get_or_create_environment(request.task_id)
        
        # Grade the query using the task-specific environment's database
        score = grader.grade(environment.db, request.query, request.task_id)
        score = clamp_score(score)  # First clamp
        score = safe_score(score)  # safe_score wrapper
        score = max(0.01, min(0.99, float(score or 0.25)))  # TRIPLE safety
        
        print(f"STEP: Grade calculated: {score:.4f}")
        
        # Get feedback (use empty string for error since we're just grading)
        feedback = grader.get_feedback(score, "")
        print(f"END (score={score:.2f})")
        
        return GraderResponse(score=safe_score(max(0.01, min(0.99, float(score or 0.25)))), feedback=feedback)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR /grader] {str(e)}")
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
        print("START")
        print("STEP: Running baseline evaluation")
        
        # Evaluate each task's broken query (deterministic: task 1, 2, 3)
        for task in TASKS:
            task_id = task["id"]
            broken_query = task["broken_query"]
            print(f"STEP: Evaluating Task {task_id}")
            
            # Get or create environment for this specific task
            environment = get_or_create_environment(task_id)
            
            # Reset environment for this specific task
            # This ensures fresh database state for each task evaluation
            environment.reset(task_id=task_id)
            
            # Grade the broken query using the task-specific environment's fresh database
            score = grader.grade(environment.db, broken_query, task_id)
            score = clamp_score(score)  # First clamp
            score = safe_score(score)  # safe_score wrapper
            score = max(0.01, min(0.99, float(score or 0.25)))  # TRIPLE safety
            
            # Store score with key task_1, task_2, task_3
            task_key = f"task_{task_id}"
            scores[task_key] = score
        
        print("END")
        
        # Calculate average score (guaranteed to have exactly 3 scores)
        average_score = sum(scores.values()) / len(scores)
        average_score = clamp_score(average_score)  # First clamp
        average_score = safe_score(average_score)  # safe_score wrapper
        average_score = max(0.01, min(0.99, float(average_score or 0.25)))  # TRIPLE safety
        
        # Return baseline response with deterministic order
        return BaselineResponse(
            task_1=safe_score(max(0.01, min(0.99, float(scores.get("task_1", 0.25))))),
            task_2=safe_score(max(0.01, min(0.99, float(scores.get("task_2", 0.25))))),
            task_3=safe_score(max(0.01, min(0.99, float(scores.get("task_3", 0.25))))),
            average=safe_score(max(0.01, min(0.99, float(average_score or 0.25))))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
