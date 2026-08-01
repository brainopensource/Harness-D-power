"""`CandidateSearch` adapter-internal seams — not hexagonal ports.

`CandidateExecutor` and `CandidateScorer` are consumed only by `CandidateSearch` v2 adapters
(`best_of_n.py`, `sequential.py`) inside this package, the same treatment
`agency/context/compactor.py`'s `ExchangeCompactor` gets: real extension points with real
conformance value, without the versioning overhead of a hexagonal port that only ever has one
family of consumer. See `docs/implementation/sprint_v2_s4_options.md` §2.1.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from sagiha.domain.control import RunContext
from sagiha.domain.events import Event
from sagiha.domain.work import CostSummary, GateReport, ReviewReport, TaskSpec


class EventEmitter(Protocol):
    """Structural stand-in for `kernel.bus.EventBus` — `sagiha.adapters` may not import
    `sagiha.kernel` (the `layers` import contract). Composition-root code passes the real
    `EventBus` in; it satisfies this shape without this module ever naming it."""

    async def emit(self, event: Event) -> None: ...


class CandidateOutcome(BaseModel):
    """Everything one Best-of-N candidate produced — the unit `BestOfNSearch` ranks and selects
    over. Frozen: an outcome is a record of what happened, not a place to accumulate state."""

    model_config = ConfigDict(frozen=True)

    branch_id: str
    run_id: str
    worktree_ref: str
    gate_report: GateReport | None = None
    review: ReviewReport | None = None
    cost: CostSummary | None = None
    steps: int = 0
    wall_clock_s: float = 0.0
    #: sha256 of `git diff` against the candidate's base — the machine-checkable signal for
    #: "did this candidate actually produce a different answer" (diversity_ratio, S4.2d).
    diff_digest: str = ""
    #: `git diff --numstat` totals, for the deterministic composite scorer's diff penalty and
    #: for the escalation ladder's `escalate_on_files`/`escalate_on_diff_lines` thresholds.
    files_changed: int = 0
    diff_lines: int = 0
    #: The sampling temperature this candidate was launched at (S4.2d's diversity ladder).
    temperature: float = 0.0
    #: Which repair round produced this outcome (0 = first attempt).
    repair_round: int = 0


class CandidateExecutor(Protocol):
    """Runs one Best-of-N candidate to completion in its own worktree.

    A `BestOfNSearch` adapter owns *policy* (how many candidates, pruning, repair, ranking);
    the executor owns *mechanism* (materialize a worktree, drive a `RunLoop`, tear down). This
    split is what lets the sequential and parallel launch strategies (S4.2b/S4.2c) share one
    executor implementation and differ only in how many run concurrently.
    """

    async def execute(
        self,
        task: TaskSpec,
        context: RunContext,
        *,
        branch_id: str,
        base_commit: str,
        temperature: float | None = None,
        repair_round: int = 0,
    ) -> CandidateOutcome: ...


class CandidateScorer(Protocol):
    """Ranks a `CandidateOutcome` — never admits. See `docs/03-contracts-and-models/domain-schemas.md`:
    a soft score that can admit is not a soft score. `adapters/search/scoring.py` (S4.3) is the
    implementer; this Protocol is declared here so `BestOfNSearch` can depend on the shape
    without depending on any particular scoring backend."""

    async def score(self, task: TaskSpec, outcome: CandidateOutcome) -> ReviewReport: ...
