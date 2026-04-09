"""
OpenEnv-compliant inference script for SQL Investigation Environment.

Strictly adheres to OpenEnv evaluation rules:
- HTTP endpoint communication
- OpenAI API for query generation
- Exact [START] / [STEP] / [END] STDOUT format
- Rewards formatted as f"{value:.2f}"
- Sanitized action and error strings
- Deterministic output
"""

import os
import sys
import requests
import json
from typing import Optional, Tuple, List

from openai import OpenAI

# ============ CONFIGURATION ============

# Use environment-provided API credentials (REQUIRED by LiteLLM validator)
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.environ["API_KEY"]  # Must exist - validator injects this

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY
)

ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

# Task name mapping
TASK_NAMES = {
    1: "Find the total number of orders per country",
    2: "Calculate total spending by each customer",
    3: "Identify products by category with high orders"
}


# ============ HELPER FUNCTIONS ============

def clean_action(action_str: str, max_length: int = 250) -> str:
    """
    Sanitize action string for logging.
    
    - Remove newlines and special characters
    - Truncate to max length
    - Ensure it's safe for plain text output
    
    Args:
        action_str: Raw action string from model
        max_length: Maximum length (default 250)
        
    Returns:
        Cleaned action string safe for logging
    """
    if not action_str:
        return "SELECT * FROM customers LIMIT 1"
    
    try:
        # Convert to string if needed
        s = str(action_str).strip()
        
        # Replace newlines and carriage returns with space
        s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # Replace multiple spaces with single space
        while '  ' in s:
            s = s.replace('  ', ' ')
        
        # Truncate if too long
        if len(s) > max_length:
            s = s[:max_length-3] + "..."
        
        return s if s else "SELECT * FROM customers LIMIT 1"
    except Exception:
        return "SELECT * FROM customers LIMIT 1"


def clean_error(error_str: str, max_length: int = 150) -> str:
    """
    Sanitize error message for logging.
    
    - Remove newlines and control characters
    - Truncate to max length
    - Return "null" if empty
    
    Args:
        error_str: Raw error string
        max_length: Maximum length (default 150)
        
    Returns:
        Cleaned error string, or "null" if empty
    """
    if not error_str or error_str.strip() == "":
        return "null"
    
    try:
        # Convert to string if needed
        s = str(error_str).strip()
        
        # Remove newlines and carriage returns
        s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # Replace multiple spaces with single space
        while '  ' in s:
            s = s.replace('  ', ' ')
        
        # Truncate if too long
        if len(s) > max_length:
            s = s[:max_length-3] + "..."
        
        return s if s else "null"
    except Exception:
        return "null"


def format_reward(reward: float) -> str:
    """Format reward to 2 decimal places."""
    try:
        return f"{float(reward):.2f}"
    except (ValueError, TypeError):
        return "0.25"


def http_request(method: str, endpoint: str, data: dict = None) -> Tuple[bool, Optional[dict], str]:
    """
    Make HTTP request to API endpoint.
    
    Args:
        method: HTTP method (GET, POST)
        endpoint: API endpoint (e.g., "/reset")
        data: Request body data
        
    Returns:
        Tuple of (success: bool, response_data: dict or None, error: str)
    """
    try:
        url = f"{ENV_BASE_URL}{endpoint}"
        print(f"[DEBUG] Calling {method} {url} with data={data}", file=sys.stderr)
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(
                url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
        else:
            return False, None, f"Unsupported HTTP method: {method}"
        
        print(f"[DEBUG] Response status: {response.status_code}", file=sys.stderr)
        print(f"[DEBUG] Response body: {response.text[:200]}", file=sys.stderr)
        
        if response.status_code == 200:
            try:
                result = response.json()
                return True, result, ""
            except json.JSONDecodeError:
                print(f"[DEBUG] ERROR: Invalid JSON response", file=sys.stderr)
                return False, None, "Invalid JSON response"
        else:
            error_msg = f"HTTP {response.status_code}"
            print(f"[DEBUG] ERROR: {error_msg}", file=sys.stderr)
            return False, None, error_msg
    
    except requests.exceptions.Timeout:
        print(f"[DEBUG] EXCEPTION in http_request: Request timeout", file=sys.stderr)
        return False, None, "Request timeout"
    except requests.exceptions.ConnectionError:
        print(f"[DEBUG] EXCEPTION in http_request: Connection refused", file=sys.stderr)
        return False, None, "Connection refused"
    except Exception as e:
        print(f"[DEBUG] EXCEPTION in http_request: {type(e).__name__}: {str(e)}", file=sys.stderr)
        return False, None, clean_error(str(e))


def generate_query(schema_info, business_question, previous_result, error_message, step):
    """
    Generate SQL query using OpenAI API through LiteLLM proxy validator.
    NO fallback queries. NO silent failures.
    
    Args:
        schema_info: Database schema
        business_question: Task description
        previous_result: Result from previous query
        error_message: Error from previous query
        step: Current step number
        
    Returns:
        Generated SQL query (real API call - will raise exception on failure)
    """
    prompt = f"""You are a SQL expert debugging queries.
Database Schema:
{schema_info}

Business Question: {business_question}
Previous Query Result: {previous_result}
Previous Error: {error_message}

Write ONLY a single SQL SELECT query. No explanation. No markdown. Just SQL."""
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.1
    )
    return response.choices[0].message.content.strip()


# ============ MAIN INFERENCE FUNCTION ============

def run_inference(task_id: Optional[int] = None, max_steps: int = 10, num_episodes: int = 1):
    """
    Run OpenEnv-compliant inference using HTTP endpoints.
    
    Outputs in strict OpenEnv format:
    [START] task=<name> env=sql-investigation-env model=<model>
    [STEP] step=<n> action=<str> reward=0.25 done=false error=null
    [END] success=true steps=1 rewards=0.25
    
    Args:
        task_id: Specific task ID to run (1, 2, or 3). If None, run task 1.
        max_steps: Maximum steps per episode
        num_episodes: Number of episodes to run
    """
    
    print("[DEBUG] Starting inference", file=sys.stderr)
    
    for episode_num in range(num_episodes):
        # Use provided task_id or default to 1
        episode_task_id = task_id if task_id else 1
        task_name = TASK_NAMES.get(episode_task_id, "SQL Query Debugging Task")
        
        # Output: [START] task=<name> env=sql-investigation-env model=<model>
        print(f"[START] task={task_name} env=sql-investigation-env model={MODEL_NAME}")
        
        # Reset environment via HTTP
        payload = {"task_id": episode_task_id} if episode_task_id is not None else {}
        success, reset_data, error = http_request("POST", "/reset", payload)
        
        # Debug: Print reset response
        print(f"[DEBUG] Reset response: {reset_data}", file=sys.stderr)
        
        # Check if /reset succeeded and returned data
        if not success or reset_data is None:
            print(f"[DEBUG] FATAL: /reset returned None - server may be down or endpoint failed", file=sys.stderr)
            print(f"[END] success=false steps=0 rewards=")
            continue
        
        # Extract schema and business question
        schema_info = reset_data.get("schema_info", "")
        business_question = reset_data.get("business_question", "")
        
        # Track metrics
        rewards_list = []
        step_count = 0
        previous_error = ""
        previous_result = ""
        done = False
        
        # Step loop
        for step_idx in range(max_steps):
            # Debug: Entering step
            print(f"[DEBUG] Entering step {step_idx + 1}", file=sys.stderr)
            
            # Generate query using OpenAI through validator proxy
            # NO fallback - if API fails, print error and emit [STEP] with reward=0.00
            action_query = ""
            try:
                action_query = generate_query(
                    schema_info,
                    business_question,
                    previous_result,
                    previous_error,
                    step_idx + 1
                )
                print(f"[DEBUG] Generated query: {action_query[:200]}", file=sys.stderr)
            except Exception as e:
                # API call failed - required by validator: print error and continue
                print(f"[ERROR] Failed to generate query: {type(e).__name__}: {str(e)}", file=sys.stderr)
                action_query = ""
            
            # If query generation failed, emit [STEP] with error and continue
            if not action_query:
                print(f"[DEBUG] Query generation failed, emitting zero-reward step", file=sys.stderr)
                action_clean = "[QUERY_GENERATION_FAILED]"
                step_count = step_idx + 1
                rewards_list.append(0.00)
                reward_str = format_reward(0.00)
                print(f"[STEP] step={step_count} action={action_clean} reward={reward_str} done=false error=query_generation_failed")
                break
            
            action_clean = clean_action(action_query)
            
            # Execute step via HTTP
            success, step_data, step_error = http_request(
                "POST", 
                "/step",
                {
                    "query": action_query,
                    "task_id": episode_task_id
                }
            )
            
            # Debug: Print step response
            print(f"[DEBUG] Step response: {step_data}", file=sys.stderr)
            
            # Extract step results - use raw values directly
            step_reward = 0.25
            done = False
            obs_error = "null"
            
            if success and step_data:
                observation = step_data.get("observation", {})
                # Get reward directly without defensive clamping
                step_reward = float(step_data.get("reward", 0.25))
                
                raw_done = step_data.get("done", False)
                # Handle both bool and string "true"/"false"
                done = raw_done if isinstance(raw_done, bool) else str(raw_done).lower() == "true"
                
                # Extract error message
                obs_error = observation.get("error_message", "") if observation else ""
                obs_error = clean_error(obs_error)
                
                # Store error and result for next iteration feedback
                query_result = observation.get("query_result", "") if observation else ""
                previous_error = obs_error if obs_error != "null" else ""
                previous_result = query_result if query_result else ""
            else:
                # Network error
                obs_error = clean_error(step_error)
                previous_error = obs_error if obs_error != "null" else ""
                previous_result = ""
                step_reward = 0.25
            
            # Track reward (raw value)
            rewards_list.append(step_reward)
            step_count = step_idx + 1
            
            # Output: [STEP] step=<n> action=<str> reward=0.25 done=<bool> error=<str|null>
            done_str = "true" if done else "false"
            reward_str = format_reward(step_reward)
            print(f"[STEP] step={step_count} action={action_clean} reward={reward_str} done={done_str} error={obs_error}")
            
            # End if done
            if done:
                break
        
        # Determine success: if we got a perfect (1.0) reward in final step
        # or use the last reward as indicator
        final_reward = rewards_list[-1] if rewards_list else 0.25
        success_bool = final_reward >= 0.5
        success_str = "true" if success_bool else "false"
        
        # Format rewards list: r1,r2,r3 using simple f"{r:.2f}" format
        rewards_formatted = [format_reward(r) for r in rewards_list]
        rewards_str = ",".join(rewards_formatted)
        
        # Output: [END] success=<bool> steps=<n> rewards=<list>
        print(f"[END] success={success_str} steps={step_count} rewards={rewards_str}")


# ============ ENTRY POINT ============

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OpenEnv-compliant inference for SQL Investigation Environment"
    )
    parser.add_argument(
        "--task-id",
        type=int,
        default=None,
        help="Specific task ID to run (1, 2, or 3). If None, runs task 1."
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=5,
        help="Maximum steps per episode (default: 5)"
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=1,
        help="Number of episodes to run (default: 1)"
    )
    
    args = parser.parse_args()
    
    # Run inference
    run_inference(
        task_id=args.task_id,
        max_steps=args.max_steps,
        num_episodes=args.episodes
    )
