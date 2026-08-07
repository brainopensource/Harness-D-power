"""Typed event catalog (TASK-022, spec.md §8) — generated docs, CI drift-
checked via `scripts/gen_aether_event_catalog.py --check`.

M1a-minimal: the seven events the walking skeleton's executor and dispatcher
actually emit this sprint. Events never schedule nodes (spec.md §8) — this is
an observational record, not a control-flow mechanism. `EVENT_TYPES` is the
single source of truth both the generated doc and the drift check read from;
edit here, not the doc.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime

from aether.domain.budget import BudgetOverrun
from aether.domain.gate import GateReport
from aether.domain.ids import Frozen, NodeId, RunId, TaskId


class RunStarted(Frozen):
    kind: Literal["run_started"] = "run_started"
    run_id: RunId
    at: AwareDatetime
    task_id: TaskId


class NodeStarted(Frozen):
    kind: Literal["node_started"] = "node_started"
    run_id: RunId
    at: AwareDatetime
    node_id: NodeId


class NodeCompleted(Frozen):
    kind: Literal["node_completed"] = "node_completed"
    run_id: RunId
    at: AwareDatetime
    node_id: NodeId
    status: Literal["ok", "error"]


class EffectDispatched(Frozen):
    kind: Literal["effect_dispatched"] = "effect_dispatched"
    run_id: RunId
    at: AwareDatetime
    effect_class: str
    status: Literal["ok", "denied", "budget_denied"]


class BudgetOverrunEmitted(Frozen):
    kind: Literal["budget_overrun_emitted"] = "budget_overrun_emitted"
    run_id: RunId
    at: AwareDatetime
    overrun: BudgetOverrun


class GateReportEmitted(Frozen):
    kind: Literal["gate_report_emitted"] = "gate_report_emitted"
    run_id: RunId
    at: AwareDatetime
    node_id: NodeId
    report: GateReport


class RunCompleted(Frozen):
    kind: Literal["run_completed"] = "run_completed"
    run_id: RunId
    at: AwareDatetime
    final_status: Literal["passed", "failed", "none", "error"]


Event = (
    RunStarted
    | NodeStarted
    | NodeCompleted
    | EffectDispatched
    | BudgetOverrunEmitted
    | GateReportEmitted
    | RunCompleted
)

# Order here is the order the generated doc lists them in — lifecycle first,
# then per-node, then per-effect, then terminal.
EVENT_TYPES: tuple[type[Frozen], ...] = (
    RunStarted,
    NodeStarted,
    NodeCompleted,
    EffectDispatched,
    BudgetOverrunEmitted,
    GateReportEmitted,
    RunCompleted,
)
