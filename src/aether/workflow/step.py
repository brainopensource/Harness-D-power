"""WorkflowStep[In, Out] — node and socket types only. No executor (ADR-0013, M0).

`workflow/validator.py` and `workflow/executor.py` are TASK-020 (M1a), out of
scope here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Generic, TypeVar

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


#: Builds one node's step from that node's declared `params`.
#:
#: Registration is by **kind**, not by node id. Sprint 2 keyed the executor's
#: step map by node id, which made two nodes of the same kind — every Best-of-N
#: topology at M3 — a `KeyError`, and made a node's implementation impossible to
#: choose from data. A kind maps to a factory; the topology supplies the params;
#: swapping an implementation is a registry entry, not a code change in a caller
#: (ADR-0014: topologies are data).
StepFactory = Callable[[Mapping[str, Any]], "WorkflowStep[Any, Any]"]

#: kind -> factory. Frozen at composition (I6); no runtime registration.
StepRegistry = Mapping[str, StepFactory]
