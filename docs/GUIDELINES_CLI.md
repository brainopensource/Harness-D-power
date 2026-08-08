---
status: rationale
updated: 2026-08-08
---

# AETHER CLI & Orchestration Guidelines

Welcome to the **AETHER Autonomous Coding Agent Harness & Orchestrator**. This guide provides a high-level, beginner-friendly introduction to the system architecture, capabilities, CLI tools, workflow topologies, provider configurations (Local Ollama vs. Paid Cloud LLMs), and instructions on how to inspect SQLite trajectory logs and trace every execution step.

---

## 1. High-Level System Architecture

AETHER is a SOTA autonomous coding agent harness designed around capability security, a microkernel dispatch choke point, declarative workflow topologies, and deterministic evaluation gates.

AETHER has no CLI of its own yet (only the Python `engine.run()` API and ad-hoc
scripts — see §4). The `sagiha` command that exists in this repo belongs to
`src/sagiha/`, a separate, retiring predecessor project (`AGENTS.md`); its
`RunLoop` does **not** call `aether.engine` and is not part of this diagram.

```
                  +-----------------------------------+
                  |   Client Script (scripts/*.py)    |
                  |  or a direct engine.run() call    |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------+-----------------+
                  |          aether.engine            |
                  |      (Headless Engine API)        |
                  +-----------------+-----------------+
                                    |
        +---------------------------+---------------------------+
        |                           |                           |
        v                           v                           v
+---------------+           +---------------+           +---------------+
| aether.kernel |           |aether.workflow|           |aether.adapters|
| (Dispatch,    |           | (Executor &   |           | (Ollama/LLM,  |
|  Bus, Policy, |           |  Topologies)  |           |  Workspace,   |
|  Governor)    |           +---------------+           |  Sqlite DB)   |
+---------------+                                       +---------------+
```

### Core Architecture Components

1. **Capability Authorization (CAR Model)**:
   - All tool executions, LLM completions, and workspace mutations pass through `PolicyEngine.authorize()`.
   - The kernel choke point (`aether.kernel.dispatch`) enforces verification right before side-effects are performed: `authorize → verify grant → acquire lease → dispatch → release`.
2. **Ports & Adapters Architecture**:
   - `aether.domain`: Pure Pydantic models with zero I/O side effects (Task, Budget, Events, GateReport, etc.).
   - `aether.ports`: Typed Python `Protocol` definitions (Evaluator, ModelProvider, TrajectoryStore, Workspace, etc.).
   - `aether.adapters`: Wire implementations (OpenAI-compatible LLM provider, Podman/subprocess sandbox, Git CLI workspace, SQLite trajectory store).
3. **Declarative Workflow Topologies**:
   - Workflows are defined as YAML DAGs under `workflows/`.
   - Steps (`retrieve`, `architect`, `generate`, `apply`, `evaluate`, `repair`, `reflector`) are plugged together at composition time without hardcoding control flow into python logic.
4. **Verification Gates & Replayability**:
   - Gate verdicts (`PASSED`, `FAILED`, `NONE`) grade candidate patches by executing test suites (`test_command`).
   - The system enforces the **`tests_unmodified` (I7)** rule: an agent modifying code cannot modify the tests grading it.
   - All events are recorded in an append-only SQLite trajectory database for complete inspection, auditability, and replay.

---

## 2. Inputs, Workflows & Outputs

### Task Inputs

A coding task is represented by the `Task` domain model (`aether.domain.task.Task`). Key fields include:
- `task_id`: Unique identifier for the task.
- `repo`: Path to the git repository workspace.
- `base_commit`: The git commit SHA from which the agent's worktree is checked out.
- `instructions`: The user prompt or feature specification (e.g. *"Create main.py that prints the sum of two numbers"*).
- `test_command_hash`: Hash of the test command used for evaluation gate checks.

### Declarative Workflows (Topologies)

Workflows are specified in YAML files under `workflows/`:

- **Simple Linear Workflow (`workflows/linear_v1.yaml`)**:
  - `retrieve` → `generate` → `apply` → `evaluate`
  - Retrieves entry context, queries the LLM for a patch, applies the patch to the git worktree, and runs the evaluation gate.
- **Iterative Self-Repair Workflow (`workflows/linear_repair_v1.yaml`)**:
  - `retrieve` → `generate` → `apply` → `evaluate` → [if failed] → `repair` → `apply` → `evaluate` (up to N iterations).
  - Automatically feeds test failure tracebacks back into the `repair` step for self-healing bug fixes.
- **Small-Model Repair Workflow (`workflows/linear_repair_small_model_v1.yaml`)**:
  - `retrieve` → `generate` → `apply` → `evaluate` → [if failed] → `repair` → `apply` → `evaluate` (up to 3 repair iterations).
  - Explicitly optimized for local small models (`1.5B–3B`, e.g. `qwen2.5:1.5b`, `llama3.2:3b`). Configured with `whole_file_codeblock` edit format, tighter token ceilings, and Tier 1/2 parser format tolerance.

### Outputs & Gate Reports

A execution run returns a `RunResult` (`aether.engine.RunResult`) containing:
- `run_id`: Unique execution run identifier (e.g. `run-a1b2c3d4e5f6`).
- `gate_report`: `GateReport` object with `status` (`PASSED`, `FAILED`, `NONE`) and `admitted` boolean.
- `usage`: `BudgetDims` object tracking precise resource consumption (USD micro-dollars spent, prompt tokens, completion tokens, wall-clock time).

---

## 3. Configuring LLM Providers (Local vs. Cloud)

AETHER connects to LLMs using an OpenAI-compatible HTTP interface via `OpenAICompatibleProvider`.

### Local LLMs (Ollama with DeepSeek / Qwen on WSL2 & Windows 11)

When running Ollama natively on Windows 11 with WSL2 Ubuntu as host:

1. **Ollama Default Port**: `11434`
2. **Accessing Windows Ollama from WSL2**:
   - If Ollama is listening on `localhost:11434` or `0.0.0.0:11434`, use base URL `http://localhost:11434/v1` or `http://127.0.0.1:11434/v1`.
   - If using the WSL2 host bridge IP: `http://<WINDOWS_HOST_IP>:11434/v1`.
3. **Recommended Local Models**:
   - Small models (1.5B–3B): `qwen2.5:1.5b` or `llama3.2:3b` (use with `workflows/linear_repair_small_model_v1.yaml` for Sprint 5 Tier 1/2 format compliance).
   - Medium/Large local models: `deepseek-r1:8b`, `deepseek-r1:14b`, `qwen2.5-coder:7b`, or `qwen3.6:27b`.

### Paid / Cloud LLMs (OpenAI, OpenRouter, DeepSeek Cloud)

To use cloud provider endpoints:

- **OpenRouter**:
  - `base_url`: `https://openrouter.ai/api/v1`
  - `model_api_key`: Env variable `OPENROUTER_API_KEY` (loaded automatically from `.env`)
  - **Verified Free Models**:
    1. `openrouter/free`
    2. `inclusionai/ling-3.0-tiny:free`
    3. `poolside/laguna-s-2.1:free`
    4. `cohere/north-mini-code:free`
    5. `google/gemma-4-26b-a4b-it:free`
    6. `nvidia/nemotron-3-super-120b-a12b:free`
    7. `openai/gpt-oss-20b:free`
  - **Verified Low-Cost Paid Models**:
    8. `deepseek/deepseek-v4-flash`
    9. `xiaomi/mimo-v2.5`
  - **Frontier Cloud Models**: `z-ai/glm-5.2`, `openai/gpt-5.6-luna`, `deepseek/deepseek-v4-pro`, `minimax/minimax-m3`
- **DeepSeek API**:
  - `base_url`: `https://api.deepseek.com/v1`
  - `model_name`: `deepseek-reasoner` or `deepseek-coder`
  - `model_api_key`: Env variable `DEEPSEEK_API_KEY`
- **OpenAI**:
  - `base_url`: `https://api.openai.com/v1`
  - `model_name`: `gpt-4o`
  - `model_api_key`: Env variable `OPENAI_API_KEY`

---

## 4. Running AETHER Today

**AETHER has no console-script CLI yet.** `sagiha run` / `sagiha replay` are
real commands, but they belong to `src/sagiha/` — a separate, retiring
predecessor codebase (`AGENTS.md`) with its own kernel and run loop. They do
not call `aether.engine`, do not exercise anything under `src/aether/`, and a
`sagiha run` invocation proves nothing about AETHER. (`TASK-058` and
`TASK-075` in `docs/agile/backlog.md` scope AETHER's own client; until they
land, use one of the two options below.)

### Option A: `scripts/run_aether_task.py` — generic ad-hoc runner

Wraps `aether.engine.run()` with real CLI flags for an arbitrary goal, entry
file(s), and test command — the closest thing to a CLI AETHER has today:

```bash
uv run python3 scripts/run_aether_task.py \
  --workspace swe_tasks/my_task \
  --entry-file main.py \
  --instructions "Write is_even(n: int) -> bool in main.py returning True if n is even." \
  --test-file run_tests.py \
  --test-code "import main; assert main.is_even(4) is True; print('PASSED')" \
  --model qwen2.5:1.5b \
  --base-url http://127.0.0.1:11434/v1 \
  --topology workflows/linear_repair_small_model_v1.yaml
```

### Option B: Call `aether.engine.run()` directly from a script

For full control, invoke the headless engine API yourself — see the tutorials
in §6. `scripts/run_aether_demo.py` is a minimal worked example.

---

## 5. Tracing Trajectory SQLite DB Logs & Event Steps

All events generated during execution are streamed over `EventBus` and saved into SQLite via `SqliteTrajectoryStore`.

### Trajectory Table Schema (`stored_events`)

| Column | Type | Description |
| :--- | :--- | :--- |
| `seq` | `INTEGER` | Monotonically increasing event sequence number for the run |
| `run_id` | `TEXT` | Unique ID of the execution run |
| `event_type` | `TEXT` | Event name (e.g., `run_started`, `node_started`, `effect_dispatched`, `gate_report_emitted`, `run_completed`) |
| `payload_json` | `TEXT` | JSON payload of the domain event |
| `at` | `TEXT` | ISO-8601 UTC timestamp |

### Lifecycle Event Flow

```
[run_started]
     |
     v
[node_started: retrieve] ---> [effect_dispatched: file_read] ---> [node_completed: retrieve]
     |
     v
[node_started: generate] ---> [effect_dispatched: llm_completion] ---> [node_completed: generate]
     |
     v
[node_started: apply]    ---> [effect_dispatched: apply_patch] ---> [node_completed: apply]
     |
     v
[node_started: evaluate] ---> [effect_dispatched: exec_test] ---> [gate_report_emitted]
     |
     v
[run_completed]
```

---

## 6. Practical Quick-Start Tutorials

### Tutorial 1: Local Ollama (DeepSeek R1 on WSL2 / Windows)

Below is a complete, runnable Python script template (`run_local_deepseek.py`) to create a simple Python file using a local Ollama LLM.

```python
#!/usr/bin/env python3
import asyncio
import os
import subprocess
import sys
from pathlib import Path

from aether import engine
from aether.domain.task import Task, TaskSource
from aether.measurement.evaluator import hash_command


def setup_target_repo(repo_dir: Path) -> str:
    """Initialize a git repository for the agent workspace."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Dev"], cwd=repo_dir, check=True)

    # Initial readme file
    (repo_dir / "README.md").write_text("# Target Python Workspace\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial commit"], cwd=repo_dir, check=True)

    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
    ).stdout.strip()
    return base_commit


async def main() -> None:
    workspace = Path("./workspace_demo").resolve()
    worktrees = Path("./worktrees_demo").resolve()
    db_path = Path("./trajectory_demo.db").resolve()

    base_commit = setup_target_repo(workspace)
    test_cmd = f'{sys.executable} -c "import main; print(\'Test OK\')"'

    task = Task(
        task_id="task-simple-sum-1",
        repo=str(workspace),
        base_commit=base_commit,
        instructions="Create a python file main.py that defines a variable a=5, b=7, and prints their sum (12).",
        environment_image_digest="sha256:" + "a" * 64,
        test_command_hash=hash_command(test_cmd),
        source=TaskSource(manifest_hash="sha256:" + "b" * 64, instance_id="demo-1"),
    )

    print("🚀 Starting AETHER Harness with local DeepSeek R1 on Ollama...")
    result = await engine.run(
        task,
        repo_path=str(workspace),
        worktrees_root=str(worktrees),
        topology_path="workflows/linear_v1.yaml",
        resolve_command=lambda spec: test_cmd,
        model_base_url="http://localhost:11434/v1",  # Local Ollama endpoint
        model_name="deepseek-r1:8b",
        trajectory_db_path=str(db_path),
        entry_file="README.md",
    )

    print("\n✅ Run Completed!")
    print(f"Run ID: {result.run_id}")
    print(f"Gate Status: {result.gate_report.status.value}")
    print(f"Gate Admitted: {result.gate_report.admitted}")
    print(f"Usage Ledger: {result.usage}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

### Tutorial 2: Paid / Cloud LLMs (OpenRouter / DeepSeek Cloud)

To run with OpenRouter or DeepSeek Cloud, supply your API key and base URL:

```python
result = await engine.run(
    task,
    repo_path=str(workspace),
    worktrees_root=str(worktrees),
    topology_path="workflows/linear_v1.yaml",
    resolve_command=lambda spec: test_cmd,
    model_base_url="https://openrouter.ai/api/v1",
    model_name="deepseek/deepseek-r1",
    model_api_key=os.getenv("OPENROUTER_API_KEY"),
    trajectory_db_path="./cloud_trajectory.db",
)
```

---

### Tutorial 3: Reading & Tracing Trajectory SQLite Logs

Use the following Python script (`inspect_trajectory.py`) to query SQLite DB logs and view every step, LLM completion delta, applied patch, and gate verdict:

```python
#!/usr/bin/env python3
import asyncio
import json
import sys
from pathlib import Path
from aether.adapters.trajectory_store.sqlite import SqliteTrajectoryStore

async def inspect(db_path: str, run_id: str | None = None) -> None:
    store = SqliteTrajectoryStore(db_path)
    
    if run_id is None:
        # Find latest run sequence
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT run_id FROM stored_events ORDER BY rowid DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if not row:
            print("No runs found in trajectory store.")
            return
        run_id = row[0]

    print(f"🔍 Inspecting Trajectory for Run ID: {run_id}\n" + "=" * 60)
    
    events = [ev async for ev in store.replay(run_id)]
    for ev in events:
        payload = json.loads(ev.payload_json)
        print(f"[{ev.seq:03d}] {ev.event_type.upper()} @ {ev.at}")
        
        if ev.event_type == "node_started":
            print(f"    --> Entering Workflow Step: {payload.get('node_id')}")
        elif ev.event_type == "effect_dispatched":
            print(f"    --> Dispatched Effect: {payload.get('effect_type')}")
        elif ev.event_type == "gate_report_emitted":
            print(f"    --> Gate Verdict: {payload.get('status')} | Admitted: {payload.get('admitted')}")
        elif ev.event_type == "node_completed":
            print(f"    --> Completed Step Output: {str(payload.get('output'))[:100]}...")
        print("-" * 60)

if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "./trajectory_demo.db"
    asyncio.run(inspect(db))
```

---

### Tutorial 4: Using Iterative Self-Repair Workflow

For complex tasks requiring self-healing iterations when tests fail:

```python
result = await engine.run(
    task,
    repo_path=str(workspace),
    worktrees_root=str(worktrees),
    topology_path="workflows/linear_repair_v1.yaml",  # Iterative self-repair DAG
    resolve_command=lambda spec: test_cmd,
    model_base_url="http://localhost:11434/v1",
    model_name="deepseek-r1:8b",
    trajectory_db_path="./repair_trajectory.db",
)
```

In `linear_repair_v1.yaml`, if the `evaluate` node returns `FAILED`, execution automatically routes to `repair` → `apply` → `evaluate` (up to 3 repair iterations).

---

## 7. Summary & Quick Reference

| Action | Command / Function |
| :--- | :--- |
| **Run an ad-hoc task** | `uv run python3 scripts/run_aether_task.py --workspace ... --instructions "..." --entry-file main.py --test-code "..." --model ...` |
| **Run Task via Python API** | `await aether.engine.run(task, repo_path=..., topology_path=..., ...)` |
| **Inspect DB via sqlite3** | `sqlite3 trajectory.db "SELECT seq, event_type, at FROM stored_events;"` |
| **Linear Workflow** | `workflows/linear_v1.yaml` |
| **Repair Workflow** | `workflows/linear_repair_v1.yaml` |
| **Small-Model Repair Workflow** | `workflows/linear_repair_small_model_v1.yaml` |

There is no AETHER-native replay verification CLI yet — `sagiha replay` is
`src/sagiha/`'s own command, unrelated to `aether.engine`.
