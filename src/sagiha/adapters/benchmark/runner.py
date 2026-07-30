"""Local task runner — runs the agent against a single task in an isolated workspace.

SENIOR TODO: Workspace isolation (worktree per task), agent invocation via RunLoop,
             cost tracking, timeout enforcement.
"""

from __future__ import annotations

import logging
import uuid

from sagiha.domain.benchmark import (
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkSuite,
    HarvestedTask,
)

logger = logging.getLogger(__name__)


class LocalTaskRunner:
    """Runs agent against harvested tasks locally."""

    async def run_task(self, task: HarvestedTask, agent_id: str) -> BenchmarkResult:
        """Run the agent against a single task.

        SENIOR TODO: Create isolated worktree, checkout base_commit,
        invoke RunLoop with task goal, evaluate result, collect cost.
        """
        return BenchmarkResult(
            task_id=task.task_id,
            agent_id=agent_id,
            resolved=False,
            error="Not implemented — awaiting senior implementation",
        )

    async def run_suite(self, suite: BenchmarkSuite, agent_id: str) -> BenchmarkRun:
        """Run agent against all tasks in a suite.

        SENIOR TODO: Parallel execution with governor budget limits,
        result aggregation, statistical summary.
        """
        results: list[BenchmarkResult] = []
        for task in suite.tasks:
            result = await self.run_task(task, agent_id)
            results.append(result)

        return BenchmarkRun(
            run_id=str(uuid.uuid4()),
            suite_id=suite.suite_id,
            agent_id=agent_id,
            results=tuple(results),
            status="completed",
        )
