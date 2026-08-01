"""Benchmark domain models — see docs/07-roadmap/phased-migration-matrix.md (E0 slice)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sagiha.domain.identity import utc_now
from sagiha.domain.work import CostSummary, GateReport


class HarvestedTask(BaseModel):
    """A task extracted from a real commit in the target repository."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    repo: str
    base_commit: str
    target_commit: str
    diff_summary: str
    failing_test_cmd: str
    files_changed: tuple[str, ...]
    #: Files under a test path in `target_commit`'s diff — retained (not reverted) by
    #: `validate_task` so the failing test can reproduce against the pre-fix source.
    test_files: tuple[str, ...] = ()
    #: Non-test files in the diff — reverted by `validate_task` to reproduce the failure.
    source_files: tuple[str, ...] = ()
    #: Set by `validate_task`. `False` (the default) means "not yet validated", not "invalid" —
    #: an un-validated task must never be counted toward the harvester's ≥30-task gate.
    validated: bool = False
    validation_reason: str | None = None
    harvested_at: datetime = Field(default_factory=utc_now)


class TaskValidation(BaseModel):
    """Result of `Harvester.validate_task` — the harvester's own honesty gate.

    A task is valid iff the base commit reverts cleanly, the failing test reproduces against
    the reverted source, and repeated reruns of that failure are deterministic. `passed=False`
    always carries a `reason`; there is no silent rejection.
    """

    model_config = ConfigDict(frozen=True)

    task_id: str
    passed: bool
    reason: str = ""
    #: How many times the failing test was rerun to probe for flakiness.
    determinism_runs: int = 1
    #: How many of those reruns actually failed (should equal `determinism_runs` for a valid task).
    determinism_failures: int = 0


class SuiteValidation(BaseModel):
    """Aggregate validation outcome for a `BenchmarkSuite` — the harvester validation gate."""

    model_config = ConfigDict(frozen=True)

    suite_id: str
    total_tasks: int
    valid_tasks: int
    min_tasks_required: int
    task_results: tuple[TaskValidation, ...]

    @property
    def passed(self) -> bool:
        """Meets `docs/07-roadmap/phased-migration-matrix.md`'s E0 slice gate: at least
        `min_tasks_required` valid tasks, and every valid task actually passed validation."""
        return self.valid_tasks >= self.min_tasks_required


class BenchmarkResult(BaseModel):
    """Result of running one agent against one harvested task."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    agent_id: str
    resolved: bool
    gate_report: GateReport | None = None
    cost: CostSummary | None = None
    steps: int = 0
    wall_clock_s: float = 0.0
    error: str | None = None
    #: Which required gate failed first, for the reporter's gate-failure breakdown. `None` when
    #: `resolved` (nothing to attribute) or when the run errored before any gate ran.
    gate_failure_kind: str | None = None
    #: Advisory cache-hit signal for this task's run, `None` when the provider did not report it.
    cache_hit: bool | None = None
    #: Which arm produced this result — `"single_shot"` (one run) or `"bon"` (Best-of-N over
    #: real worktrees). Recorded per-result so a comparison report can never silently pair two
    #: runs of the same arm and call it a treatment effect.
    strategy: str = "single_shot"
    #: `distinct_candidates / N` for the BoN arm (v2-S4 S4.2d) — `None` for single-shot, where
    #: N=1 makes the ratio meaningless rather than 1.0. A ratio at or near `1/N` invalidates
    #: the comparison: the candidates were one answer sampled N times, so any measured delta is
    #: a sampling artifact and BoN paid N× for single-shot's diversity.
    diversity_ratio: float | None = None
    #: Candidates actually proposed for this task under the BoN arm. `None` for single-shot.
    candidates: int | None = None


class BenchmarkSuite(BaseModel):
    """A pinned collection of tasks for reproducible evaluation."""

    model_config = ConfigDict(frozen=True)

    suite_id: str
    repo: str
    tasks: tuple[HarvestedTask, ...]
    created_at: datetime = Field(default_factory=utc_now)


class BenchmarkRun(BaseModel):
    """An execution of one agent against one suite."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    suite_id: str
    agent_id: str
    results: tuple[BenchmarkResult, ...]
    status: Literal["running", "completed", "failed"] = "running"
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class NoiseFloor(BaseModel):
    """Statistical noise floor for A/A baseline comparison — see `e0.statistics.bootstrap_ci`.

    `confidence_interval` is a real percentile-bootstrap interval over paired per-task deltas
    from two runs of the *unmodified* harness, seeded for reproducibility (H5 fix — it used to
    be `(0.0, mean_delta * 1.5)`, invented arithmetic with no statistical basis).
    """

    model_config = ConfigDict(frozen=True)

    manifest_id: str
    runs_per_task: int = 2
    mean_delta: float = 0.0
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    #: Bootstrap parameters — recorded so the CI is reproducible and auditable, not just stated.
    alpha: float = 0.05
    k_runs: int = 2
    n_tasks: int = 0
    seed: int = 0


class ComparisonResult(BaseModel):
    """Paired comparison result between treatment and control runs.

    H5 fix: `p_value` was a hardcoded `0.05` literal and `beats_noise_floor` was `delta > 0`,
    never consulting the noise floor at all. Both are now `None` when the comparison could not
    be honestly computed (e.g. fewer than 2 runs, or an empty/unpaired suite) — mirroring the
    `GateReport` doctrine that absence of a verdict must never be representable as a pass.
    """

    model_config = ConfigDict(frozen=True)

    control_agent_id: str
    treatment_agent_id: str
    delta_pass_rate: float
    #: Exact two-sided McNemar p-value over discordant pairs. `None` when not computed.
    p_value: float | None = None
    #: `p_value` after Holm–Bonferroni correction across the comparisons run in the same suite.
    adjusted_p_value: float | None = None
    #: Count of discordant pairs (control passed/treatment failed, or vice versa) McNemar used.
    n_discordant: int = 0
    #: Name of the test actually applied, e.g. "mcnemar_exact" — empty when nothing was computed.
    method: str = ""
    #: `None` is never a pass — computed only when the noise floor was itself computed and the
    #: comparison has enough discordant pairs to test.
    beats_noise_floor: bool | None = None
