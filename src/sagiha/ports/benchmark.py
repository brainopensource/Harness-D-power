"""Benchmark ports — commit-replay harvester and task runner for E0-lite.

See docs/07-roadmap/phased-migration-matrix.md (E0 slice) and
docs/08-decisions/0015-benchmark-target-repository.md.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.benchmark import (
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkSuite,
    HarvestedTask,
)

PORT_VERSION: Final = 1
STABILITY: Final = "experimental"


class CommitReplayHarvester(Protocol):
    """Mines a git repository's commit history for evaluation tasks."""

    async def harvest(self, repo_path: str, *, limit: int = 100) -> list[HarvestedTask]: ...

    async def validate_task(self, task: HarvestedTask, repo_path: str) -> bool:
        """Returns True if base_commit reverts cleanly and failing_test_cmd reproduces."""
        ...


class TaskRunner(Protocol):
    """Runs an agent against harvested tasks and collects results."""

    async def run_task(self, task: HarvestedTask, agent_id: str) -> BenchmarkResult: ...

    async def run_suite(self, suite: BenchmarkSuite, agent_id: str) -> BenchmarkRun: ...
