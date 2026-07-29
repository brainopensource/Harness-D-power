"""MetaImprover — proposes mutations restricted to the mutable surface, outside the TCB.

See docs/03-contracts-and-models/hexagonal-ports.md#orchestration--improvement. Deferred past
v0.1 per the 2026-07-28 architecture review (RHI outer loop out of scope) — this Protocol exists
so the port surface is complete, but ships with no adapter and no conformance suite in v0.1; only
the event-logging substrate that will train it is built. Deployment of any resulting mutation
requires human sign-off — this port never writes to the TCB
(docs/08-decisions/0007-trusted-computing-base.md).
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.work import TaskSpec

PORT_VERSION: Final = 1
STABILITY: Final = "experimental"


class MetaImprover(Protocol):
    async def propose_mutation(self, task: TaskSpec) -> str: ...  # unified diff, path-allowlisted
