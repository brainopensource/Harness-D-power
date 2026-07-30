"""Task specs, acceptance, and gates — see docs/03-contracts-and-models/domain-schemas.md#work--evaluation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from sagiha.domain.control import TaskStatus


class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    description: str  # human-readable; enters the prompt
    check: str  # machine-executable, run via Toolchain
    required: bool = True  # non-required criteria rank but never admit


class TaskSpec(BaseModel):
    """Amended by revision, never mutation — a mid-run goal change produces a new TaskSpec."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    revision: int = 0
    goal: str
    acceptance: tuple[AcceptanceCriterion, ...]
    profile: str = "coding"  # execution profile; resolved at composition, not an enum
    parent_task_id: str | None = None
    status: TaskStatus = "submitted"


class CostSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    usd: float
    input_tokens: int
    output_tokens: int
    wall_clock_s: float
    model_calls: int


class CriterionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    description: str
    check: str
    passed: bool
    required: bool
    output: str = ""
    duration_ms: float = 0.0


class GateReport(BaseModel):
    """Hard gates are separate from soft scores — proxies rank candidates but never admit one."""

    model_config = ConfigDict(frozen=True)

    criteria: tuple[CriterionResult, ...]
    # Code-specific gates. None means "not applicable under this profile" —
    # never defaulted to True, which would read as "passed".
    no_new_suppressions: bool | None = None
    tests_unmodified: bool | None = None
    coverage_not_decreased: bool | None = None
    diff_within_bounds: bool | None = None

    @property
    def acceptance_met(self) -> bool:
        return all(c.passed for c in self.criteria if c.required)

    @property
    def admitted(self) -> bool:
        """Admit only when every coding gate is an explicit True.

        `None` means "not evaluated" — never a pass. Absence of a verdict must
        never be representable as admission (D20).
        """
        gates = (
            self.no_new_suppressions,
            self.tests_unmodified,
            self.coverage_not_decreased,
            self.diff_within_bounds,
        )
        return self.acceptance_met and all(g is True for g in gates)


class ReviewFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    line: int | None = None
    severity: Literal["blocker", "major", "minor", "nit"]
    category: Literal["correctness", "design", "readability", "test-quality", "security"]
    summary: str


class ReviewReport(BaseModel):
    """Never enters GateReport — a soft score that can admit is not a soft score."""

    model_config = ConfigDict(frozen=True)

    score: float  # 0-1, ranks only
    findings: tuple[ReviewFinding, ...]
    judge_model: str  # must differ from the generating model
    rubric_version: str


class Edit(BaseModel):
    model_config = ConfigDict(frozen=True)

    old_string: str  # unique anchor; empty == insert at start
    new_string: str
    expected_occurrences: int = 1


class EditRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    edits: tuple[Edit, ...]


class HunkResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    applied: bool
    index: int
    reason: (
        Literal["ok", "anchor_not_found", "ambiguous_anchor", "skipped_after_failure", "syntax_invalid"]
        | None
    ) = None
    nearest_match: str | None = None


class EditResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    hunks: tuple[HunkResult, ...]
    syntax_valid: bool


class Prediction(BaseModel):
    """AOI outputs are never bare floats — a scalar carries no basis for deciding if it may be acted on."""

    model_config = ConfigDict(frozen=True)

    value: float
    confidence: float
    calibrated: bool
    shadow_mode: bool


class SubagentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    goal: str
    outcome: Literal["success", "failure", "partial", "timeout"]
    diff_summary: str
    artifacts: tuple[str, ...] = ()
    cost: CostSummary
    gate_result: GateReport | None = None
