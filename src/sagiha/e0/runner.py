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

logger = logging.getLogger(__name__)


class BenchmarkRunnerError(RuntimeError):
    """Base exception for benchmark runner failures."""


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

        try:
            mode_val = cast(Literal["live", "replay", "record"], self._model_mode)
            config = Config(
                model=ModelConfig(mode=mode_val),
                workspace=WorkspaceConfig(root=self._workspace_root),
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

            resolved_ws = str(await anyio.Path(self._workspace_root).resolve())
            ctx = RunContext(
                run_id=run_id,
                autonomy_level=config.autonomy.level,
                workspace_root=resolved_ws,
                budget_remaining_usd=config.governor.max_spend_usd_per_run,
            )

            loop_result = await loop.run(task_spec, ctx)
            elapsed = time.monotonic() - start_time

            return BenchmarkResult(
                task_id=task.task_id,
                agent_id=self._agent_id,
                resolved=loop_result.gate_report.admitted,
                gate_report=loop_result.gate_report,
                cost=None,
                steps=len(loop_result.steps),
                wall_clock_s=elapsed,
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

    async def run_suite(self, run_id: str | None = None) -> BenchmarkRun:
        actual_run_id = run_id or str(uuid.uuid4())
        results: list[BenchmarkResult] = []

        for task in self._suite.tasks:
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
