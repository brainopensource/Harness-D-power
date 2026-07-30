"""ToolRegistry — open tool namespace, dispatch. See docs/02-architecture/car-model.md.

`dispatch` takes no `Grant` parameter. It is reachable only through `kernel/dispatch.py`, which
calls `PolicyEngine.authorize()` first and consumes the resulting grant privately — the grant
never crosses this or any other port signature (docs/08-decisions/0007-trusted-computing-base.md,
enforced by tests/contracts/test_port_shape.py::test_no_grant_in_any_public_signature). This
supersedes the illustrative `registry.dispatch(call, decision.grant)` pseudocode in
docs/02-architecture/car-model.md — see the 2026-07-28 architecture review, finding D1.
"""

from __future__ import annotations

from typing import Any, Final, Protocol

from sagiha.domain.content import EffectClass, ToolCall, ToolResult

PORT_VERSION: Final = 1
STABILITY: Final = "stable"


class ToolRegistry(Protocol):
    # `schema` is exempt from contract rule 1 — JSON Schema is externally defined.
    async def register(self, tool_name: str, schema: dict[str, Any], effect: EffectClass) -> None: ...

    async def dispatch(self, call: ToolCall) -> ToolResult: ...

    async def get_effect_class(self, tool_name: str) -> EffectClass: ...
