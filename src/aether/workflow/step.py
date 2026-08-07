"""WorkflowStep[In, Out] — node and socket types only. No executor (ADR-0013, M0).

`workflow/validator.py` and `workflow/executor.py` are TASK-020 (M1a), out of
scope here.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from aether.domain.ids import Frozen, LeaseId, NodeId, RunId

In = TypeVar("In", bound=Frozen)
Out = TypeVar("Out", bound=Frozen)


class StepContext(Frozen):
    run_id: RunId
    node_id: NodeId
    lease: LeaseId
    # Steps receive NO adapter handles: all effects go through a dispatch
    # facade injected by the executor — the choke point is unavoidable by type.


class WorkflowStep(Generic[In, Out]):
    """Abstract node. Concrete steps are registered at composition (I6) under a
    stable string id; topologies (YAML) reference ids, never classes."""

    node_kind: str
    input_type: type[In]
    output_type: type[Out]  # socket types — the schema validator checks edges with these

    async def run(self, ctx: StepContext, payload: In) -> Out:
        raise NotImplementedError  # stubs raise (measurement.md §5)

    def input_digest(self, payload: In) -> str:
        """M2 memoization key = sha256(node_kind, impl_version, payload json).
        Not implemented at M0 — no executor exists yet to consume it."""
        raise NotImplementedError
