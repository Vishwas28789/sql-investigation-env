---
title: SQL Investigation Environment
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

## Live Demo

HuggingFace Space:
https://vishwas004-sql-investigation-env.hf.space

This environment allows users to interactively debug SQL queries across multiple tasks and receive execution-based feedback.

---

## Project Overview

SQL Investigation Environment is an OpenEnv-compatible reinforcement learning environment designed to train agents to debug and correct SQL queries using execution-based reward signals.

The system provides:
- Task-specific database schemas
- Natural language business problems
- Deterministic grading based on query execution results
- Smooth reward signals for reinforcement learning

---

## Key Features

- Deterministic execution-based grading (no LLM dependency)
- Task isolation with independent schemas per task
- Partial reward system (0.2 to 1.0)
- Real-time SQL execution and feedback
- Fully reproducible evaluation environment

---

## Submission Details

This project is submitted as part of the OpenEnv Hackathon.

Repository:
https://github.com/Vishwas28789/sql-investigation-env

---



# SQL Investigation Environment

**SQL Investigation OpenEnv — An OpenEnv RL environment for training agents to debug and fix SQL queries through execution-based feedback.**

## Why This Matters

SQL errors cost engineering teams millions in debugging time annually. No existing OpenEnv environment targets structured query reasoning with execution-based feedback. This environment provides deterministic, reproducible reward signals independent of external LLMs—directly trainable with TRL, GRPO, or any policy gradient framework. Agents learn to navigate schema constraints, compose joins correctly, and derive business logic from natural language specifications.

## Environment Overview

**SQL Investigation** is a fixed-task RL environment with three difficulty-scaled SQL debugging challenges. Agents observe a database schema and natural language business question, then iteratively submit SQL queries. The environment executes each query against an in-memory SQLite database, compares results against ground truth (row-sorted, float-tolerant at 2 decimal places), and returns execution-based reward signals.

**Observation:** Schema information, business question, query execution result or error message, step count.

**Action:** SQL query string + task identifier.

**Reward Calculation:** Smooth curve: `0.2 + (match_ratio × 0.8) - extra_row_penalty`. Syntax errors yield 0.0; valid query execution with zero correct rows yields 0.2 minimum.

**Termination:** Episode ends when score ≥ 0.9 or max_steps (10) reached.

## Action Space

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | SQL query to execute against task-specific database |
| `task_id` | integer | Task identifier (1, 2, or 3) |

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `schema_info` | string | Database schema: CREATE TABLE statements with all columns |
| `business_question` | string | Natural language specification of task goal |
| `query_result` | string | Query execution output: formatted table or error message |
| `error_message` | string | SQL error details (empty string if successful execution) |
| `reward` | float | Scalar reward for current step |
| `done` | boolean | Episode termination flag |
| `feedback` | string | Textual correctness feedback for debugging |

## Reward Function

| Condition | Reward |
|-----------|--------|
| Exact result match (100% rows correct) | 1.0 |
| >80% rows match expected output | 0.8 - 0.88 |
| >50% rows match | 0.6 - 0.8 |
| Query executes, 0% rows match | 0.2 |
| Query fails: syntax error | 0.0 |
| Query fails: missing column | 0.0 |
| Query fails: type mismatch | 0.0 |
| Step penalty | -0.01 × step_count (cumulative) |

**Grader Details:** Comparison is order-independent; results sorted before matching. Float values normalized to 2 decimal places. Extra rows penalized proportionally to excess count.

## Tasks

| ID | Name | Difficulty | What Agent Must Fix |
|----|------|-----------|-------------|
| 1 | Syntax Repair | Easy | Missing punctuation in SELECT statement |
| 2 | Logic Fix | Medium | Incorrect JOIN condition (equating wrong columns) |
| 3 | Business Investigation | Hard | Missing GROUP BY columns + absent HAVING clause |

Each task provides a broken query, hint text, and expected result set for evaluation. Databases are task-specific; schema differs per task_id.

## Grader Design

**Execution-based comparison:** Compares result sets, not query syntax. Two queries returning identical rows receive identical scores.

**Order-independent:** Sorts rows before comparison. `SELECT * FROM t ORDER BY id` and `SELECT * FROM t` score identically if result sets match.

**Float-tolerant:** Numeric columns normalized to 2 decimal places before comparison. Avoids floating-point precision artifacts.

**Deterministic:** Identical input query always produces identical output. No randomness in reward assignment or grading.

## Baseline Scores

| Task | Broken Query Score | Qwen 72B Zero-Shot | Qwen 72B + Context |
|------|-------------------|-------------------|-------------------|
| Task 1 (Syntax) | 0.00 | 0.99 | 0.99 |
| Task 2 (JOIN Logic) | 0.00 | 0.99 | 0.99 |
| Task 3 (Aggregation) | 0.00 | 0.99 | 0.99 |
| Average | 0.00 | 0.99 | 0.99 |

## Quick Start

### Docker Deployment

```bash
docker pull vishwas004/sql-investigation-env
docker run -p 7860:7860 vishwas004/sql-investigation-env
```

### Reset Environment

```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": 1}'
```

### Execute Query

```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT COUNT(*) FROM orders",
    "task_id": 1
  }'
```

## API Reference

| Endpoint | Method | Input | Output | Purpose |
|----------|--------|-------|--------|---------|
| `/reset` | POST | `{"task_id": int}` | `{observation, episode_id}` | Initialize episode |
| `/step` | POST | `{"query": string, "task_id": int}` | `{observation, reward, done, info}` | Execute query step |
| `/grader` | POST | `{"query": string, "task_id": int}` | `{score, feedback}` | Score query without stepping |
| `/baseline` | POST | — | `{task_1, task_2, task_3, average}` | Evaluate all broken queries |
| `/state` | GET | — | `{schema_info, business_question, ...}` | Get current state |
| `/tasks` | GET | — | `{tasks: [...], action_schema}` | List all available tasks |
| `/health` | GET | — | `{status: "ok"}` | Health check |

## Training with GRPO

Integrate this environment with TRL's GRPO trainer for policy optimization:

```python
from trl import GRPOTrainer, GRPOConfig
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "Qwen/Qwen2.5-72B-Instruct"
model = AutoModelForCausalLM.from_pretrained(model_id)
tokenizer = AutoTokenizer.from_pretrained(model_id)

config = GRPOConfig(
    output_dir="./sql-grpo-results",
    num_train_episodes=1000,
    max_episode_length=10,
    learning_rate=1e-5,
)

trainer = GRPOTrainer(
    model=model,
    tokenizer=tokenizer,
    args=config,
    eval_strategy="steps",
)

# Environment interaction loop
task_id = 1
observation = env.reset(task_id=task_id)

for step in range(max_steps):
    # Agent generates SQL query from observation
    query = model.generate(prompt=observation.schema_info + "\n" + observation.business_question)
    
    # Environment executes and returns reward
    observation, reward, done, info = env.step(query=query, task_id=task_id)
    
    if done:
        break

trainer.train()
```

Smooth reward curve enables robust policy gradients: partial progress (0.2 floor) provides learning signal even for failed attempts.

## Why This Is Novel

**No Prior SQL Environment in OpenEnv Catalog:** Existing SQL systems focus on generation benchmarks; none offer RL training with execution-based reward.

**Execution-Based Reward (Not LLM Judge):** Deterministic, reproducible scoring. No external API calls. Training cost is database execution time, not LLM inference.

**Natural Difficulty Progression:** Task 1 requires syntax understanding. Task 2 demands logical composition. Task 3 requires semantic reasoning about business intent. Suitable for curriculum learning.

**Task-Specific Schemas:** Each task has independent database structure. Agents cannot memorize. Generalization is required.

**SQLite In-Memory:** Zero external dependencies. Runs on laptop, cloud, or air-gapped environment. No Docker registry required for research reproducibility.
