#!/usr/bin/env python3
"""Cheap CI gate for the `sagiha bench --aa` machinery (v2-S7a, R0).

Builds a real one-commit git repo and a one-task suite, runs the replay-mode
A/A path (`BenchmarkRunner.run_suite` twice, `StatisticalAnalyzer.compute_noise_floor`)
against it, and asserts the pipeline completes and the task actually resolves —
not just that no exception was raised. A prior ad-hoc check of this exact code
path against a *fake* base_commit in a non-git tmp dir silently errored every
task (`git worktree add` failing) while still reporting `resolved: bool` and
`wall_clock_s > 0`, which is the false-success shape the project's honesty
doctrine exists to catch. This script is deliberately not a pytest test: it is
the CI-cheap stand-in for the real (expensive, human-run) A/A + ablation suite
that produces `docs/rationale/benchmarks/noise-floor.md` — see that doc and
`docs/implementation/planning_final_sprint_rev2.md` §4.1 for the real run.

    python3 scripts/bench_aa_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import anyio

from sagiha.adapters.model.cassette import CassetteEntry, request_digest
from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.composition import build_kernel
from sagiha.domain.benchmark import BenchmarkSuite, HarvestedTask
from sagiha.domain.config import Config, ModelConfig, SandboxConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.content import Message, ModelRequest, TextBlock
from sagiha.domain.control import RunContext
from sagiha.domain.trajectory import Completion, StreamEvent, TokenUsage
from sagiha.e0.runner import BenchmarkRunner
from sagiha.e0.statistics import StatisticalAnalyzer


class _StopImmediately:
    """Scripted one-turn, no-tool-call provider — records the exact request
    `BenchmarkRunner`'s single-shot arm assembles for this task, so the cassette
    generated below matches on replay by construction rather than by luck."""

    def __init__(self) -> None:
        self.recorded: list[tuple[ModelRequest, Message]] = []

    async def complete(self, request: ModelRequest) -> Completion:
        msg = Message(role="assistant", content=[TextBlock(text="Nothing to do.")])
        self.recorded.append((request, msg))
        return Completion(message=msg, usage=TokenUsage(input_tokens=0, output_tokens=0), model="cassette")

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


async def _generate_cassette(*, workspace_root: Path, cassette_path: Path, task: HarvestedTask) -> None:
    """Runs the real single-shot code path once with a scripted provider, then writes
    its exact request/response pair as a cassette entry — mirrors
    `scripts/gen_replay_fixture.py`, adapted to `BenchmarkRunner`'s task shape
    (`"Fix issue: {diff_summary}"` / `checks=[failing_test_cmd]`) rather than the
    CLI `replay` command's trivial one, since the two do not share a request digest.
    """
    await anyio.Path(cassette_path).write_text("[]", encoding="utf-8")
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(workspace_root)),
        telemetry=TelemetryConfig(trajectory_db=str(workspace_root / "traj.db")),
    )
    kernel = build_kernel(config, cassette_path=str(cassette_path), include_search=False)
    scripted = _StopImmediately()
    loop = RunLoop(
        model_provider=scripted,  # type: ignore[arg-type]
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        max_steps=kernel.config.governor.max_steps_per_run,
        tool_schemas=list(kernel.tool_schemas),
        evaluator=kernel.evaluator,
        workspace=kernel.workspace,
        pricing=kernel.config.pricing,
        context=kernel.config.context,
    )
    ctx = RunContext(
        run_id="cassette-gen",
        autonomy_level="interactive",
        workspace_root=str(workspace_root),
        budget_remaining_usd=config.governor.max_spend_usd_per_run,
        base_commit=task.base_commit,
    )
    task_spec = make_task(
        goal=f"Fix issue: {task.diff_summary}", checks=[task.failing_test_cmd], task_id="cassette-gen"
    )
    result = await loop.run(task_spec, ctx)
    if not result.gate_report.admitted:
        print(f"FAIL: cassette generation itself did not admit: {result.gate_report}", file=sys.stderr)
        raise SystemExit(1)

    entries = [
        CassetteEntry(request=req, response=resp, digest=request_digest(req)).model_dump(mode="json")
        for req, resp in scripted.recorded
    ]
    await anyio.Path(cassette_path).write_text(json.dumps(entries) + "\n", encoding="utf-8")


def _init_repo(root: Path) -> str:
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=root, check=True, capture_output=True, text=True)

    run("git", "init", "-q", ".")
    run("git", "config", "user.email", "smoke@sagiha.local")
    run("git", "config", "user.name", "bench-aa-smoke")
    (root / "a.py").write_text("x = 1\n")
    run("git", "add", "a.py")
    run("git", "commit", "-q", "-m", "init")
    return run("git", "rev-parse", "HEAD").stdout.strip()


async def _main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base_commit = _init_repo(root)

        task = HarvestedTask(
            task_id="smoke-1",
            repo=str(root),
            base_commit=base_commit,
            target_commit=base_commit,
            diff_summary="smoke task",
            failing_test_cmd="true",
            files_changed=("a.py",),
        )
        suite = BenchmarkSuite(suite_id="bench-aa-smoke", repo=str(root), tasks=(task,))

        cassette_path = root / "cassette.json"
        await _generate_cassette(workspace_root=root, cassette_path=cassette_path, task=task)

        # `runtime="subprocess"`: this is a cheap CI smoke check of the bench/statistics
        # pipeline, not a security-relevant run — the default `"container"` sandbox cannot
        # resolve a worktree's `.git` file (it points outside the mounted worktree leaf to
        # `<repo>/.git/worktrees/<id>`), which would report every coding-profile gate as
        # `None` here for a reason unrelated to what this gate is checking.
        runner = BenchmarkRunner(
            suite=suite,
            model_mode="replay",
            cassette_path=str(cassette_path),
            workspace_root=str(root),
            sandbox=SandboxConfig(runtime="subprocess"),
        )

        run_a = await runner.run_suite(run_id="aa-smoke-pass-1")
        run_b = await runner.run_suite(run_id="aa-smoke-pass-2")

        for label, run in (("pass-1", run_a), ("pass-2", run_b)):
            if len(run.results) != 1:
                print(f"FAIL: {label} produced {len(run.results)} result(s), expected 1", file=sys.stderr)
                return 1
            result = run.results[0]
            if result.error is not None:
                print(f"FAIL: {label} task errored: {result.error}", file=sys.stderr)
                return 1
            if not result.resolved:
                print(
                    f"FAIL: {label} task did not resolve (gate_report={result.gate_report})",
                    file=sys.stderr,
                )
                return 1

        floor = StatisticalAnalyzer.compute_noise_floor(run_a, run_b)
        print(f"bench-aa-smoke OK: mean_delta={floor.mean_delta:.4f} n={floor.n_tasks}")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
