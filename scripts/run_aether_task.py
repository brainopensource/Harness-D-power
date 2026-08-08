#!/usr/bin/env python3
"""Generic AETHER task runner.

Unlike `run_aether_demo.py` (which always runs one hardcoded "add" task),
this accepts an arbitrary goal, entry file(s), and test command, so it can
drive `aether.engine.run()` against a real local Ollama model for any task.

`aether` has no CLI of its own yet (see AGENTS.md — only `sagiha`, which is
predecessor material being retired, is registered as a console script). This
is a thin, uncommitted-to-TCB script wrapping the public `aether.engine.run()`
API — it does not touch anything under `src/aether/`.

Example (single file):
    uv run python3 scripts/run_aether_task.py \\
      --workspace swe_tasks/my_task \\
      --entry-file main.py \\
      --instructions "Write is_even(n: int) -> bool in main.py returning True if n is even." \\
      --test-file run_tests.py \\
      --test-code "import main; assert main.is_even(4) is True; assert main.is_even(3) is False; print('PASSED')" \\
      --model qwen2.5:1.5b

Example (multiple entry files):
    uv run python3 scripts/run_aether_task.py \\
      --workspace swe_tasks/my_pkg_task \\
      --entry-file pkg/__init__.py --entry-file pkg/ops.py \\
      --instructions "In pkg/ops.py define add(a,b) and mul(a,b); re-export both from pkg/__init__.py." \\
      --test-file run_tests.py \\
      --test-code "from pkg import add, mul; assert add(2,3)==5 and mul(2,3)==6; print('PASSED')" \\
      --model qwen2.5:1.5b
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aether import engine  # noqa: E402
from aether.domain.ids import TaskId  # noqa: E402
from aether.domain.task import Task, TaskSource  # noqa: E402
from aether.measurement.evaluator import hash_command  # noqa: E402


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def prepare_repo(repo_dir: Path, entry_files: list[str], test_file: str, test_code: str) -> str:
    """(Re)initialize a fresh git repo containing stub entry files and the fixed test file.

    The test file is written by us, not the model — I7 (`tests_unmodified`) means the
    candidate that writes the fix must never be the one grading it.
    """
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    repo_dir.mkdir(parents=True, exist_ok=True)

    for rel in entry_files:
        path = repo_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(f"# TODO: {rel} — see task instructions\n", encoding="utf-8")

    (repo_dir / test_file).parent.mkdir(parents=True, exist_ok=True)
    (repo_dir / test_file).write_text(test_code + "\n", encoding="utf-8")

    _git(["init", "-q"], repo_dir)
    _git(["config", "user.email", "dev@aether.local"], repo_dir)
    _git(["config", "user.name", "Aether Task Runner"], repo_dir)
    _git(["add", "."], repo_dir)
    _git(["commit", "-q", "-m", "initial commit"], repo_dir)
    return _git(["rev-parse", "HEAD"], repo_dir).stdout.strip()


def inspect_trajectory_db(db_path: Path) -> None:
    if not db_path.exists():
        print(f"(no trajectory DB at {db_path})")
        return
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT seq, event_type, payload_json, at FROM events ORDER BY seq ASC"
    ).fetchall()
    print(f"\n--- {len(rows)} trajectory events ({db_path}) ---")
    for seq, event_type, payload_json, at in rows:
        print(f"[{seq:02d}] {event_type:<24} @ {at}")
        if event_type == "gate_report_emitted":
            try:
                report = json.loads(payload_json).get("report", {})
                print(f"      status={report.get('status')} detail={str(report.get('detail'))[:200]}")
            except Exception:
                pass
    conn.close()


def copy_admitted_files(worktrees_root: Path, entry_files: list[str], out_dir: Path) -> None:
    for rel in entry_files:
        candidates = list(worktrees_root.glob(f"**/{rel}"))
        if candidates:
            target = out_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(candidates[0], target)
            print(f"  saved: {target}")


async def run_task(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    repo_dir = workspace / "repo"
    worktrees_root = workspace / "worktrees"
    trajectory_db = workspace / "trajectory.db"

    if worktrees_root.exists():
        shutil.rmtree(worktrees_root)
    worktrees_root.mkdir(parents=True, exist_ok=True)
    if trajectory_db.exists():
        trajectory_db.unlink()

    base_commit = prepare_repo(repo_dir, args.entry_file, args.test_file, args.test_code)
    test_cmd = f"python3 {args.test_file}"

    task = Task(
        task_id=TaskId(args.task_id),
        repo=str(repo_dir),
        base_commit=base_commit,
        instructions=args.instructions,
        environment_image_digest="local-python3",
        test_command_hash=hash_command(test_cmd),
        test_paths=(args.test_file,),
        source=TaskSource(manifest_hash="ad-hoc", instance_id=args.task_id),
    )

    print(f"Task        : {args.task_id}")
    print(f"Model       : {args.model} @ {args.base_url}")
    print(f"Topology    : {args.topology}")
    print(f"Entry files : {', '.join(args.entry_file)}")
    print(f"Test cmd    : {test_cmd}")
    print(f"Workspace   : {workspace}\n")

    result = await engine.run(
        task,
        repo_path=str(repo_dir),
        worktrees_root=str(worktrees_root),
        topology_path=args.topology,
        resolve_command=lambda spec: test_cmd,
        model_base_url=args.base_url,
        model_name=args.model,
        trajectory_db_path=str(trajectory_db),
        sandbox_runtime=None,
        entry_files=tuple(args.entry_file),
    )

    print(f"run_id      : {result.run_id}")
    print(f"status      : {result.gate_report.status.value.upper()}")
    print(f"gate        : {result.gate_report.gate}")
    print(f"detail      : {result.gate_report.detail}")

    inspect_trajectory_db(trajectory_db)

    if result.gate_report.status.value == "passed":
        copy_admitted_files(worktrees_root, args.entry_file, workspace)
        return 0
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", required=True, help="Directory to (re)create the task repo/worktrees/db in")
    parser.add_argument("--instructions", required=True, help="Task instructions given to the model")
    parser.add_argument(
        "--entry-file", action="append", required=True, help="Repo-relative file the agent may read/write (repeatable)"
    )
    parser.add_argument("--test-file", default="run_tests.py", help="Repo-relative path for the fixed test file")
    parser.add_argument("--test-code", required=True, help="Literal Python source for --test-file (written by us, not the model)")
    parser.add_argument("--model", default="qwen2.5:1.5b", help="Ollama model tag")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1", help="OpenAI-compatible base URL")
    parser.add_argument(
        "--topology",
        default=str(REPO_ROOT / "workflows" / "linear_repair_wholefile_v1.yaml"),
        help="Path to workflow topology YAML",
    )
    parser.add_argument("--task-id", default="ad-hoc-task")
    args = parser.parse_args()
    return asyncio.run(run_task(args))


if __name__ == "__main__":
    sys.exit(main())
