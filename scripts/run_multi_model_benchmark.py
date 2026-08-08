#!/usr/bin/env python3
"""Multi-Model Benchmark Runner for AETHER Coding Agent Harness.

Executes a benchmark matrix across local Ollama models:
- llama3.2:3b        -> swe_tasks/llama32_001/main_001.py
- deepseek-r1:14b    -> swe_tasks/deepseek_r1_001/main_001.py
- qwen2.5:1.5b       -> swe_tasks/qwen25_001/main_001.py

For each model, logs step-by-step inputs, outputs, gate verdicts,
and trajectory DB logs without overwriting each other.
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
from aether.domain.ids import TaskId  # noqa: E402
from aether.domain.task import Task, TaskSource  # noqa: E402
from aether.measurement.evaluator import hash_command  # noqa: E402

SWE_TASKS_DIR = REPO_ROOT / "swe_tasks"


def setup_model_workspace(model_folder_name: str) -> tuple[Path, Path, Path, str]:
    """Create isolated repo, worktree, and DB paths for a specific model run."""
    folder = SWE_TASKS_DIR / model_folder_name
    folder.mkdir(parents=True, exist_ok=True)

    repo_dir = folder / "repo"
    worktrees_root = folder / "worktrees"
    db_path = folder / "trajectory.db"

    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    if worktrees_root.exists():
        shutil.rmtree(worktrees_root)
    if db_path.exists():
        db_path.unlink()

    repo_dir.mkdir(parents=True, exist_ok=True)
    worktrees_root.mkdir(parents=True, exist_ok=True)

    # Initial main_001.py stub
    main_py = repo_dir / "main_001.py"
    main_py.write_text(
        "# TODO: Implement function add_numbers(a: int, b: int) -> int\n"
        "def add_numbers(a: int, b: int) -> int:\n"
        "    pass\n",
        encoding="utf-8",
    )

    # Test runner script run_tests.py
    run_tests_py = repo_dir / "run_tests.py"
    run_tests_py.write_text(
        "import main_001\n\n"
        "res = main_001.add_numbers(12, 18)\n"
        "assert res == 30, f'Expected 30, got {res}'\n"
        "print('TEST SUITE PASSED: add_numbers(12, 18) == 30')\n",
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "bench@aether.local"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Aether Bench"], cwd=repo_dir, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial commit"], cwd=repo_dir, check=True)

    res = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
    )
    base_commit = res.stdout.strip()
    return repo_dir, worktrees_root, db_path, base_commit


def inspect_model_trajectory(db_path: Path) -> None:
    if not db_path.exists():
        print(f"No trajectory DB found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT seq, event_type, payload_json, at FROM events ORDER BY seq ASC")
    rows = cursor.fetchall()
    print(f"\n--- Trajectory Events Summary ({len(rows)} events in {db_path.name}) ---")
    for seq, event_type, payload_json, at in rows:
        try:
            raw: object = json.loads(payload_json)
            if isinstance(raw, dict):
                node_id = str(raw.get("node_id", ""))  # type: ignore[no-any-expr]
                if event_type == "node_started":
                    print(f"  Event #{seq:02d} | Node Started   : {node_id} @ {at}")
                elif event_type == "node_completed":
                    print(f"  Event #{seq:02d} | Node Completed : {node_id} @ {at}")
                    out = raw.get("output")  # type: ignore[no-any-expr]
                    if isinstance(out, dict):
                        pt = out.get("patch_text")  # type: ignore[no-any-expr]
                        if isinstance(pt, str):
                            snip = pt[:150].replace("\n", " ")
                            print(f"             Output Patch Snippet: {snip}...")
                elif event_type == "gate_report_emitted":
                    rep = raw.get("report")  # type: ignore[no-any-expr]
                    if isinstance(rep, dict):
                        st_val = str(rep.get("status", ""))  # type: ignore[no-any-expr]
                        dt_val = str(rep.get("detail", ""))  # type: ignore[no-any-expr]
                        print(f"  Event #{seq:02d} | GATE VERDICT   : status={st_val} | detail={dt_val}")
                elif event_type == "repair_iteration_started":
                    cur_it = str(raw.get("iteration", ""))  # type: ignore[no-any-expr]
                    max_it = str(raw.get("max_iterations", ""))  # type: ignore[no-any-expr]
                    print(f"  Event #{seq:02d} | REPAIR LOOP    : iteration {cur_it}/{max_it}")
        except Exception:
            pass
    conn.close()


async def run_single_benchmark(
    model_tag: str,
    folder_name: str,
    base_url: str,
    topology_path: str,
) -> dict[str, str | int | float]:
    print("\n=======================================================")
    print(f" RUNNING BENCHMARK: {model_tag}")
    print(f" Output Folder : {SWE_TASKS_DIR / folder_name}")
    print("=======================================================")

    repo_dir, worktrees_root, db_path, base_commit = await asyncio.to_thread(
        setup_model_workspace, folder_name
    )

    test_cmd = "python3 run_tests.py"
    instructions = (
        "Fix `main_001.py` so that function `add_numbers(a: int, b: int) -> int` "
        "returns the sum of `a` and `b` (`a + b`). Ensure tests in `run_tests.py` pass."
    )

    task = Task(
        task_id=TaskId(f"bench-{folder_name}"),
        repo=str(repo_dir),
        base_commit=base_commit,
        instructions=instructions,
        environment_image_digest="local-python3",
        test_command_hash=hash_command(test_cmd),
        source=TaskSource(manifest_hash="bench-manifest", instance_id=f"bench-{folder_name}"),
    )

    t0 = time.monotonic()
    result = await engine.run(
        task,
        repo_path=str(repo_dir),
        worktrees_root=str(worktrees_root),
        topology_path=topology_path,
        resolve_command=lambda spec: test_cmd,
        model_base_url=base_url,
        model_name=model_tag,
        trajectory_db_path=str(db_path),
        sandbox_runtime=None,
        entry_files=("main_001.py",),
    )
    elapsed = time.monotonic() - t0

    # Save admitted result to folder_name/main_001.py
    candidate_files = list(worktrees_root.glob("**/main_001.py"))
    saved_filepath = ""
    if candidate_files:
        admitted_dest = SWE_TASKS_DIR / folder_name / "main_001.py"
        shutil.copy(candidate_files[0], admitted_dest)
        saved_filepath = str(admitted_dest)

    inspect_model_trajectory(db_path)

    print(f"\nResult for {model_tag}:")
    print(f"  Status        : {result.gate_report.status.value.upper()}")
    print(f"  Elapsed Time  : {elapsed:.2f}s")
    print(f"  Admitted File : {saved_filepath}")

    return {
        "model": model_tag,
        "folder": folder_name,
        "status": result.gate_report.status.value.upper(),
        "elapsed": elapsed,
        "filepath": saved_filepath,
        "db_path": str(db_path),
    }


async def run_matrix(base_url: str, topology_path: str) -> None:
    SWE_TASKS_DIR.mkdir(parents=True, exist_ok=True)
    models = [
        ("llama3.2:3b", "llama32_001"),
        ("deepseek-r1:14b", "deepseek_r1_001"),
        ("qwen2.5:1.5b", "qwen25_001"),
    ]

    benchmark_summary: list[dict[str, str | int | float]] = []
    for model_tag, folder_name in models:
        res = await run_single_benchmark(model_tag, folder_name, base_url, topology_path)
        benchmark_summary.append(res)

    print("\n=======================================================")
    print("        FINAL MULTI-MODEL BENCHMARK SUMMARY")
    print("=======================================================")
    for b in benchmark_summary:
        print(f"Model    : {b['model']}")
        print(f"Folder   : {SWE_TASKS_DIR / str(b['folder'])}")
        print(f"Filepath : {b['filepath']}")
        print(f"Status   : {b['status']}")
        print(f"Elapsed  : {b['elapsed']:.2f}s")
        print(f"DB Log   : {b['db_path']}")
        print("-" * 50)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument(
        "--topology",
        default=str(REPO_ROOT / "workflows" / "linear_repair_wholefile_v1.yaml"),
    )
    args = parser.parse_args(sys.argv[1:])
    base_url: str = str(args.base_url)
    topology: str = str(args.topology)
    asyncio.run(run_matrix(base_url, topology))
    return 0


if __name__ == "__main__":
    sys.exit(main())
