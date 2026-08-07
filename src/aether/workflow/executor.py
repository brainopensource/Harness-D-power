"""WorkflowExecutor (TASK-020 + TASK-023).

M1a scope was unconditional linear order. Sprint 3 adds the one conditional
construct ADR-0013 permits before M3: the **bounded repair edge**, executed as
a *static unroll*. `evaluate →(fail, k)→ repair → apply → evaluate` runs at
most `max_iterations` times; the graph the validator checked is still acyclic,
because the loop has a compile-time bound rather than a runtime condition that
could fail to terminate.

Routing rule, and the one that matters most (`measurement.md` §2 B4):

    PASSED  -> stop, this candidate resolved
    FAILED  -> repair, while iterations and budget remain
    NONE    -> stop. **Never repair.**

`NONE` is *unmeasured*, not *failed*. Routing it into repair would point the
single largest lever in the system at our own instrument bugs, and every
iteration it burned would look like ordinary work.

Budget: each iteration reserves its **own** parent lease from
`repair.budget_per_iteration`, and each node inside the iteration carves a
child lease from it (`kernel/governor.py` refunds a child's release to its
parent, not to the global pool). Exhausting the budget **ends the loop, not
the run** — the candidate keeps whatever verdict it last had.

Still out of scope: conditional edges in general and Best-of-N fan-out (M3,
TASK-035), and memoization (M2, TASK-032).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aether.domain.budget import BudgetDims
from aether.domain.events import NodeCompleted, NodeStarted, RepairIterationStarted
from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import LeaseId, NodeId, RunId
from aether.kernel.bus import EventBus
from aether.kernel.governor import ResourceGovernor
from aether.ports.resource_governor import ReservationDenied
from aether.workflow.step import StepContext, WorkflowStep


class WorkflowExecutionError(Exception):
    def __init__(self, node_id: str, cause: Exception) -> None:
        self.node_id = node_id
        self.cause = cause
        super().__init__(f"node '{node_id}' failed: {cause}")


def _budget_from(source: dict[str, Any] | None) -> BudgetDims:
    budget: dict[str, Any] = source or {}
    return BudgetDims(
        usd_micros=budget.get("usd_micros", 0),
        prompt_tokens=budget.get("prompt_tokens", 0),
        completion_tokens=budget.get("completion_tokens", 0),
        wall_clock_ms=budget.get("wall_clock_ms", 0),
        concurrency_slots=budget.get("concurrency_slots", 0),
    )


def _budget_from_node(node: dict[str, Any]) -> BudgetDims:
    return _budget_from(node.get("budget"))


def gate_status_of(payload: Any) -> GateStatus | None:
    """The tri-state carried by a node's output, if it carries one.

    Read structurally rather than by importing `workflow/nodes/*`: the
    executor binds node ids to registered steps and must not know their
    concrete payload classes (same reason `validator.py` takes an injected
    socket map). `None` means "this payload carries no verdict", which is not
    the same as `GateStatus.NONE`.
    """
    report = getattr(payload, "report", None)
    return report.status if isinstance(report, GateReport) else None


def _topological_order(topology: dict[str, Any]) -> list[str]:
    """M1a topologies are a single linear chain — one outgoing edge per node.

    Only nodes that appear in `edges` are part of that chain. A node reachable
    solely through a `repair` block (the repair node itself) has no incoming
    edge and would otherwise be mistaken for a second entry point and run once
    before the loop — `validator.check_evaluator_termination` already draws
    the same distinction for the same reason.
    """
    edges = topology["edges"]
    in_edges = {e["from"] for e in edges} | {e["to"] for e in edges}
    node_ids = [n["id"] for n in topology["nodes"] if n["id"] in in_edges]
    edge_map = {e["from"]: e["to"] for e in edges}
    has_incoming = {e["to"] for e in edges}

    order = [nid for nid in node_ids if nid not in has_incoming]
    seen = set(order)
    current = order[-1] if order else None
    while current is not None and current in edge_map:
        nxt = edge_map[current]
        if nxt in seen:
            break
        order.append(nxt)
        seen.add(nxt)
        current = nxt
    return order


class WorkflowExecutor:
    def __init__(
        self,
        topology: dict[str, Any],
        steps: dict[str, WorkflowStep[Any, Any]],
        bus: EventBus,
        governor: ResourceGovernor,
    ) -> None:
        self._topology = topology
        self._steps = steps
        self._bus = bus
        self._governor = governor
        self._nodes_by_id = {n["id"]: n for n in topology["nodes"]}
        self._repair: dict[str, Any] | None = topology.get("repair")

    async def execute(self, run_id: RunId, initial_payload: Any) -> Any:
        payload: Any = initial_payload
        for node_id in _topological_order(self._topology):
            payload = await self._run_node(run_id, node_id, payload)

        if self._repair is not None:
            payload = await self._run_repair_unroll(run_id, payload)
        return payload

    async def _run_node(
        self, run_id: RunId, node_id: str, payload: Any, parent: LeaseId | None = None
    ) -> Any:
        step = self._steps[node_id]
        node_budget = _budget_from_node(self._nodes_by_id[node_id])

        lease = await self._governor.reserve(run_id, node_budget, parent=parent)
        if isinstance(lease, ReservationDenied):
            raise WorkflowExecutionError(node_id, RuntimeError(f"budget denied: {lease.rationale}"))

        ctx = StepContext(run_id=run_id, node_id=NodeId(node_id), lease=lease.lease_id)
        await self._bus.emit(NodeStarted(run_id=run_id, at=datetime.now(UTC), node_id=NodeId(node_id)))

        try:
            result = await step.run(ctx, payload)
        except Exception as exc:
            await self._governor.release(lease.lease_id)
            await self._bus.emit(
                NodeCompleted(
                    run_id=run_id, at=datetime.now(UTC), node_id=NodeId(node_id), status="error"
                )
            )
            raise WorkflowExecutionError(node_id, exc) from exc

        # M1a: node-level gate only; effect actuals commit inside dispatch().
        await self._governor.release(lease.lease_id)
        await self._bus.emit(
            NodeCompleted(run_id=run_id, at=datetime.now(UTC), node_id=NodeId(node_id), status="ok")
        )
        return result

    async def _run_repair_unroll(self, run_id: RunId, payload: Any) -> Any:
        """Statically unrolled `repair` block. Validated already: the bound is
        present and in [1, 16], and every node id it names exists."""
        assert self._repair is not None
        max_iterations: int = self._repair["max_iterations"]
        chain: list[str] = [*self._repair["via_nodes"], self._repair["back_to"]]
        per_iteration = _budget_from(self._repair.get("budget_per_iteration"))

        for iteration in range(1, max_iterations + 1):
            status = gate_status_of(payload)
            if status is not GateStatus.FAILED:
                # PASSED: resolved, nothing to repair.
                # NONE: unmeasured — an instrument failure is not a repair
                # candidate, and this is the line that enforces it.
                # No verdict at all: the block does not apply to this payload.
                break

            lease = await self._governor.reserve(run_id, per_iteration)
            if isinstance(lease, ReservationDenied):
                # Exhausting the budget ends the loop, not the run: the
                # candidate keeps the verdict it already earned.
                break

            await self._bus.emit(
                RepairIterationStarted(
                    run_id=run_id,
                    at=datetime.now(UTC),
                    iteration=iteration,
                    max_iterations=max_iterations,
                    from_node=NodeId(self._repair["from_node"]),
                )
            )
            try:
                for node_id in chain:
                    payload = await self._run_node(run_id, node_id, payload, parent=lease.lease_id)
            finally:
                # Child leases refund into this parent; releasing it returns
                # the unspent remainder of the iteration to the run.
                await self._governor.release(lease.lease_id)

        return payload
