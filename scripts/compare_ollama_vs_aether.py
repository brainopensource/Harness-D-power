#!/usr/bin/env python3
"""Compare direct raw Ollama output vs AETHER Coding Agent Harness output.

1. Direct raw Ollama LLM call (DeepSeek R1 14B) via OpenAI-compatible endpoint.
2. AETHER Autonomous Harness call with capability security, structured edit format,
   worktree isolation, test gate verification, and trajectory SQLite DB logging.
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
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aether import engine  # noqa: E402
from aether.domain.config import ModelRoute, RunConfig  # noqa: E402
from aether.domain.ids import TaskId  # noqa: E402
from aether.domain.task import Task, TaskSource  # noqa: E402
from aether.measurement.evaluator import hash_command  # noqa: E402

DEMO_REPO = Path("/tmp/aether_compare_repo")
WORKTREES = Path("/tmp/aether_compare_worktrees")
TRAJECTORY_DB = Path("/tmp/aether_compare_trajectory.db")


def setup_test_repository() -> str:
    if DEMO_REPO.exists():
        shutil.rmtree(DEMO_REPO)
    DEMO_REPO.mkdir(parents=True, exist_ok=True)

    main_py = DEMO_REPO / "main.py"
    main_py.write_text(
        "# TODO: Define function calculate_sum(a: int, b: int) -> int\n"
        "def calculate_sum(a: int, b: int) -> int:\n"
        "    pass\n",
        encoding="utf-8",
    )

    run_tests_py = DEMO_REPO / "run_tests.py"
    run_tests_py.write_text(
        "import main\n\n"
        "res = main.calculate_sum(15, 25)\n"
        "assert res == 40, f'Expected 40, got {res}'\n"
        "print('ALL TESTS PASSED: calculate_sum(15, 25) == 40')\n",
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-q"], cwd=DEMO_REPO, check=True)
    subprocess.run(["git", "config", "user.email", "dev@aether.local"], cwd=DEMO_REPO, check=True)
    subprocess.run(["git", "config", "user.name", "Aether Tester"], cwd=DEMO_REPO, check=True)
    subprocess.run(["git", "add", "."], cwd=DEMO_REPO, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial commit"], cwd=DEMO_REPO, check=True)

    res = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=DEMO_REPO, check=True, capture_output=True, text=True
    )
    return res.stdout.strip()


def query_ollama_direct(model: str, base_url: str, prompt: str) -> str:
    """Send direct raw call to local Ollama chat completions endpoint."""
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            choices = body.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                return str(msg.get("content", ""))
            return "No content in choices"
    except Exception as err:
        return f"Direct Ollama Error: {err}"


def inspect_db_trajectory(db_path: Path) -> list[dict[str, str]]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT seq, event_type, payload_json, at FROM events ORDER BY seq ASC")
    rows = cursor.fetchall()
    events: list[dict[str, str]] = []
    for seq, event_type, payload_json, at in rows:
        events.append({"seq": str(seq), "type": str(event_type), "payload": str(payload_json), "at": str(at)})
    conn.close()
    return events


def prepare_workspace() -> str:
    if WORKTREES.exists():
        shutil.rmtree(WORKTREES)
    WORKTREES.mkdir(parents=True, exist_ok=True)
    if TRAJECTORY_DB.exists():
        TRAJECTORY_DB.unlink()
    return setup_test_repository()


async def run_comparison(model: str, base_url: str, topology: str) -> None:
    base_commit = await asyncio.to_thread(prepare_workspace)

    prompt_text = (
        "Create a python function `calculate_sum(a: int, b: int) -> int` in file `main.py` "
        "that returns the sum of two integers `a + b` so that tests pass."
    )

    print("\n=======================================================")
    print("      1. DIRECT RAW OLLAMA CALL (No Harness)")
    print(f"      Endpoint: {base_url} | Model: {model}")
    print("=======================================================\n")
    
    t0 = time.monotonic()
    direct_response = await asyncio.to_thread(query_ollama_direct, model, base_url, prompt_text)
    direct_elapsed = time.monotonic() - t0
    
    print(f"Direct Response Received in {direct_elapsed:.2f}s:")
    print("-" * 60)
    print(direct_response[:1000])
    if len(direct_response) > 1000:
        print("... [truncated]")
    print("-" * 60)

    print("\n=======================================================")
    print("      2. AETHER HARNESS RUN (Autonomous Agent)")
    print(f"      Topology: {topology}")
    print("=======================================================\n")

    test_cmd = "python3 run_tests.py"
    task = Task(
        task_id=TaskId("compare-task-01"),
        repo=str(DEMO_REPO),
        base_commit=base_commit,
        instructions=prompt_text,
        environment_image_digest="local-python3",
        test_command_hash=hash_command(test_cmd),
        source=TaskSource(manifest_hash="compare-manifest", instance_id="compare-task-01"),
    )

    t1 = time.monotonic()
    config = RunConfig(
        topology_path=topology,
        repo_path=str(DEMO_REPO),
        worktrees_root=str(WORKTREES),
        trajectory_db_path=str(TRAJECTORY_DB),
        entry_files=("main.py",),
        routes=(ModelRoute(base_url=base_url, model=model),),
        test_command=test_cmd,
    )
    run_res = await engine.run(
        task,
        config,
        resolve_command=lambda spec: test_cmd,
    )
    aether_elapsed = time.monotonic() - t1

    print("\n=======================================================")
    print("               AETHER HARNESS RESULTS")
    print("=======================================================")
    print(f"Run ID      : {run_res.run_id}")
    print(f"Gate Status : {run_res.gate_report.status.value.upper()}")
    print(f"Gate        : {run_res.gate_report.gate}")
    print(f"Elapsed Time: {aether_elapsed:.2f}s")
    print(f"Spend Tokens: Prompt={run_res.usage.prompt_tokens}, Completion={run_res.usage.completion_tokens}")

    # Inspect SQLite Trajectory DB
    db_events = inspect_db_trajectory(TRAJECTORY_DB)
    print(f"\nSQLite Trajectory DB Logged {len(db_events)} Events in {TRAJECTORY_DB}:")
    for ev in db_events:
        print(f"  [Seq #{ev['seq']}] {ev['type']} @ {ev['at']}")

    def find_main() -> list[Path]:
        return list(WORKTREES.glob("**/main.py"))

    candidate_main = await asyncio.to_thread(find_main)
    if candidate_main:
        print("\nFinal Candidate `main.py` in Isolated Worktree:")
        print("=" * 60)
        print(candidate_main[0].read_text(encoding="utf-8"))
        print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="deepseek-r1:14b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument(
        "--topology",
        default=str(REPO_ROOT / "workflows" / "linear_repair_wholefile_v1.yaml"),
    )
    args = parser.parse_args(sys.argv[1:])
    model: str = str(args.model)
    base_url: str = str(args.base_url)
    topology: str = str(args.topology)
    asyncio.run(run_comparison(model, base_url, topology))
    return 0


if __name__ == "__main__":
    sys.exit(main())
