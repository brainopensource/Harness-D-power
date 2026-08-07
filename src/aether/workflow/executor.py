"""WorkflowExecutor (TASK-020) — M1a scope: unconditional linear order only.

Loads the validated topology, binds node ids to registered step instances,
runs in topological order, emits one `NodeStarted`/`NodeCompleted` pair per
node to the bus, and reserves/releases one governor lease per node (on top of
the per-effect reserve/commit/release each `DispatchFacade` call already
exercises inside `Dispatcher.dispatch()` — M1a Gate 5). No memoization, no
branching — those are M2/M3 (`workflow/validator.py`'s `bounded_iteration`/
`declared_fanout` checks pass vacuously for this sprint's topology).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aether.domain.budget import BudgetDims
from aether.domain.events import NodeCompleted, NodeStarted
from aether.domain.ids import NodeId, RunId
from aether.kernel.bus import EventBus
from aether.kernel.governor import ResourceGovernor
from aether.ports.resource_governor import ReservationDenied
from aether.workflow.step import StepContext, WorkflowStep


class WorkflowExecutionError(Exception):
    def __init__(self, node_id: str, cause: Exception) -> None:
        self.node_id = node_id
        self.cause = cause
        super().__init__(f"node '{node_id}' failed: {cause}")


def _budget_from_node(node: dict[str, Any]) -> BudgetDims:
    budget: dict[str, Any] = node.get("budget") or {}
    return BudgetDims(
        usd_micros=budget.get("usd_micros", 0),
        prompt_tokens=budget.get("prompt_tokens", 0),
        completion_tokens=budget.get("completion_tokens", 0),
        wall_clock_ms=budget.get("wall_clock_ms", 0),
        concurrency_slots=budget.get("concurrency_slots", 0),
    )


def _topological_order(topology: dict[str, Any]) -> list[str]:
    """M1a topologies are a single linear chain — one outgoing edge per node."""
    node_ids = [n["id"] for n in topology["nodes"]]
    edges = topology["edges"]
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

    async def execute(self, run_id: RunId, initial_payload: Any) -> Any:
        payload: Any = initial_payload
        for node_id in _topological_order(self._topology):
            step = self._steps[node_id]
            node_budget = _budget_from_node(self._nodes_by_id[node_id])

            lease = await self._governor.reserve(run_id, node_budget)
            if isinstance(lease, ReservationDenied):
                raise WorkflowExecutionError(node_id, RuntimeError(f"budget denied: {lease.rationale}"))

            ctx = StepContext(run_id=run_id, node_id=NodeId(node_id), lease=lease.lease_id)
            await self._bus.emit(NodeStarted(run_id=run_id, at=datetime.now(UTC), node_id=NodeId(node_id)))

            try:
                payload = await step.run(ctx, payload)
            except Exception as exc:
                await self._governor.release(lease.lease_id)
                node_completed = NodeCompleted(
                    run_id=run_id, at=datetime.now(UTC), node_id=NodeId(node_id), status="error"
                )
                await self._bus.emit(node_completed)
                raise WorkflowExecutionError(node_id, exc) from exc

            # M1a: node-level gate only; effect actuals commit inside dispatch().
            await self._governor.release(lease.lease_id)
            await self._bus.emit(
                NodeCompleted(run_id=run_id, at=datetime.now(UTC), node_id=NodeId(node_id), status="ok")
            )

        return payload
