"""PolicyEngine — the capability security choke point.

See docs/02-architecture/car-model.md and docs/08-decisions/0007-trusted-computing-base.md.
Grants never leave the dispatch choke point (`kernel/dispatch.py`); this Protocol never accepts
or returns a `Grant` — only `grant_id` for correlation via `Decision`.

Conformance suite must assert: `test_forged_grant_is_rejected_at_dispatch`.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.content import ToolCall, ToolResult
from sagiha.domain.control import Decision, RunContext

PORT_VERSION: Final = 1
STABILITY: Final = "stable"


class PolicyEngine(Protocol):
    async def authorize(self, call: ToolCall, context: RunContext) -> Decision: ...

    async def record_outcome(self, grant_id: str, result: ToolResult) -> None: ...
