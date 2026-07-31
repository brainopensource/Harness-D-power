"""Export eligibility — the four criteria from `trace-distillation.md`, no exceptions.

A trajectory is exportable iff `admitted ∧ replay-verified ∧ ¬tainted ∧ within-budget`. Every
criterion is an explicit `bool | None`, mirroring the `GateReport` doctrine: absence of a verdict
must never be representable as a pass. The taint criterion in particular is "the one most likely
to be dropped under dataset-size pressure. It is the one least safe to drop" (trace-distillation.md)
— this module makes dropping it require deliberately overriding `eligible`, not merely forgetting
to check.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from sagiha.domain.events import Event, GateEvaluated, ReplayVerified
from sagiha.domain.trajectory import RunRecord, TrajectoryStep


class RunEligibility(BaseModel):
    """Frozen verdict for one run. `reasons()` is what the exporter's ledger prints — honest
    negatives (excluded runs, and why) are deliverables, not noise to suppress."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    admitted: bool | None
    tainted: bool | None
    within_budget: bool | None
    replay_verified: bool | None

    @property
    def eligible(self) -> bool:
        return (
            self.admitted is True
            and self.tainted is False
            and self.within_budget is True
            and self.replay_verified is True
        )

    def reasons(self) -> tuple[str, ...]:
        """Which criteria failed or were unevaluated — empty iff `eligible`."""
        out: list[str] = []
        if self.admitted is not True:
            out.append(f"admitted={self.admitted}")
        if self.tainted is not False:
            out.append(f"tainted={self.tainted}")
        if self.within_budget is not True:
            out.append(f"within_budget={self.within_budget}")
        if self.replay_verified is not True:
            out.append(f"replay_verified={self.replay_verified}")
        return tuple(out)


def _last_gate_admitted(events: list[Event]) -> bool | None:
    """The last `GateEvaluated` event's `gate_report.admitted` — `None` if no such event exists
    (an ungated profile, or a run that never reached evaluation). Never assumed `True`."""
    gate_events = [e for e in events if isinstance(e, GateEvaluated)]
    if not gate_events:
        return None
    return gate_events[-1].gate_report.admitted


def _any_taint(steps: list[TrajectoryStep]) -> bool:
    """`ToolResult.trusted` defaults to `False`, and that default is the security property
    (`domain/content.py`) — so `any(not r.trusted ...)` is the durable, storage-level signal for
    taint, independent of `DefaultPolicyEngine._tainted_runs`, which is in-process only and does
    not survive a restart."""
    return any(not result.trusted for step in steps for result in step.tool_results)


def _replay_verified(events: list[Event]) -> bool | None:
    """`True` iff a `ReplayVerified` event exists for this run; `None` otherwise — absence is
    not "not verified", it is "never checked", and the exporter treats both as ineligible via
    the `is not True` comparison in `eligible`, but the ledger reports them distinctly."""
    if any(isinstance(e, ReplayVerified) for e in events):
        return True
    return None


def assess(record: RunRecord, steps: list[TrajectoryStep], events: list[Event]) -> RunEligibility:
    """Derive a `RunEligibility` purely from what the `TrajectoryStore` already persisted —
    no live model calls, no re-execution. `record.status` carries budget-park state directly:
    `RunLoop` sets it to `"input-required"` on budget exhaustion (`agency/run_loop.py`), so
    within-budget is `record.status == "completed"` — `"failed"` (stuck/error) and
    `"input-required"` (parked) are both excluded, for different reasons a caller may want to
    distinguish via `record.status` itself.
    """
    return RunEligibility(
        run_id=record.run_id,
        admitted=_last_gate_admitted(events),
        tainted=_any_taint(steps),
        within_budget=record.status == "completed",
        replay_verified=_replay_verified(events),
    )
