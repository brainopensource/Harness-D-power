#!/usr/bin/env python3
"""Run an AETHER benchmark task using OpenRouter API models.

Records total execution time, LLM inference wall-clock time, USD cost,
tokens/second throughput, gate verdict, and trajectory events. Saves each
run in a dedicated folder under `swe_tasks/<model_slug>/`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

# Ensure `src` is in Python path when executed directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether import engine
from aether.domain.config import ModelRoute, RunConfig
from aether.domain.task import Task, TaskId, TaskSource
from aether.measurement.evaluator import hash_command


def load_env_file() -> None:
    """Load variables from .env if present."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


def sanitize_slug(name: str) -> str:
    """Convert model ID to safe directory slug (e.g., 'google/gemma-4:free' -> 'google_gemma-4_free')."""
    return name.replace("/", "_").replace(":", "_").replace(".", "_")


def prepare_repo(repo_dir: Path, entry_files: list[str], test_file: str, test_code: str) -> str:
    import subprocess

    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    repo_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "benchmark@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "AetherBenchmark"], cwd=repo_dir, check=True)

    (repo_dir / "README.md").write_text("# Benchmark Workspace\n")
    for f_path in entry_files:
        p = repo_dir / f_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("# Initial file placeholder\n")

    tf = repo_dir / test_file
    tf.parent.mkdir(parents=True, exist_ok=True)
    tf.write_text(test_code)

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial benchmark state"], cwd=repo_dir, check=True)

    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
    ).stdout.strip()
    return base_commit


async def run_benchmark(args: argparse.Namespace) -> dict:
    load_env_file()
    api_key = args.api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment or .env file.")
        sys.exit(1)

    model_slug = sanitize_slug(args.model)
    workspace = Path(args.swe_tasks_dir).resolve() / model_slug
    repo_dir = workspace / "repo"
    worktrees_root = workspace / "worktrees"
    trajectory_db = workspace / "trajectory.db"

    if worktrees_root.exists():
        shutil.rmtree(worktrees_root)
    worktrees_root.mkdir(parents=True, exist_ok=True)
    if trajectory_db.exists():
        trajectory_db.unlink()

    base_commit = prepare_repo(repo_dir, args.entry_files, args.test_file, args.test_code)
    test_cmd = f"python3 {args.test_file}"

    task = Task(
        task_id=TaskId(f"bench-{model_slug}"),
        repo=str(repo_dir),
        base_commit=base_commit,
        instructions=args.instructions,
        environment_image_digest="local-python3",
        test_command_hash=hash_command(test_cmd),
        test_paths=(args.test_file,),
        source=TaskSource(manifest_hash="openrouter-bench", instance_id=args.model),
    )

    print("============================================================")
    print(f"Model       : {args.model}")
    print(f"Topology    : {args.topology}")
    print(f"Workspace   : {workspace}")
    print("============================================================")

    os.environ["OPENROUTER_API_KEY"] = api_key

    config = RunConfig(
        topology_path=args.topology,
        repo_path=str(repo_dir),
        worktrees_root=str(worktrees_root),
        trajectory_db_path=str(trajectory_db),
        entry_files=tuple(args.entry_files),
        routes=(ModelRoute(base_url=args.base_url, model=args.model, api_key_env="OPENROUTER_API_KEY"),),
        test_command=test_cmd,
    )

    start_wall = time.perf_counter()
    result = await engine.run(task, config, resolve_command=lambda spec: test_cmd)
    end_wall = time.perf_counter()

    total_wall_time = end_wall - start_wall
    cost_usd = result.usage.usd_micros / 1_000_000.0
    total_tokens = result.usage.prompt_tokens + result.usage.completion_tokens
    tok_per_sec = (total_tokens / total_wall_time) if total_wall_time > 0 else 0.0

    summary = {
        "model": args.model,
        "status": result.gate_report.status.value.upper(),
        "gate": result.gate_report.gate,
        "detail": result.gate_report.detail,
        "total_wall_sec": round(total_wall_time, 2),
        "prompt_tokens": result.usage.prompt_tokens,
        "completion_tokens": result.usage.completion_tokens,
        "total_tokens": total_tokens,
        "tokens_per_sec": round(tok_per_sec, 2),
        "cost_usd": round(cost_usd, 6),
    }

    # Write metrics summary to workspace
    (workspace / "benchmark_summary.json").write_text(json.dumps(summary, indent=2))

    print("\n--- RUN RESULT ---")
    print(f"Status        : {summary['status']}")
    print(f"Total Time    : {summary['total_wall_sec']}s")
    print(f"Tokens/Sec    : {summary['tokens_per_sec']}")
    print(f"Cost USD      : ${summary['cost_usd']}")
    print(f"Detail        : {summary['detail'][:100]}...\n")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="OpenRouter model ID (e.g. openrouter/free)")
    parser.add_argument("--instructions", required=True, help="Task instructions for the LLM")
    parser.add_argument(
        "--entry-file", action="append", dest="entry_files", required=True, help="Entry file (repeatable)"
    )
    parser.add_argument("--test-file", default="run_tests.py", help="Test runner script")
    parser.add_argument("--test-code", required=True, help="Python code for test file")
    parser.add_argument(
        "--topology",
        default="workflows/linear_repair_small_model_v1.yaml",
        help="Workflow topology YAML path",
    )
    parser.add_argument("--base-url", default="https://openrouter.ai/api/v1", help="OpenRouter base URL")
    parser.add_argument("--api-key", default="", help="Optional explicit API key override")
    parser.add_argument("--swe-tasks-dir", default="swe_tasks", help="Root swe_tasks directory")

    args = parser.parse_args()
    summary = asyncio.run(run_benchmark(args))
    return 0 if summary["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
