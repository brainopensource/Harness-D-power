"""Default PolicyEngine implementation — see docs/02-architecture/car-model.md."""

from __future__ import annotations

import os.path
import uuid
from datetime import timedelta
from typing import Any, cast

from sagiha.domain.content import ToolCall, ToolResult
from sagiha.domain.control import Decision, Grant, RunContext
from sagiha.domain.identity import utc_now


def _extract_paths_from_schema(schema: dict[str, Any], arguments: dict[str, Any]) -> list[str]:
    """Walk JSON Schema for `x-sagiha-path: true` properties and collect argument values."""
    paths: list[str] = []

    def walk(node: dict[str, Any], value: object) -> None:
        props_raw = node.get("properties")
        if isinstance(props_raw, dict) and isinstance(value, dict):
            props = cast(dict[str, Any], props_raw)
            value_dict = cast(dict[str, Any], value)
            for key, subschema_raw in props.items():
                if not isinstance(subschema_raw, dict):
                    continue
                subschema = cast(dict[str, Any], subschema_raw)
                if subschema.get("x-sagiha-path") is True:
                    raw = value_dict.get(key)
                    if isinstance(raw, str):
                        paths.append(raw)
                    elif isinstance(raw, list):
                        for item in cast(list[object], raw):
                            if isinstance(item, str):
                                paths.append(item)
                child = value_dict.get(key)
                if isinstance(child, dict):
                    walk(subschema, cast(dict[str, Any], child))
                elif isinstance(child, list):
                    walk(subschema, cast(list[object], child))
        items_raw = node.get("items")
        if isinstance(items_raw, dict) and isinstance(value, list):
            items = cast(dict[str, Any], items_raw)
            for item in cast(list[object], value):
                if isinstance(item, dict):
                    walk(items, cast(dict[str, Any], item))

    walk(schema, arguments)
    return paths


def escapes_root(root: str, candidate: str) -> bool:
    """Return True when `candidate` resolves outside `root`.

    Purely lexical — `os.path.normpath` collapses `..` without touching the
    filesystem, so the kernel performs no I/O while authorizing. The adapter
    repeats the check against a resolved path to also catch symlink escapes
    (see `adapters/workspace/local.resolve_within`); this is defence in depth,
    with the authoritative refusal at the choke point.
    """
    if not root:
        return False
    root_norm = os.path.normpath(root)
    joined = candidate if os.path.isabs(candidate) else os.path.join(root_norm, candidate)
    target = os.path.normpath(joined)
    return target != root_norm and not target.startswith(root_norm + os.sep)


class DefaultPolicyEngine:
    """Trusted capability authorization engine.

    Mints capability Grants internally upon authorization.
    Grants remain encapsulated within kernel control plane and dispatch.
    """

    def __init__(self, always_gate: list[str] | None = None) -> None:
        self._always_gate = set(always_gate or [])
        self._active_grants: dict[str, Grant] = {}
        self._tool_schemas: dict[str, dict[str, Any]] = {}

    def register_tool_schema(self, tool_name: str, schema: dict[str, Any]) -> None:
        """Bind JSON Schema used for path extraction at authorize time (C1)."""
        self._tool_schemas[tool_name] = schema

    def get_grant(self, grant_id: str) -> Grant | None:
        """Internal kernel helper to retrieve an active capability grant.

        Not part of the `PolicyEngine` Protocol — `Grant` may never cross a port signature
        (test_no_grant_in_any_public_signature). Direct callers must hold a reference to this
        concrete class, not the Protocol; `dispatch.py` uses `verify_grant` instead.
        """
        grant = self._active_grants.get(grant_id)
        if grant is None:
            return None
        if grant.expires_at <= utc_now():
            del self._active_grants[grant_id]
            return None
        return grant

    async def verify_grant(self, grant_id: str) -> bool:
        """Point-of-effect check (C1 / D8): True iff `grant_id` is active and unexpired."""
        return self.get_grant(grant_id) is not None

    async def authorize(self, call: ToolCall, context: RunContext) -> Decision:
        if call.tool_name in self._always_gate:
            return Decision(
                allowed=False,
                reason=f"Tool '{call.tool_name}' requires explicit human grant",
                requires_human=True,
            )

        schema = self._tool_schemas.get(call.tool_name)
        if schema is None:
            # R3: a tool with no registered schema has no declared path parameters to scope,
            # so it cannot be granted a path-bearing capability — fail closed rather than
            # guess at argument key names (the guess could miss a real path argument and
            # mint an unscoped grant for a mutating tool).
            return Decision(
                allowed=False,
                reason=f"No registered schema for tool '{call.tool_name}' — cannot scope grant",
                requires_human=False,
            )
        scope_paths = _extract_paths_from_schema(schema, call.arguments)

        # Containment is enforced here, at the choke point, so the grant's
        # scope is load-bearing rather than advisory. Relying on each adapter
        # to re-check means one forgetful adapter silently loses the property.
        for scoped in scope_paths:
            if escapes_root(context.workspace_root, scoped):
                return Decision(
                    allowed=False,
                    reason=(f"Path '{scoped}' escapes workspace root for tool '{call.tool_name}'"),
                    requires_human=False,
                )

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
        self._active_grants.pop(grant_id, None)
