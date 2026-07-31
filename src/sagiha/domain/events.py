"""Event bus registry — see docs/04-workflows-and-loops/event-catalog.md.

Generates docs/04-workflows-and-loops/event-catalog.md via scripts/gen_event_catalog.py — that
file is derived from this module, not hand-maintained. See docs/implementation/contracts-to-code.md.

Naming convention: `group.past_tense`. Events describe what happened, never what should happen.
`replay_relevant` mirrors the catalog's Replay column: `sagiha replay --verify-all` asserts on
those events; the rest are fire-and-observe. `emitted_by`/`consumers` carry the narrative that
would otherwise be lost when the hand-written catalog is deleted — consumers use the abbreviations
from the catalog: TS TrajectoryStore, OT OTel exporter, UI TUI/SSE/A2A streamers, HK user hooks,
GV ResourceGovernor, MI MetaImprover / trajectory mining.
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
    group: ClassVar[str] = "Lifecycle"
    emitted_by: ClassVar[str] = ""
    consumers: ClassVar[tuple[str, ...]] = ()


# --- Lifecycle ---


class RunStarted(Event):
    event: Literal["run.started"] = "run.started"
    task: TaskSpec
    run_context: RunContext
    profile: str
    extension_manifest: tuple[str, ...] = ()

    emitted_by: ClassVar[str] = "Orchestrator"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "MI")


class RunCompleted(Event):
    event: Literal["run.completed"] = "run.completed"
    gate_report: GateReport | None
    cost: CostSummary

    emitted_by: ClassVar[str] = "Orchestrator"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK", "MI")


class RunFailed(Event):
    event: Literal["run.failed"] = "run.failed"
    error_kind: str
    disposition: Disposition
    message: str

    emitted_by: ClassVar[str] = "Orchestrator"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK")


class RunCanceled(Event):
    event: Literal["run.canceled"] = "run.canceled"
    reason: str
    canceled_by: str

    emitted_by: ClassVar[str] = "Orchestrator"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI")


class CheckpointCreated(Event):
    event: Literal["checkpoint.created"] = "checkpoint.created"
    label: str
    commit_sha: str

    emitted_by: ClassVar[str] = "Workspace"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "UI")


# --- Reasoning ---


class StepStarted(Event):
    event: Literal["step.started"] = "step.started"

    group: ClassVar[str] = "Reasoning"
    emitted_by: ClassVar[str] = "Orchestrator"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI")


class ModelCallStarted(Event):
    event: Literal["model.call_started"] = "model.call_started"
    model: str
    request_digest: str
    cache_breakpoints: tuple[int, ...] = ()

    group: ClassVar[str] = "Reasoning"
    emitted_by: ClassVar[str] = "ModelProvider"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "GV")


class ModelDelta(Event):
    event: Literal["model.delta"] = "model.delta"
    frame: StreamEvent

    replay_relevant: ClassVar[bool] = False
    group: ClassVar[str] = "Reasoning"
    emitted_by: ClassVar[str] = "ModelProvider"
    consumers: ClassVar[tuple[str, ...]] = ("UI",)


class ModelCallCompleted(Event):
    event: Literal["model.call_completed"] = "model.call_completed"
    usage: TokenUsage
    stop_reason: str
    cost: CostSummary

    group: ClassVar[str] = "Reasoning"
    emitted_by: ClassVar[str] = "ModelProvider"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "GV", "MI")


class StepCompleted(Event):
    event: Literal["step.completed"] = "step.completed"
    step: TrajectoryStep

    group: ClassVar[str] = "Reasoning"
    emitted_by: ClassVar[str] = "Orchestrator"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "MI")


class StepScoredEvent(Event):
    """Wraps the domain.trajectory.StepScored record — never written back into a stored step."""

    event: Literal["step.scored"] = "step.scored"
    scored: StepScored

    replay_relevant: ClassVar[bool] = False
    group: ClassVar[str] = "Reasoning"
    emitted_by: ClassVar[str] = "Evaluator / Reviewer / AOI"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "MI")


# --- Tools ---


class ToolCallRequested(Event):
    event: Literal["tool.call_requested"] = "tool.call_requested"
    call: ToolCall

    group: ClassVar[str] = "Tools"
    emitted_by: ClassVar[str] = "Agency"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK")


class ToolCallAuthorized(Event):
    """Never carries a Grant — see docs/02-architecture/car-model.md."""

    event: Literal["tool.call_authorized"] = "tool.call_authorized"
    decision: Decision

    group: ClassVar[str] = "Tools"
    emitted_by: ClassVar[str] = "PolicyEngine"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "HK")


class ToolCallDenied(Event):
    event: Literal["tool.call_denied"] = "tool.call_denied"
    decision: Decision
    reason: str
    requires_human: bool

    group: ClassVar[str] = "Tools"
    emitted_by: ClassVar[str] = "PolicyEngine"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK")


class ToolCallCompleted(Event):
    event: Literal["tool.call_completed"] = "tool.call_completed"
    call_id: str
    result: ToolResult
    duration_ms: float

    group: ClassVar[str] = "Tools"
    emitted_by: ClassVar[str] = "Dispatch"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK", "MI")


class ToolCallFailed(Event):
    event: Literal["tool.call_failed"] = "tool.call_failed"
    call_id: str
    error_kind: str
    disposition: Disposition

    group: ClassVar[str] = "Tools"
    emitted_by: ClassVar[str] = "Dispatch"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK")


class TaintIntroduced(Event):
    """An untrusted tool output entered the run, taints it monotonically (T7).

    Emitted once per untrusted result, not once per run, so a trajectory shows exactly
    which call introduced the taint that later refused a mutation.
    """

    event: Literal["tool.taint_introduced"] = "tool.taint_introduced"
    call_id: str
    tool_name: str
    #: What the envelope's `source=` attribute was set to.
    source: str

    group: ClassVar[str] = "Tools"
    emitted_by: ClassVar[str] = "Dispatch"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK", "MI")


# --- Context ---


class CompactionApplied(Event):
    """The context window was compacted at a deliberate checkpoint.

    Replay-relevant: a replayed run must compact at the same step, or its requests diverge
    from the recording after that point.
    """

    event: Literal["context.compaction_applied"] = "context.compaction_applied"
    exchanges_before: int
    exchanges_after: int
    tail_tokens_before: int
    tail_tokens_after: int
    #: Whether the summarized span contained untrusted content, and the summary therefore
    #: carries the `<untrusted-data>` envelope forward (T7 through compaction).
    tainted_span: bool = False

    group: ClassVar[str] = "Context"
    emitted_by: ClassVar[str] = "ContextAssembler"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "MI")


class ProviderFailover(Event):
    """The execution provider failed over to a role-level fallback (S3.4).

    Replay-relevant as a checkpoint: a resumed run must know which provider served which
    steps, and cross-provider resumes drop reasoning blocks whole-exchange.
    """

    event: Literal["model.provider_failover"] = "model.provider_failover"
    from_provider: str
    to_provider: str
    reason: str
    #: True when reasoning blocks were stripped from the request for the new provider.
    reasoning_dropped: bool = False

    group: ClassVar[str] = "Reasoning"
    emitted_by: ClassVar[str] = "FallbackModelAdapter"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "MI")


# --- Workspace ---


class EditApplied(Event):
    event: Literal["edit.applied"] = "edit.applied"
    result: EditResult

    group: ClassVar[str] = "Workspace"
    emitted_by: ClassVar[str] = "Workspace"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK", "MI")


class CommandExecuted(Event):
    event: Literal["command.executed"] = "command.executed"
    argv: tuple[str, ...]
    exit_code: int
    output: str
    truncated: bool = False
    full_output_uri: str | None = None

    group: ClassVar[str] = "Workspace"
    emitted_by: ClassVar[str] = "Workspace"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK")


class DiagnosticsChanged(Event):
    event: Literal["diagnostics.changed"] = "diagnostics.changed"
    added: tuple[DiagnosticItem, ...] = ()
    removed: tuple[DiagnosticItem, ...] = ()

    replay_relevant: ClassVar[bool] = False
    group: ClassVar[str] = "Workspace"
    emitted_by: ClassVar[str] = "LSPAdapter"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "MI")


class WorktreeAllocated(Event):
    event: Literal["worktree.allocated"] = "worktree.allocated"
    branch_id: str
    base_commit: str

    group: ClassVar[str] = "Workspace"
    emitted_by: ClassVar[str] = "WorktreeManager"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI")


class WorktreeReleased(Event):
    event: Literal["worktree.released"] = "worktree.released"
    branch_id: str
    disposition: str

    group: ClassVar[str] = "Workspace"
    emitted_by: ClassVar[str] = "WorktreeManager"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI")


class IndexUpdated(Event):
    event: Literal["index.updated"] = "index.updated"
    paths: tuple[str, ...]
    chunk_delta: int
    duration_s: float

    replay_relevant: ClassVar[bool] = False
    group: ClassVar[str] = "Workspace"
    emitted_by: ClassVar[str] = "Indexer"
    consumers: ClassVar[tuple[str, ...]] = ("OT", "UI")


# --- Evaluation & Control ---


class GateEvaluated(Event):
    """Never emitted with an empty GateReport — see execution-profiles.md."""

    event: Literal["gate.evaluated"] = "gate.evaluated"
    gate_report: GateReport

    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "Evaluator"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "HK", "MI")


class ReviewCompleted(Event):
    event: Literal["review.completed"] = "review.completed"
    review: ReviewReport

    replay_relevant: ClassVar[bool] = False
    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "Reviewer"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "MI", "UI")


class CandidateProposed(Event):
    event: Literal["candidate.proposed"] = "candidate.proposed"
    branch_id: str
    strategy: str
    budget_usd: float

    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "CandidateSearch"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI")


class CandidateSelected(Event):
    event: Literal["candidate.selected"] = "candidate.selected"
    branch_id: str
    gate_report: GateReport
    selection_basis: str
    #: `distinct_candidates / N` over the proposed batch (v2-S4 Epic S4.2d) — a validity
    #: precondition on the Best-of-N exit gate, not a score. Reported here (rather than a
    #: separate event) because `select()` is the one call site that already holds the full
    #: `branch_ids` batch a diversity ratio is computed over.
    diversity_ratio: float = 1.0

    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "CandidateSearch"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI")


class ApprovalRequested(Event):
    """The only event whose delivery blocks the run."""

    event: Literal["approval.requested"] = "approval.requested"
    action: str
    scope: tuple[str, ...]
    rationale: str
    blast_radius: str

    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "PolicyEngine"
    consumers: ClassVar[tuple[str, ...]] = ("UI", "HK (blocking)")


class ApprovalResolved(Event):
    event: Literal["approval.resolved"] = "approval.resolved"
    approved: bool
    resolved_by: str
    note: str = ""

    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "Entry point"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI")


class BudgetWarning(Event):
    event: Literal["budget.warning"] = "budget.warning"
    spent_usd: float
    remaining_usd: float
    projected_usd: float

    replay_relevant: ClassVar[bool] = False
    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "ResourceGovernor"
    consumers: ClassVar[tuple[str, ...]] = ("UI", "HK")


class BudgetExhausted(Event):
    event: Literal["budget.exhausted"] = "budget.exhausted"
    spent_usd: float
    limit_usd: float
    limit_kind: str

    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "ResourceGovernor"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "UI", "HK")


# --- Steering ---


class UserMessageReceived(Event):
    event: Literal["user.message_received"] = "user.message_received"
    text: str
    provenance: Literal[Provenance.OPERATOR] = Provenance.OPERATOR
    at_step: StepId | None = None

    group: ClassVar[str] = "Steering"
    emitted_by: ClassVar[str] = "Entry point"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI")


class TaskRevised(Event):
    event: Literal["task.revised"] = "task.revised"
    task: TaskSpec  # new revision
    supersedes: int  # prior revision number

    group: ClassVar[str] = "Steering"
    emitted_by: ClassVar[str] = "Orchestrator"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "MI")


class BenchmarkTaskHarvested(Event):
    event: Literal["benchmark.task_harvested"] = "benchmark.task_harvested"
    task_id: str
    repo: str

    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "Harvester"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI")


class BenchmarkTaskCompleted(Event):
    event: Literal["benchmark.task_completed"] = "benchmark.task_completed"
    task_id: str
    agent_id: str
    resolved: bool

    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "TaskRunner"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT", "UI", "MI")


class ReplayVerified(Event):
    """The cassette-recorded requests of `run_id` reproduce exactly under digest-checked replay.

    Emitted against the ORIGINAL run's `run_id` (the base `Event.run_id`), not the fresh
    ephemeral run `sagiha replay --verify` mints to perform the check — `replay_run_id` carries
    that one, for audit trail. Without this event, "replay-verified" (one of the exporter's four
    eligibility criteria, v2-S4 Epic S4.4) has no durable signal to check for a real run.
    """

    event: Literal["replay.verified"] = "replay.verified"
    replay_run_id: str

    group: ClassVar[str] = "Evaluation & Control"
    emitted_by: ClassVar[str] = "CLI"
    consumers: ClassVar[tuple[str, ...]] = ("TS", "OT")


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
    TaintIntroduced,
    CompactionApplied,
    ProviderFailover,
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
    BenchmarkTaskHarvested,
    BenchmarkTaskCompleted,
    ReplayVerified,
)
"""Source of truth for docs/04-workflows-and-loops/event-catalog.md — see scripts/gen_event_catalog.py."""
