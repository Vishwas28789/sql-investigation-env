---
title: SQL Investigation Environment
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# 🔍 SQL Investigation Environment

> **An OpenEnv RL environment that trains AI agents to debug and fix SQL queries through pure execution-based reward signals — no LLM judge, no subjectivity, no external dependencies.**

[![HuggingFace](https://img.shields.io/badge/🤗%20HuggingFace-Live%20Demo-blue)](https://vishwas004-sql-investigation-env.hf.space)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black)](https://github.com/Vishwas28789/sql-investigation-env)
[![Built For](https://img.shields.io/badge/Built%20for-Meta%20×%20PyTorch%20×%20SST%20OpenEnv%20Hackathon-orange)](https://huggingface.co/spaces/Vishwas004/sql-investigation-env)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-green)](https://github.com/meta-pytorch/OpenEnv)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🧠 Why This Exists

Every data engineer, analyst, and ML researcher writes SQL. And every single one of them has spent hours — sometimes days — debugging a query that runs but returns completely wrong results. Wrong JOIN column. Missing HAVING clause. Bad GROUP BY scope. These are not beginner mistakes. They are the daily reality of working with data at scale.

**No RL environment has ever targeted this problem.**

The entire OpenEnv catalog — games, code execution, browser tasks, calendar management — had zero representation of SQL debugging. A problem that costs engineering teams millions of hours annually, that every developer hits daily, that has no deterministic automated solution.

This environment fills that gap. An AI agent receives a broken SQL query, a real database schema, and a natural language business question. It must figure out what is wrong, fix it, and prove correctness by execution — not by guessing, not by string matching, but by actually running the query and comparing real results.

The reward signal is execution-based, deterministic, and reproducible. No LLM judge. No subjectivity. No external API calls. Just Python, SQLite, and mathematics.

---

## ⚡ Live Demo

**Try it right now:** [https://vishwas004-sql-investigation-env.hf.space](https://vishwas004-sql-investigation-env.hf.space)

The web UI lets you select tasks, write SQL queries, and see live execution feedback with reward scores. The full API is also exposed for agent interaction.

```bash
# Health check — confirm space is running
curl https://vishwas004-sql-investigation-env.hf.space/health

# Start an episode on Task 1 (Syntax Repair)
curl -X POST https://vishwas004-sql-investigation-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": 1}'

# Submit a SQL query and receive reward
curl -X POST https://vishwas004-sql-investigation-env.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT country, COUNT(*) as total_orders FROM customers JOIN orders ON customers.id = orders.customer_id GROUP BY country",
    "task_id": 1
  }'

# Grade a query directly without stepping
curl -X POST https://vishwas004-sql-investigation-env.hf.space/grader \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT country, COUNT(*) FROM customers JOIN orders ON customers.id = orders.customer_id GROUP BY country", "task_id": 1}'

# Run baseline evaluation across all 3 tasks
curl -X POST https://vishwas004-sql-investigation-env.hf.space/baseline
```

---

## 🏗️ Environment Architecture

This environment follows the full OpenEnv specification. Three layers work together:
Agent
│
▼
FastAPI Server (HTTP endpoints)
│
▼
SQLInvestigationEnvironment (reset / step / state)
│
▼
DatabaseManager (SQLite in-memory, task-specific schema)
│
▼
Grader (execution-based, deterministic reward)

Each task runs in a completely isolated environment with its own database schema. Task 1, Task 2, and Task 3 have different table structures, different column names, and different data. An agent that memorizes Task 1 will fail Task 2. Generalization is required.

---

## 🎯 The Three Tasks

### Task 1 — Syntax Repair (🟢 Easy)
**Business Question:** Find the total number of orders per country

The broken query has a missing comma between column names in the SELECT clause — the most common SQL syntax error in production code. The agent must identify the punctuation error and produce a query that correctly groups orders by customer country.

**Schema:** `customers(id, name, email, country)` + `orders(id, customer_id, amount, status, created_date)`

**What's broken:** `SELECT country COUNT(*) FROM ...` — missing comma after `country`

---

### Task 2 — Logic Fix (🟡 Medium)
**Business Question:** Find the top 5 customers by total spending

The broken query has a wrong JOIN condition — it joins orders to customers using the order ID instead of the customer ID. The query runs without error but returns completely wrong results. This is the hardest class of SQL bugs to catch because there is no error message — just silently wrong data.

**Schema:** `customers(cust_id, customer_name, email, signup_date)` + `orders(order_id, cust_id, order_amount, order_status, order_date)`

**What's broken:** `JOIN orders ON customers.cust_id = orders.order_id` — should be `orders.cust_id`

---

### Task 3 — Business Investigation (🔴 Hard)
**Business Question:** Find product categories where average order value exceeds 100 and at least 3 orders were placed

The broken query has two simultaneous issues: wrong GROUP BY column (groups by product ID instead of category) and a completely missing HAVING clause. The agent must understand the business question deeply enough to realize that category-level aggregation with minimum order count filtering requires both fixes together.

**Schema:** `products(product_id, product_name, product_category, unit_price)` + `orders(order_id, customer_id, total_amount, order_status, order_date)` + `order_items(item_id, order_id, product_id, quantity, line_total)`

**What's broken:** Wrong GROUP BY column + no HAVING clause for business filters

---

## 📐 Observation Space

What the agent receives after each step:

| Field | Type | Description |
|-------|------|-------------|
| `schema_info` | string | Complete database schema — all tables, all columns, all types |
| `business_question` | string | Natural language description of what the query must answer |
| `query_result` | string | Formatted table of actual execution output, or error message |
| `error_message` | string | SQL error details if execution failed — empty string on success |
| `reward` | float | Scalar reward for this step, strictly between 0.01 and 0.99 |
| `done` | boolean | True when episode is complete — correct answer or max steps reached |
| `feedback` | string | Human-readable correctness feedback for debugging |

---

## ⚙️ Action Space

What the agent sends to take a step:

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | SQL query to execute against the task-specific database |
| `task_id` | integer | Task identifier — 1, 2, or 3 |

---

## 📊 Reward Function

The reward function is designed to provide dense, informative signal across the entire trajectory — not just binary success or failure at the end.
reward = (match_ratio × 0.8) + 0.2_base - (0.01 × step_count)

| Condition | Reward |
|-----------|--------|
| Exact result match — 100% rows correct | **0.99** |
| Greater than 80% rows match expected output | **0.75** |
| Partial match — some rows correct | **0.45** |
| Query executes but returns wrong results | **0.25** |
| Query fails with SQL error | **0.01** |
| Per-step time penalty | **−0.01 × step_count** |

**Why the 0.25 floor matters for RL:** Any query that executes without error gets at least 0.25. This means the agent always has gradient signal, even when it produces completely wrong results. The sparse reward problem — where the agent wanders randomly because it never gets positive signal — is eliminated by design.

**Why the step penalty matters:** The agent is incentivized to reach the correct answer in fewer steps. A perfect answer on step 1 scores 0.99. A perfect answer on step 5 scores 0.94. Efficiency is rewarded.

**Why 0.99 instead of 1.0:** Scores are strictly bounded between 0.01 and 0.99, never exactly 0.0 or 1.0. This is intentional — it maintains a continuous reward signal and avoids degenerate policy behavior at the boundaries.

---

## 🔬 Grader Design

The grader is the technical core of this environment. It solves a problem that most SQL evaluation systems get wrong: **it compares result sets, not query strings.**

Two completely different SQL queries that return the same rows receive the same score. This is the only correct way to evaluate SQL — the same business question can be answered by dozens of syntactically different queries.

### Technical Implementation

```python
# Execute both queries against the live database
user_rows, user_error = db.execute_query(agent_query)
expected_rows, _ = db.execute_query(reference_query)

# Normalize for robust comparison
user_normalized = normalize_rows(user_rows)    # sort, round floats, handle nulls
expected_normalized = normalize_rows(expected_rows)

# Set-based comparison — order independent
user_set = set(user_normalized)
expected_set = set(expected_normalized)

# Calculate match ratio for partial credit
match_ratio = len(user_set & expected_set) / len(expected_set)
```

### Normalization Rules

- **Order-independent:** Rows are sorted before comparison. `SELECT * FROM t ORDER BY id` and `SELECT * FROM t` score identically if data matches
- **Float-tolerant:** All numeric values normalized to 2 decimal places before comparison — eliminates floating point precision artifacts
- **NULL-consistent:** Python `None` values mapped to string `"NULL"` before hashing
- **Deterministic:** Given identical input, output is always identical. No randomness anywhere in the pipeline

### Why Not an LLM Judge?

LLM judges introduce three problems: cost (API call per evaluation), latency (seconds per step), and non-determinism (same query can score differently on different calls). This grader has zero API calls, sub-millisecond evaluation, and perfect reproducibility. It scales to millions of training steps without budget concerns.

---

## 📈 Baseline Scores

Baseline evaluation uses the broken query from each task — the query with the intentional bug — as the agent's submission. This establishes the floor that any trained agent must exceed.

| Task | Broken Query Score | Qwen/Qwen2.5-72B Zero-Shot | Qwen/Qwen2.5-72B + Context |
|------|-------------------|---------------------------|---------------------------|
| Task 1 — Syntax Repair | 0.01 | **0.99** | **0.99** |
| Task 2 — JOIN Logic Fix | 0.01 | **0.99** | **0.99** |
| Task 3 — Aggregation + HAVING | 0.01 | **0.99** | **0.99** |
| **Average** | **0.01** | **0.99** | **0.99** |

Qwen2.5-72B solves all three tasks in a single step with 99% reward in zero-shot setting. The environment is calibrated to challenge smaller, trainable models where the training signal between 0.01 and 0.99 drives genuine learning.

---

## 🚀 Complete API Reference

| Endpoint | Method | Input Body | Output | Purpose |
|----------|--------|-----------|--------|---------|
| `/health` | GET | — | `{"status": "ok"}` | Liveness check |
| `/reset` | POST | `{"task_id": int}` | Full observation object | Initialize new episode |
| `/step` | POST | `{"query": str, "task_id": int}` | `{observation, reward, done, info}` | Execute query, get reward |
| `/grader` | POST | `{"query": str, "task_id": int}` | `{score, feedback}` | Score without stepping |
| `/baseline` | POST | — | `{task_1, task_2, task_3, average}` | Evaluate all broken queries |
| `/tasks` | GET | — | `{tasks: [...], action_schema}` | List tasks and schema |
| `/state` | GET | — | Current `SQLState` object | Get episode metadata |

---

## 🐳 Local Setup

### Python (Development)

```bash
git clone https://github.com/Vishwas28789/sql-investigation-env
cd sql-investigation-env

pip install fastapi uvicorn pydantic openai requests aiofiles

uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload
```

Open `http://localhost:7860` for the interactive UI.

### Docker (Production)

```bash
docker build -t sql-investigation-env .
docker run -p 7860:7860 sql-investigation-env
```

---

## 🤖 Running Inference

```bash
export HF_TOKEN=your_huggingface_token
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export ENV_BASE_URL=https://vishwas004-sql-investigation-env.hf.space

# Run all 3 tasks
python inference.py

# Run specific task with custom steps
python inference.py --task-id 1 --max-steps 5
```

The inference script uses the OpenAI-compatible HuggingFace router. Any model accessible via `https://router.huggingface.co/v1` works as a drop-in replacement.

### Expected Output Format
[START] task=Find the total number of orders per country env=sql-investigation-env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT country, COUNT(*) as total_orders FROM customers JOIN orders ON customers.id = orders.customer_id GROUP BY country reward=0.99 done=true error=null
[END] success=true steps=1 rewards=0.99

---

## 🎓 Training with GRPO

This environment integrates directly with TRL's GRPO trainer for reinforcement learning from execution feedback:

```python
import requests
from trl import GRPOTrainer, GRPOConfig
from transformers import AutoModelForCausalLM, AutoTokenizer

ENV_URL = "https://vishwas004-sql-investigation-env.hf.space"

def get_reward(query, task_id):
    response = requests.post(f"{ENV_URL}/grader", json={
        "query": query,
        "task_id": task_id
    })
    return response.json()["score"]

# Environment interaction loop
for episode in range(num_episodes):
    obs = requests.post(f"{ENV_URL}/reset", json={"task_id": 1}).json()
    schema = obs["schema_info"]
    question = obs["business_question"]

    for step in range(max_steps):
        # Agent generates SQL from observation
        query = model.generate(prompt=f"Schema: {schema}\nQuestion: {question}\nSQL:")

        # Environment executes and returns reward
        result = requests.post(f"{ENV_URL}/step", json={
            "query": query,
            "task_id": 1
        }).json()

        reward = result["reward"]
        done = result["done"]

        if done:
            break
```

The smooth reward curve (0.25 floor for any executable query) provides robust policy gradients even in early training when the agent produces mostly wrong but syntactically valid SQL.

---

## 📁 Project Structure
sql-investigation-env/
├── inference.py          # OpenEnv-compliant inference script
├── models.py             # Pydantic models: SQLAction, SQLObservation, SQLState
├── environment.py        # Core RL environment: reset(), step(), state()
├── db.py                 # DatabaseManager: SQLite in-memory, task schemas
├── tasks.py              # Task definitions: broken queries, expected queries, hints
├── grader.py             # Execution-based deterministic grader
├── openenv.yaml          # OpenEnv specification manifest
├── Dockerfile            # Container definition for HuggingFace Spaces
├── pyproject.toml        # Python project dependencies
├── README.md             # This file
└── server/
├── app.py            # FastAPI application: all HTTP endpoints
└── static/
└── index.html    # Web UI for interactive testing

---

## 🏆 What Makes This Stand Out

**Novel domain.** No SQL debugging environment exists anywhere in the OpenEnv catalog. This is not a variation of an existing idea — it is a new category.

**Execution-based grading.** The grader compares actual query results, not query text. This is the technically correct approach that most SQL evaluation systems avoid because it is harder to implement. It is the only approach that correctly handles semantically equivalent queries.

**Deterministic and reproducible.** Every score can be independently verified. Run the same query twice, get the same score. Run it on any machine, get the same score. No external dependencies, no API calls, no randomness.

**Dense reward signal.** The 0.25 floor for executable queries eliminates the sparse reward problem that makes SQL tasks notoriously hard to train on. Every step provides learning signal.

**Task-specific schemas.** Each of the three tasks has a different database structure. Agents must generalize — they cannot memorize schema-specific heuristics from one task and apply them to another.

**Real-world utility.** SQL debugging is not a toy problem invented for benchmarking. It is what developers do every day, what costs real engineering time, and what a trained agent could genuinely help with in production.

---

## 👤 Author

**Vishwas Mangapatnam**
Built for the Meta × PyTorch × Scaler School of Technology OpenEnv Hackathon — Round 1

- GitHub: [Vishwas28789](https://github.com/Vishwas28789)
- HuggingFace: [Vishwas004](https://huggingface.co/Vishwas004)
- Live Environment: [sql-investigation-env](https://vishwas004-sql-investigation-env.hf.space)

---

## 📄 License

MIT License — free to use, modify, and distribute with attribution.

---

*Built with FastAPI · SQLite · Pydantic · HuggingFace Spaces · OpenEnv*
