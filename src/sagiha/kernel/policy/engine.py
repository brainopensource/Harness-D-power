"""Default PolicyEngine implementation — see docs/02-architecture/car-model.md."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sagiha.domain.content import ToolCall, ToolResult
from sagiha.domain.control import Decision, Grant, RunContext
from sagiha.domain.identity import utc_now


class DefaultPolicyEngine:
    """Trusted capability authorization engine.

    Mints capability Grants internally upon authorization.
    Grants remain encapsulated within kernel control plane and dispatch.
    """

    def __init__(self, always_gate: list[str] | None = None) -> None:
        self._always_gate = set(always_gate or [])
        self._active_grants: dict[str, Grant] = {}

    def get_grant(self, grant_id: str) -> Grant | None:
        """Internal kernel helper to retrieve an active capability grant."""
        grant = self._active_grants.get(grant_id)
        if grant is None:
            return None
        if grant.expires_at <= utc_now():
            del self._active_grants[grant_id]
            return None
        return grant

    async def authorize(self, call: ToolCall, context: RunContext) -> Decision:
        # Require human approval if tool is in always_gate list
        if call.tool_name in self._always_gate:
            return Decision(
                allowed=False,
                reason=f"Tool '{call.tool_name}' requires explicit human grant",
                requires_human=True,
            )

        # Scoped path extraction from arguments
        scope_paths: list[str] = []
        for key in ("path", "file_path", "target_file", "dir"):
            val = call.arguments.get(key)
            if isinstance(val, str):
                scope_paths.append(val)

        now = utc_now()
        grant_id = str(uuid.uuid4())
        grant = Grant(
            grant_id=grant_id,
            tool_name=call.tool_name,
            scope_paths=tuple(scope_paths),
            run_id=context.run_id,
            issued_at=now,
            expires_at=now + timedelta(minutes=5),
        )

        self._active_grants[grant_id] = grant
        return Decision(
            allowed=True,
            reason=f"Authorized tool call '{call.tool_name}'",
            grant_id=grant_id,
        )

    async def record_outcome(self, grant_id: str, result: ToolResult) -> None:
        # Expire/clean up used grant
        self._active_grants.pop(grant_id, None)
