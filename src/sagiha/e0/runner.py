"""Benchmark task runner — executes an agent against a manifest/suite of tasks (E0 / Block 2)."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Literal, cast

import anyio

from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.composition import build_kernel
from sagiha.domain.benchmark import BenchmarkResult, BenchmarkRun, BenchmarkSuite, HarvestedTask
from sagiha.domain.config import Config, ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.control import RunContext
from sagiha.domain.identity import utc_now
from sagiha.domain.work import GateReport

logger = logging.getLogger(__name__)

#: `GateReport.required_gates`, in the order the reporter's failure breakdown attributes a
#: multi-gate failure to a single "first cause" — deterministic, so the same run always
#: attributes the same way.
_GATE_ATTRIBUTION_ORDER = (
    "tests_unmodified",
    "diff_within_bounds",
    "no_new_suppressions",
    "coverage_not_decreased",
)


class BenchmarkRunnerError(RuntimeError):
    """Base exception for benchmark runner failures."""


def _first_gate_failure(gate_report: GateReport) -> str | None:
    """The first required gate that reports an explicit `False`, in a fixed attribution order.

    `None` means either the run resolved, or every non-passing gate reported `None` (could not
    be evaluated) rather than an explicit failure — those two cases are distinguishable by
    `BenchmarkResult.resolved`, not by this field.
    """
    for name in _GATE_ATTRIBUTION_ORDER:
        if name in gate_report.required_gates and getattr(gate_report, name, None) is False:
            return name
    return None


class BenchmarkRunner:
    """Runs an agent over a benchmark suite, evaluating per-task admission and recording metrics."""

    def __init__(
        self,
        suite: BenchmarkSuite,
        *,
        agent_id: str = "sagiha",
        model_mode: Literal["live", "replay", "record"] = "replay",
        cassette_path: str | None = None,
        workspace_root: str | None = None,
        trajectory_db: str = ".sagiha/trajectories.db",
        max_steps: int = 20,
    ) -> None:
        self._suite = suite
        self._agent_id = agent_id
        self._model_mode = model_mode
        self._cassette_path = cassette_path or ".sagiha/cassettes/default.json"
        self._workspace_root = workspace_root or suite.repo
        self._trajectory_db = trajectory_db
        self._max_steps = max_steps

    async def run_single_task(self, task: HarvestedTask) -> BenchmarkResult:
        run_id = str(uuid.uuid4())
        start_time = time.monotonic()

        from sagiha.adapters.workspace.worktree import GitWorktreeManager

        manager = GitWorktreeManager(self._workspace_root)
        branch_id = f"bench-{task.task_id}-{run_id[:8]}"
        allocated = False

        try:
            await manager.allocate(task.base_commit, branch_id, run_id=run_id)
            allocated = True
            # `Workspace` (the port) deliberately has no path accessor — `path_for` is a
            # concrete-class-only escape hatch for exactly this caller, which must rebuild a
            # `Kernel` bound to the worktree's real filesystem location.
            task_root = str(await anyio.Path(manager.path_for(branch_id)).resolve())

            mode_val = cast(Literal["live", "replay", "record"], self._model_mode)
            config = Config(
                model=ModelConfig(mode=mode_val),
                workspace=WorkspaceConfig(root=task_root),
                telemetry=TelemetryConfig(trajectory_db=self._trajectory_db),
            )
            kernel = build_kernel(config, cassette_path=self._cassette_path)

            loop = RunLoop(
                model_provider=kernel.model_provider,
                policy_engine=kernel.policy_engine,
                resource_governor=kernel.resource_governor,
                tool_registry=kernel.tool_registry,
                trajectory_store=kernel.trajectory_store,
                bus=kernel.bus,
                max_steps=self._max_steps,
                tool_schemas=list(kernel.tool_schemas),
                evaluator=kernel.evaluator,
                workspace=kernel.workspace,
                pricing=kernel.config.pricing,
                context=kernel.config.context,
            )

            task_spec = make_task(
                goal=f"Fix issue: {task.diff_summary}",
                checks=[task.failing_test_cmd],
                task_id=run_id,
            )

            ctx = RunContext(
                run_id=run_id,
                autonomy_level=config.autonomy.level,
                workspace_root=task_root,
                budget_remaining_usd=config.governor.max_spend_usd_per_run,
                # The task's own base_commit, not a self-checkpoint of whatever the worktree
                # happens to be on — the gates must diff against the task's recorded baseline.
                base_commit=task.base_commit,
            )

            loop_result = await loop.run(task_spec, ctx)
            elapsed = time.monotonic() - start_time

            cache_read_total = sum(step.usage.cache_read_tokens for step in loop_result.steps)
            input_total = sum(step.usage.input_tokens for step in loop_result.steps)
            cache_hit = (cache_read_total > 0) if input_total > 0 else None

            return BenchmarkResult(
                task_id=task.task_id,
                agent_id=self._agent_id,
                resolved=loop_result.gate_report.admitted,
                gate_report=loop_result.gate_report,
                cost=loop_result.cost,
                steps=len(loop_result.steps),
                wall_clock_s=elapsed,
                gate_failure_kind=(
                    None if loop_result.gate_report.admitted else _first_gate_failure(loop_result.gate_report)
                ),
                cache_hit=cache_hit,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            logger.error("Benchmark task %s failed with exception: %s", task.task_id, exc)
            return BenchmarkResult(
                task_id=task.task_id,
                agent_id=self._agent_id,
                resolved=False,
                gate_report=None,
                cost=None,
                steps=0,
                wall_clock_s=elapsed,
                error=str(exc),
            )
        finally:
            if allocated:
                await manager.release(branch_id, run_id=run_id)

    async def run_suite(self, run_id: str | None = None, *, k: int = 1) -> BenchmarkRun:
        """Run the full suite once, or `k` times per task when `k > 1`.

        `k >= 3` is the plan's own requirement for reporting variance rather than a point
        estimate (`docs/06-guides-and-patterns/running-benchmarks.md` rule 1). Each repetition
        of a task gets its own worktree and its own `run_id` internally; all repetitions land
        in one flat `BenchmarkRun.results` tuple, distinguishable by `task_id` recurring `k`
        times — the reporter aggregates by grouping on it.
        """
        actual_run_id = run_id or str(uuid.uuid4())
        results: list[BenchmarkResult] = []

        for task in self._suite.tasks:
            for _ in range(max(1, k)):
                result = await self.run_single_task(task)
                results.append(result)

        return BenchmarkRun(
            run_id=actual_run_id,
            suite_id=self._suite.suite_id,
            agent_id=self._agent_id,
            results=tuple(results),
            status="completed",
            started_at=utc_now(),
            completed_at=utc_now(),
        )
