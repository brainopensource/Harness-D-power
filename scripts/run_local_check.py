#!/usr/bin/env python3
"""Run a few manifest tasks against a local model (Sprint 3.5, tier 0/1).

**Not a benchmark and not a floor.** N is tiny, no gate family is consulted,
nothing is written to `docs/`. It answers one question the instruments cannot:
does this harness, on this topology, actually resolve a task?

The ladder it belongs to separates two failure causes that look identical from
the outside — a harness that cannot carry a task, and a model that cannot solve
one. Same tasks, same evaluator, one variable at a time:

    tier 0  internal-floor-01   trivial single-bug tasks, local model, free
    tier 1  internal-medium-01  multi-file tasks, local model, free

    python3 scripts/run_local_check.py --model qwen2.5:1.5b --tasks 3
    python3 scripts/run_local_check.py --model qwen2.5:1.5b --tasks 3 \\
        --topology workflows/linear_repair_wholefile_v1.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aether import engine  # noqa: E402
from aether.domain.gate import GateStatus  # noqa: E402
from aether.domain.task import Task, TaskSource  # noqa: E402
from aether.measurement.manifest import load_manifest, manifest_hash, tasks_in_split  # noqa: E402
from aether.measurement.outcomes import ArmRun, TaskOutcome  # noqa: E402
from aether.measurement.pricing import cost_usd_micros  # noqa: E402
from aether.measurement.statistics import resolve_rate  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "benchmarks" / "manifests" / "internal-floor-01.yaml"
DEFAULT_SUITE_DIR = Path.home() / ".cache" / "aether" / "internal_suite"
TEST_COMMAND = "python3 run_tests.py"


def build_task_instructions(task_dir: Path, entry_files: list[str]) -> str:
    test_file = task_dir / "run_tests.py"
    test_content = test_file.read_text(encoding="utf-8") if test_file.exists() else ""
    files_str = ", ".join(entry_files)
    return (
        f"The tests in `run_tests.py` assert the correct behaviour. "
        f"Fix the bug in the following files: {files_str} so the tests pass.\n\n"
        f"## run_tests.py\n```python\n{test_content}\n```"
    )


def auto_discover_entry_files(task_dir: Path) -> list[str]:
    files: list[str] = []
    for p in task_dir.glob("**/*.py"):
        if p.name == "run_tests.py":
            continue
        files.append(str(p.relative_to(task_dir)))
    return sorted(files)


async def main_async(args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    sha = manifest_hash(manifest)
    # The manifest is the static truth; a run downsamples it. Seeded, so
    # "10 random tasks" is a reproducible 10 and not a different suite per run.
    pool = tasks_in_split(manifest, args.split)
    if args.max_tasks and args.max_tasks < len(pool):
        tasks = sorted(
            random.Random(args.sample_seed).sample(pool, args.max_tasks),
            key=lambda t: t["instance_id"],
        )
    else:
        tasks = pool

    print(f"model      {args.model} @ {args.base_url}")
    print(f"topology   {Path(args.topology).name}")
    print(
        f"manifest   {sha[:22]}…  split={args.split}  "
        f"sampled {len(tasks)}/{len(pool)} (seed {args.sample_seed})"
    )
    print(f"evaluator  {'contained (' + args.runtime + ')' if not args.uncontained else 'UNCONTAINED'}")

    ceiling = int(args.usd_cap * 1_000_000) if args.usd_cap else None
    if ceiling is not None:
        # Pre-flight: state the worst case before spending anything. A cap
        # nobody checked before the run is a cap discovered on the invoice.
        worst_calls = len(tasks) * 4  # 1 generate + up to 3 repair iterations
        worst = worst_calls * cost_usd_micros(args.model, 4_000, 1_000, base_url=args.base_url)
        print(
            f"budget     cap ${args.usd_cap:.2f} per run · worst case ~{worst_calls} calls "
            f"≈ ${worst / 1_000_000:.4f}/task-run at list price"
        )
        if worst > ceiling:
            print("           worst case exceeds the cap — the governor will stop the run early")
    print()

    results: list[TaskOutcome] = []
    started_all = time.monotonic()
    for index, entry in enumerate(tasks, start=1):
        instance_id = entry["instance_id"]
        task_dir = Path(args.suite_dir) / instance_id

        task_entry_files = args.entry_files if args.entry_files else auto_discover_entry_files(task_dir)
        task_instructions = (
            args.instructions
            if args.instructions is not None
            else build_task_instructions(task_dir, task_entry_files)
        )

        task = Task(
            task_id=instance_id,  # type: ignore[arg-type]
            repo=entry["repo"],
            base_commit=entry["base_commit"],
            instructions=task_instructions,
            environment_image_digest=entry["environment_image_digest"],
            test_command_hash=entry["test_command_hash"],
            source=TaskSource(manifest_hash=sha, instance_id=instance_id),
        )
        started = time.monotonic()
        try:
            result = await engine.run(
                task,
                repo_path=str(Path(args.suite_dir) / instance_id),
                worktrees_root=str(Path(args.workdir) / instance_id),
                topology_path=args.topology,
                resolve_command=lambda spec: TEST_COMMAND,
                model_base_url=args.base_url,
                model_name=args.model,
                trajectory_db_path=str(Path(args.workdir) / "trajectory.db"),
                sandbox_runtime=None if args.uncontained else args.runtime,
                usd_micros_ceiling=ceiling,
                model_api_key=os.environ.get("OPENROUTER_API_KEY"),
                entry_files=tuple(task_entry_files) if task_entry_files else None,
            )
            outcome = TaskOutcome(
                task_id=instance_id,
                status=result.gate_report.status,
                wall_clock_ms=int((time.monotonic() - started) * 1000),
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
                usd_micros=result.usage.usd_micros,
                detail=result.gate_report.instrument_error or "",
            )
        except Exception as exc:  # noqa: BLE001 — our crash is an instrument error, not a task failure
            outcome = TaskOutcome(
                task_id=instance_id,
                status=GateStatus.NONE,
                wall_clock_ms=int((time.monotonic() - started) * 1000),
                detail=f"{type(exc).__name__}: {exc}",
            )
        results.append(outcome)
        mark = {"passed": "PASS", "failed": "fail", "none": "NONE"}[outcome.status.value]
        print(
            f"  {index:2d}/{len(tasks)} {instance_id:28} {mark:5} {outcome.wall_clock_ms / 1000:6.1f}s"
            + (f"  {outcome.detail[:90]}" if outcome.detail else "")
        )

    run = ArmRun(
        run_id="local-check",
        arm_id="local",
        harness_id="aether",
        manifest_hash=sha,
        split=args.split,
        model_fingerprint=f"openai_compatible:{args.model}:local",
        seed=0,
        results=tuple(results),
        contained=not args.uncontained,
    )
    rate = resolve_rate(run)
    elapsed = time.monotonic() - started_all
    measured = [r for r in results if r.measured]
    print(
        f"\nresolved {sum(1 for r in results if r.resolved)}/{len(measured)} measured"
        f" ({'n/a' if rate is None else f'{rate:.0%}'})"
        f" · instrument errors {len(results) - len(measured)}"
        f" · {elapsed:.0f}s total"
        f" · spend ${sum(r.usd_micros for r in results) / 1_000_000:.4f}"
    )
    print("Not a benchmark: N is tiny, no family declared, nothing published.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--suite-dir", default=str(DEFAULT_SUITE_DIR))
    parser.add_argument("--workdir", default="/tmp/aether_local_check")
    parser.add_argument("--topology", default=str(REPO_ROOT / "workflows" / "linear_repair_v1.yaml"))
    parser.add_argument("--model", default="qwen2.5:1.5b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--split", default="dev", choices=["dev", "holdout", "sealed"])
    parser.add_argument("--max-tasks", type=int, default=3, help="downsample the manifest")
    parser.add_argument("--sample-seed", type=int, default=0)
    parser.add_argument("--usd-cap", type=float, default=None, help="hard per-run ceiling in USD")
    parser.add_argument("--entry-files", nargs="*", default=None)
    parser.add_argument("--runtime", default="docker", choices=["podman", "docker"])
    parser.add_argument("--uncontained", action="store_true")
    parser.add_argument("--instructions", default=None)
    args = parser.parse_args(argv)
    Path(args.workdir).mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(Path(args.manifest).read_text(encoding="utf-8"))
    return asyncio.run(main_async(args, manifest))


if __name__ == "__main__":
    raise SystemExit(main())
