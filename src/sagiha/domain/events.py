"""Event bus registry — see docs/04-workflows-and-loops/event-catalog.md.

Generates docs/04-workflows-and-loops/event-catalog.md via scripts/gen_event_catalog.py — that
file is derived from this module, not hand-maintained. See docs/implementation/contracts-to-code.md.

Naming convention: `group.past_tense`. Events describe what happened, never what should happen.
`replay_relevant` mirrors the catalog's Replay column: `sagiha replay --verify-all` asserts on
those events; the rest are fire-and-observe.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from sagiha.domain.content import ToolCall, ToolResult
from sagiha.domain.control import Decision, RunContext
from sagiha.domain.graph import DiagnosticItem
from sagiha.domain.identity import StepId, utc_now
from sagiha.domain.memory import Provenance
from sagiha.domain.trajectory import StepScored, StreamEvent, TokenUsage, TrajectoryStep
from sagiha.domain.work import CostSummary, EditResult, GateReport, ReviewReport, TaskSpec

Disposition = Literal["RETRY", "DEGRADE", "SURFACE", "ABORT"]
"""Every failure resolves to exactly one of these — see docs/03-contracts-and-models/error-taxonomy.md."""


class Event(BaseModel):
    """Base every bus event extends."""

    model_config = ConfigDict(frozen=True)

    event: str  # discriminator, e.g. "tool.call_requested"
    schema_version: int = 1  # bumped per event type, not globally
    run_id: str
    step_id: StepId | None = None
    timestamp: datetime = Field(default_factory=utc_now)

    replay_relevant: ClassVar[bool] = True


# --- Lifecycle ---


class RunStarted(Event):
    event: Literal["run.started"] = "run.started"
    task: TaskSpec
    run_context: RunContext
    profile: str
    extension_manifest: tuple[str, ...] = ()


class RunCompleted(Event):
    event: Literal["run.completed"] = "run.completed"
    gate_report: GateReport | None
    cost: CostSummary


class RunFailed(Event):
    event: Literal["run.failed"] = "run.failed"
    error_kind: str
    disposition: Disposition
    message: str


class RunCanceled(Event):
    event: Literal["run.canceled"] = "run.canceled"
    reason: str
    canceled_by: str


class CheckpointCreated(Event):
    event: Literal["checkpoint.created"] = "checkpoint.created"
    label: str
    commit_sha: str


# --- Reasoning ---


class StepStarted(Event):
    event: Literal["step.started"] = "step.started"


class ModelCallStarted(Event):
    event: Literal["model.call_started"] = "model.call_started"
    model: str
    request_digest: str
    cache_breakpoints: tuple[int, ...] = ()


class ModelDelta(Event):
    event: Literal["model.delta"] = "model.delta"
    frame: StreamEvent

    replay_relevant: ClassVar[bool] = False


class ModelCallCompleted(Event):
    event: Literal["model.call_completed"] = "model.call_completed"
    usage: TokenUsage
    stop_reason: str
    cost: CostSummary


class StepCompleted(Event):
    event: Literal["step.completed"] = "step.completed"
    step: TrajectoryStep


class StepScoredEvent(Event):
    """Wraps the domain.trajectory.StepScored record — never written back into a stored step."""

    event: Literal["step.scored"] = "step.scored"
    scored: StepScored

    replay_relevant: ClassVar[bool] = False


# --- Tools ---


class ToolCallRequested(Event):
    event: Literal["tool.call_requested"] = "tool.call_requested"
    call: ToolCall


class ToolCallAuthorized(Event):
    """Never carries a Grant — see docs/02-architecture/car-model.md."""

    event: Literal["tool.call_authorized"] = "tool.call_authorized"
    decision: Decision


class ToolCallDenied(Event):
    event: Literal["tool.call_denied"] = "tool.call_denied"
    decision: Decision
    reason: str
    requires_human: bool


class ToolCallCompleted(Event):
    event: Literal["tool.call_completed"] = "tool.call_completed"
    result: ToolResult
    duration_ms: float


class ToolCallFailed(Event):
    event: Literal["tool.call_failed"] = "tool.call_failed"
    error_kind: str
    disposition: Disposition


# --- Workspace ---


class EditApplied(Event):
    event: Literal["edit.applied"] = "edit.applied"
    result: EditResult


class CommandExecuted(Event):
    event: Literal["command.executed"] = "command.executed"
    argv: tuple[str, ...]
    exit_code: int
    output: str
    truncated: bool = False
    full_output_uri: str | None = None


class DiagnosticsChanged(Event):
    event: Literal["diagnostics.changed"] = "diagnostics.changed"
    added: tuple[DiagnosticItem, ...] = ()
    removed: tuple[DiagnosticItem, ...] = ()

    replay_relevant: ClassVar[bool] = False


class WorktreeAllocated(Event):
    event: Literal["worktree.allocated"] = "worktree.allocated"
    branch_id: str
    base_commit: str


class WorktreeReleased(Event):
    event: Literal["worktree.released"] = "worktree.released"
    branch_id: str
    disposition: str


class IndexUpdated(Event):
    event: Literal["index.updated"] = "index.updated"
    paths: tuple[str, ...]
    chunk_delta: int
    duration_s: float

    replay_relevant: ClassVar[bool] = False


# --- Evaluation & Control ---


class GateEvaluated(Event):
    """Never emitted with an empty GateReport — see execution-profiles.md."""

    event: Literal["gate.evaluated"] = "gate.evaluated"
    gate_report: GateReport


class ReviewCompleted(Event):
    event: Literal["review.completed"] = "review.completed"
    review: ReviewReport

    replay_relevant: ClassVar[bool] = False


class CandidateProposed(Event):
    event: Literal["candidate.proposed"] = "candidate.proposed"
    branch_id: str
    strategy: str
    budget_usd: float


class CandidateSelected(Event):
    event: Literal["candidate.selected"] = "candidate.selected"
    branch_id: str
    gate_report: GateReport
    selection_basis: str


class ApprovalRequested(Event):
    """The only event whose delivery blocks the run."""

    event: Literal["approval.requested"] = "approval.requested"
    action: str
    scope: tuple[str, ...]
    rationale: str
    blast_radius: str


class ApprovalResolved(Event):
    event: Literal["approval.resolved"] = "approval.resolved"
    approved: bool
    resolved_by: str
    note: str = ""


class BudgetWarning(Event):
    event: Literal["budget.warning"] = "budget.warning"
    spent_usd: float
    remaining_usd: float
    projected_usd: float

    replay_relevant: ClassVar[bool] = False


class BudgetExhausted(Event):
    event: Literal["budget.exhausted"] = "budget.exhausted"
    spent_usd: float
    limit_usd: float
    limit_kind: str


# --- Steering ---


class UserMessageReceived(Event):
    event: Literal["user.message_received"] = "user.message_received"
    text: str
    provenance: Literal[Provenance.OPERATOR] = Provenance.OPERATOR
    at_step: StepId | None = None


class TaskRevised(Event):
    event: Literal["task.revised"] = "task.revised"
    task: TaskSpec  # new revision
    supersedes: int  # prior revision number


ALL_EVENTS: tuple[type[Event], ...] = (
    RunStarted,
    RunCompleted,
    RunFailed,
    RunCanceled,
    CheckpointCreated,
    StepStarted,
    ModelCallStarted,
    ModelDelta,
    ModelCallCompleted,
    StepCompleted,
    StepScoredEvent,
    ToolCallRequested,
    ToolCallAuthorized,
    ToolCallDenied,
    ToolCallCompleted,
    ToolCallFailed,
    EditApplied,
    CommandExecuted,
    DiagnosticsChanged,
    WorktreeAllocated,
    WorktreeReleased,
    IndexUpdated,
    GateEvaluated,
    ReviewCompleted,
    CandidateProposed,
    CandidateSelected,
    ApprovalRequested,
    ApprovalResolved,
    BudgetWarning,
    BudgetExhausted,
    UserMessageReceived,
    TaskRevised,
)
"""Source of truth for docs/04-workflows-and-loops/event-catalog.md — see scripts/gen_event_catalog.py."""
