#!/usr/bin/env python3
"""AETHER Harness Demo & Trajectory Inspector Script.

Runs the AETHER coding agent harness against a local Ollama LLM endpoint
(e.g., DeepSeek R1) to solve a simple Python task:
Create/fix `main.py` to compute and print the sum of two numbers.

Saves and reads trajectory SQLite DB logs to trace harness inputs/outputs,
LLM steps, tool calls, and evaluator reports.
Saves all workspace files and results in `swe_tasks/` directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aether import engine  # noqa: E402
from aether.domain.config import ModelRoute, RunConfig  # noqa: E402
from aether.domain.ids import TaskId  # noqa: E402
from aether.domain.task import Task, TaskSource  # noqa: E402
from aether.measurement.evaluator import hash_command  # noqa: E402

SWE_TASKS_DIR = REPO_ROOT / "swe_tasks"
DEMO_REPO_DIR = SWE_TASKS_DIR / "demo_repo"
WORKTREES_ROOT = SWE_TASKS_DIR / "worktrees"
TRAJECTORY_DB = SWE_TASKS_DIR / "trajectory.db"


def setup_demo_git_repository() -> None:
    """Initialize a small git repository in swe_tasks/ for the agent task."""
    SWE_TASKS_DIR.mkdir(parents=True, exist_ok=True)
    if DEMO_REPO_DIR.exists():
        shutil.rmtree(DEMO_REPO_DIR)
    DEMO_REPO_DIR.mkdir(parents=True, exist_ok=True)

    # Initial main.py stub
    main_py = DEMO_REPO_DIR / "main.py"
    main_py.write_text(
        "# TODO: Define function add(a: int, b: int) -> int\n"
        "def add(a: int, b: int) -> int:\n"
        "    pass\n\n"
        "if __name__ == '__main__':\n"
        "    print(add(10, 20))\n",
        encoding="utf-8",
    )

    # Test runner script run_tests.py
    run_tests_py = DEMO_REPO_DIR / "run_tests.py"
    run_tests_py.write_text(
        "import sys\n"
        "import main\n\n"
        "res = main.add(10, 20)\n"
        "assert res == 30, f'Expected 30, got {res}'\n"
        "print('TEST PASSED: 10 + 20 = 30')\n",
        encoding="utf-8",
    )

    # Git init and initial commit
    subprocess.run(["git", "init"], cwd=DEMO_REPO_DIR, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Aether Demo"], cwd=DEMO_REPO_DIR, check=True)
    subprocess.run(["git", "config", "user.email", "demo@aether.local"], cwd=DEMO_REPO_DIR, check=True)
    subprocess.run(["git", "add", "."], cwd=DEMO_REPO_DIR, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=DEMO_REPO_DIR, check=True)


def get_git_head_sha() -> str:
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=DEMO_REPO_DIR, check=True, capture_output=True, text=True
    )
    return res.stdout.strip()


def inspect_trajectory_db(db_path: Path) -> None:
    """Read and format the trajectory SQLite DB events for debugging and audit."""
    print("\n=======================================================")
    print("       INSPECTING TRAJECTORY SQLITE DB LOGS")
    print(f"       File: {db_path}")
    print("=======================================================\n")

    if not db_path.exists():
        print(f"Error: Trajectory DB {db_path} does not exist!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT seq, run_id, event_type, payload_json, at FROM events ORDER BY seq ASC")
    rows = cursor.fetchall()
    print(f"Total Trajectory Events Logged: {len(rows)}\n")

    for seq, _run_id, event_type, payload_json, at in rows:
        print(f"--- Event #{seq} | Type: {event_type} | Time: {at} ---")
        try:
            payload = json.loads(payload_json)
            if event_type == "node_started":
                print(f"  --> Entering Node: {payload.get('node_id')}")
            elif event_type == "node_completed":
                print(f"  --> Completed Node: {payload.get('node_id')}")
                output = payload.get("output")
                if isinstance(output, dict):
                    if "patch_text" in output:
                        print(f"      Generated Patch:\n{output['patch_text'][:500]}")
                    elif "report" in output:
                        print(f"      Evaluation Report: {output['report']}")
            elif event_type == "effect_dispatched":
                request = payload.get("request", {})
                print(f"  --> Dispatched Effect Class: {request.get('effect_class')}")
                if "descriptor" in request:
                    desc = str(request["descriptor"])
                    if len(desc) > 300:
                        print(f"      Descriptor Snippet: {desc[:300]}...")
                    else:
                        print(f"      Descriptor: {desc}")
            elif event_type == "gate_report_emitted":
                rep = payload.get("report", {})
                st = rep.get("status")
                gt = rep.get("gate")
                dt = rep.get("detail")
                print(f"  --> GATE REPORT: status={st} | gate={gt} | detail={dt}")
            else:
                print(f"  Payload: {json.dumps(payload, indent=2)}")
        except Exception:
            print(f"  Raw Payload: {payload_json[:300]}...")
        print()

    conn.close()


def prepare_workspace() -> str:
    setup_demo_git_repository()
    if WORKTREES_ROOT.exists():
        shutil.rmtree(WORKTREES_ROOT)
    WORKTREES_ROOT.mkdir(parents=True, exist_ok=True)
    if TRAJECTORY_DB.exists():
        TRAJECTORY_DB.unlink()
    return get_git_head_sha()


def copy_final_results() -> None:
    """Copy final candidate main.py and run_tests.py to swe_tasks/ root for easy viewing."""
    candidate_mains = list(WORKTREES_ROOT.glob("**/main.py"))
    if candidate_mains:
        target_main = SWE_TASKS_DIR / "main.py"
        target_repo_main = DEMO_REPO_DIR / "main.py"
        shutil.copy(candidate_mains[0], target_main)
        shutil.copy(candidate_mains[0], target_repo_main)
        print("\nSaved admitted code to:")
        print(f"  - {target_main}")
        print(f"  - {target_repo_main}")


async def run_demo(
    model_name: str, base_url: str, topology: str
) -> None:
    print(f"Setting up demo Git repository in {SWE_TASKS_DIR}...")
    base_commit = await asyncio.to_thread(prepare_workspace)

    test_cmd = "python3 run_tests.py"
    instructions = (
        "The file `main.py` has a function `add(a: int, b: int) -> int` that currently does nothing.\n"
        "Fix `main.py` so `add(a, b)` returns `a + b` and tests in `run_tests.py` pass."
    )

    task = Task(
        task_id=TaskId("demo-python-sum-task"),
        repo=str(DEMO_REPO_DIR),
        base_commit=base_commit,
        instructions=instructions,
        environment_image_digest="local-python3",
        test_command_hash=hash_command(test_cmd),
        source=TaskSource(manifest_hash="demo-manifest", instance_id="demo-python-sum-task"),
    )

    print("\nStarting AETHER Coding Harness Execution:")
    print(f"  Task ID    : {task.task_id}")
    print(f"  Model      : {model_name}")
    print(f"  Endpoint   : {base_url}")
    print(f"  Topology   : {topology}")
    print(f"  Workdir    : {WORKTREES_ROOT}")
    print(f"  DB Path    : {TRAJECTORY_DB}\n")

    started = time.monotonic()
    config = RunConfig(
        topology_path=topology,
        repo_path=str(DEMO_REPO_DIR),
        worktrees_root=str(WORKTREES_ROOT),
        trajectory_db_path=str(TRAJECTORY_DB),
        entry_files=("main.py",),
        routes=(ModelRoute(base_url=base_url, model=model_name),),
        test_command=test_cmd,
    )
    result = await engine.run(
        task,
        config,
        resolve_command=lambda spec: test_cmd,
    )
    elapsed = time.monotonic() - started

    print("\n=======================================================")
    print("               AETHER RUN COMPLETED")
    print("=======================================================")
    print(f"Run ID      : {result.run_id}")
    print(f"Status      : {result.gate_report.status.value.upper()}")
    print(f"Gate        : {result.gate_report.gate}")
    print(f"Detail      : {result.gate_report.detail}")
    print(f"Elapsed     : {elapsed:.2f}s")
    print(f"Tokens Spent: Prompt={result.usage.prompt_tokens}, Completion={result.usage.completion_tokens}")

    inspect_trajectory_db(TRAJECTORY_DB)

    if result.gate_report.status.value == "passed":
        await asyncio.to_thread(copy_final_results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="deepseek-r1:14b", help="Ollama model tag")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434/v1",
        help="OpenAI-compatible base URL",
    )
    parser.add_argument(
        "--topology",
        default=str(REPO_ROOT / "workflows" / "linear_repair_wholefile_v1.yaml"),
        help="Path to workflow topology YAML",
    )
    args = parser.parse_args(sys.argv[1:])
    model: str = str(args.model)
    base_url: str = str(args.base_url)
    topology: str = str(args.topology)
    asyncio.run(run_demo(model, base_url, topology))
    return 0


if __name__ == "__main__":
    sys.exit(main())
