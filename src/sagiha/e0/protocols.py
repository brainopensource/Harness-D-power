"""E0-internal seams — not hexagonal ports.

`Harvester`/`BenchmarkRunner`/`StatisticalAnalyzer` in this package are concrete, CLI-wired classes
that import `sagiha.agency` and `sagiha.composition` to drive real coding runs — the `layers` import
contract (`.importlinter`) forbids `sagiha.adapters` from doing that, so these Protocols cannot be
hexagonal ports the way `CandidateSearch` or `Workspace` are (no adapter package could ever import
them). They get the same treatment `ExchangeCompactor` gets in `agency/context/compactor.py`:
package-internal swap seams, defined next to the class that will someday need one.

See ADR-0024 for why `adapters/benchmark/` and `ports/benchmark.py` were deleted rather than kept as
the "real" hexagonal home for this behavior.
"""

from __future__ import annotations

from typing import Protocol

from sagiha.domain.benchmark import (
    BenchmarkRun,
    BenchmarkSuite,
    ComparisonResult,
    HarvestedTask,
    NoiseFloor,
    TaskValidation,
)


class TaskHarvester(Protocol):
    """Mines a repository's commit history for evaluation tasks and validates them."""

    async def harvest_suite(self, suite_id: str = ...) -> BenchmarkSuite: ...

    async def validate_task(self, task: HarvestedTask) -> TaskValidation:
        """True iff `base_commit` reverts cleanly, the failing test reproduces, and repeated
        reruns of that failure are deterministic (no flakes admitted into a pinned suite)."""
        ...


class SuiteRunner(Protocol):
    """Runs an agent against every task in a suite and collects results."""

    async def run_suite(self, *, run_id: str | None = ..., k: int = ...) -> BenchmarkRun: ...


class StatisticalTest(Protocol):
    """A paired statistical comparison between two `BenchmarkRun`s over the same suite."""

    def compute_noise_floor(self, run_a: BenchmarkRun, run_b: BenchmarkRun) -> NoiseFloor: ...

    def compare_runs(self, control: BenchmarkRun, treatment: BenchmarkRun) -> ComparisonResult: ...
