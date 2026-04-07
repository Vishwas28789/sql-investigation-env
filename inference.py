"""
OpenEnv-compliant inference script for SQL Investigation Environment.

Strictly adheres to OpenEnv evaluation rules:
- HTTP endpoint communication
- OpenAI API for query generation
- Exact [START] / [STEP] / [END] STDOUT format
- No repr() calls
- Sanitized action and error strings
- Deterministic output
"""

import os
import sys
from pathlib import Path
import requests
import json
from typing import Optional, Tuple, List

# Try to import OpenAI client
try:
    from openai import OpenAI, APIError
except ImportError:
    OpenAI = None
    APIError = Exception


# ============ CONFIGURATION ============

# Environment Server URL (Localhost defaults to 7860 as per openenv.yaml entrypoint)
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

# Meta LLM Proxy - MANDATORY REQUIREMENTS
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "sql-agent")

# Initialize OpenAI client using environment variables
openai_client = None
api_status = "DISCONNECTED"

if API_BASE_URL and API_KEY:
    try:
        from openai import OpenAI
        openai_client = OpenAI(
            base_url=API_BASE_URL,
            api_key=API_KEY
        )
        api_status = "CONNECTED"
    except Exception as e:
        api_status = f"ERROR: {str(e)}"
else:
    api_status = "MISSING_ENV_VERS"
    openai_client = None

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
        return "0.00"


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


def generate_query_with_openai(task_desc: str, schema: str, previous_error: str = "", previous_result: str = "") -> str:
    """
    Generate SQL query using OpenAI API with HuggingFace router.
    
    Args:
        task_desc: Task description (business question)
        schema: Database schema info
        previous_error: Error message from previous attempt (if any)
        previous_result: Result from previous attempt (if any)
        
    Returns:
        Generated SQL query (from OpenAI) or fallback query on error
    """
    # Only use fallback if API is definitively unavailable
    if not openai_client:
        print(f"[DEBUG] OpenAI client not available, using fallback", file=sys.stderr)
        return "SELECT * FROM customers LIMIT 1"
    
    try:
        print(f"[DEBUG] Using MODEL_NAME: {MODEL_NAME}", file=sys.stderr)
        
        # Build prompt with feedback from previous attempts
        prompt = f"""You are an expert SQL engineer.

Given:

Database Schema:
{schema}

Business Question:
{task_desc}

Your Task:
Write the EXACT SQL query that correctly answers the business question.

Rules:
* Use correct JOIN conditions (match ON clauses carefully)
* Use correct GROUP BY when aggregating
* Use aggregation functions if needed (COUNT, SUM, AVG, MAX, MIN)
* Do NOT use SELECT * (be specific about columns)
* Do NOT use LIMIT unless explicitly required
* Return ONLY the SQL query, no explanation
* Remove any syntax errors or mistakes

"""
        
        # Add context from previous attempt if available
        if previous_error:
            prompt += f"Previous attempt error: {previous_error}\nFix this mistake in your next query.\n\n"
        if previous_result:
            prompt += f"Previous result was incomplete or incorrect.\nWrite a better query.\n\n"
        
        prompt += "Generate the SQL query:"
        
        print(f"[DEBUG] Calling HuggingFace API with model={MODEL_NAME}", file=sys.stderr)
        
        # Call HuggingFace API via OpenAI client with proper parameters
        response = openai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        )
        
        # Extract raw response
        raw_response = response.choices[0].message.content
        print(f"[DEBUG] Raw API response: {raw_response[:200]}", file=sys.stderr)
        
        # Process response
        query = raw_response.strip()
        
        # Clean up markdown code blocks if present
        if query.startswith("```"):
            lines = query.split("\n")
            # Find the content between the markdown code blocks
            content_lines = [line for line in lines[1:-1] if line.strip()]
            query = "\n".join(content_lines).strip()
        
        query = query.strip()
        
        print(f"[DEBUG] Processed query: {query[:200]}", file=sys.stderr)
        
        # Return the generated query only if it's valid
        if query and "SELECT" in query.upper():
            print(f"[DEBUG] Query valid, returning: {query[:100]}...", file=sys.stderr)
            return query
        else:
            # Invalid response from API - use fallback
            print(f"[DEBUG] Invalid query response (no SELECT found), using fallback", file=sys.stderr)
            return "SELECT * FROM customers LIMIT 1"
    
    except Exception as e:
        # API call failed - print exception clearly then use fallback
        print(f"[DEBUG] API Exception: {type(e).__name__}: {str(e)}", file=sys.stderr)
        return "SELECT * FROM customers LIMIT 1"


# ============ MAIN INFERENCE FUNCTION ============

def run_inference(task_id: Optional[int] = None, max_steps: int = 10, num_episodes: int = 1):
    """
    Run OpenEnv-compliant inference using HTTP endpoints.
    
    Outputs in strict OpenEnv format:
    [START] task=<name> env=sql-investigation-env model=<model>
    [STEP] step=<n> action=<str> reward=<0.00> done=<bool> error=<str|null>
    [END] success=<bool> steps=<n> rewards=<r1,r2,...>
    
    Args:
        task_id: Specific task ID to run (1, 2, or 3). If None, uses None.
        max_steps: Maximum steps per episode
        num_episodes: Number of episodes to run
    """
    
    # Debug: Print API status
    if api_status == "CONNECTED":
        print("[DEBUG] HF API Connected", file=sys.stderr)
    else:
        print(f"[DEBUG] API NOT CONNECTED ({api_status})", file=sys.stderr)
    
    # MANDATORY: Ping LiteLLM proxy for validation
    if openai_client:
        try:
            print("[DEBUG] Pinging LLM proxy for validation...", file=sys.stderr)
            openai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
        except Exception as e:
            print(f"[DEBUG] Ping failed: {str(e)}", file=sys.stderr)
    
    for episode_num in range(num_episodes):
        # Use first episode's task_id for the START line
        episode_task_id = task_id if task_id else 1
        task_name = TASK_NAMES.get(episode_task_id, "SQL Query Debugging Task")
        
        # Output: [START] task=<name> env=sql-investigation-env model=<model>
        print(f"[START] task={task_name} env=sql-investigation-env model={MODEL_NAME}")
        
        # Reset environment via HTTP with safe payload
        payload = {"task_id": task_id} if task_id is not None else {}
        success, reset_data, error = http_request("POST", "/reset", payload)
        
        # Debug: Print reset response
        print(f"[DEBUG] Reset response: {reset_data}", file=sys.stderr)
        print(f"[DEBUG] Done from reset: {reset_data.get('done', 'NOT FOUND') if reset_data else 'reset_data is None'}", file=sys.stderr)
        print(f"[DEBUG] Schema present: {bool(reset_data.get('schema_info', '') if reset_data else '')}", file=sys.stderr)
        
        # CRITICAL: Check if /reset succeeded and returned data
        if not success or reset_data is None:
            print(f"[DEBUG] FATAL: /reset returned None - server may be down or endpoint failed", file=sys.stderr)
            print(f"[END] success=false steps=0 rewards=")
            continue
        
        # Extract schema and business question
        schema_info = reset_data.get("observation", {}).get("schema_info", "")
        business_question = reset_data.get("observation", {}).get("business_question", "")
        episode_id = reset_data.get("episode_id", "unknown")
        
        # Track metrics
        rewards_list = []
        step_count = 0
        final_score = 0.0
        previous_error = ""
        previous_result = ""
        
        # Always start with done=False regardless of reset response
        done = False
        
        # Step loop
        for step_idx in range(max_steps):
            # Debug: Entering step
            print(f"[DEBUG] Entering step {step_idx + 1}", file=sys.stderr)
            
            # Generate query using OpenAI with feedback from previous attempts
            action_query = generate_query_with_openai(
                business_question, 
                schema_info,
                previous_error=previous_error,
                previous_result=previous_result
            )
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
            
            # Extract step results
            step_reward = 0.0
            done = False
            obs_error = "null"
            
            if success and step_data:
                observation = step_data.get("observation", {})
                step_reward = step_data.get("reward", 0.0)
                raw_done = step_data.get("done", False)
                # Handle both bool and string "true"/"false"
                done = raw_done if isinstance(raw_done, bool) else str(raw_done).lower() == "true"
                info = step_data.get("info", {})
                
                # Safe reward extraction
                try:
                    step_reward = float(step_reward) if step_reward is not None else 0.0
                except (ValueError, TypeError):
                    step_reward = 0.0
                
                # Extract score for success determination
                score = info.get("score", 0.0) if info else 0.0
                try:
                    final_score = float(score) if score is not None else 0.0
                except (ValueError, TypeError):
                    final_score = 0.0
                
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
            
            # Track reward
            rewards_list.append(step_reward)
            step_count = step_idx + 1
            
            # Output: [STEP] step=<n> action=<str> reward=<0.00> done=<bool> error=<str|null>
            done_str = "true" if done else "false"
            print(f"[STEP] step={step_count} action={action_clean} reward={format_reward(step_reward)} done={done_str} error={obs_error}")
            
            # End if done
            if done:
                break
        
        # Determine success: final_score >= 0.5
        success_bool = final_score >= 0.5
        success_str = "true" if success_bool else "false"
        
        # Format rewards list: r1,r2,r3
        rewards_str = ",".join(format_reward(r) for r in rewards_list)
        
        # Output: [END] success=<bool> steps=<n> score=<...> rewards=<list>
        print(f"[END] success={success_str} steps={step_count} score={format_reward(final_score)} rewards={rewards_str}")


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
        help="Specific task ID to run (1, 2, or 3). If None, runs all 3 tasks in sequence."
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
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="API base URL (default: http://localhost:7860)"
    )
    
    args = parser.parse_args()
    
    # Update API URL if specified
    if args.api_url:
        API_BASE_URL = args.api_url
    
    # If task_id is None, run all 3 tasks in sequence
    if args.task_id is None:
        for task_id in [1, 2, 3]:
            run_inference(
                task_id=task_id,
                max_steps=args.max_steps,
                num_episodes=args.episodes
            )
    else:
        # Run single task
        run_inference(
            task_id=args.task_id,
            max_steps=args.max_steps,
            num_episodes=args.episodes
        )
