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
    harvested_at: datetime = Field(default_factory=utc_now)


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
    """Statistical noise floor for A/A baseline comparison."""

    model_config = ConfigDict(frozen=True)

    manifest_id: str
    runs_per_task: int = 2
    mean_delta: float = 0.0
    confidence_interval: tuple[float, float] = (0.0, 0.0)


class ComparisonResult(BaseModel):
    """Paired comparison result between treatment and control runs."""

    model_config = ConfigDict(frozen=True)

    control_agent_id: str
    treatment_agent_id: str
    delta_pass_rate: float
    p_value: float = 0.05
    beats_noise_floor: bool = True
