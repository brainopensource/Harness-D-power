"""Default PolicyEngine implementation — see docs/02-architecture/car-model.md."""

from __future__ import annotations

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
        """Internal kernel helper to retrieve an active capability grant."""
        grant = self._active_grants.get(grant_id)
        if grant is None:
            return None
        if grant.expires_at <= utc_now():
            del self._active_grants[grant_id]
            return None
        return grant

    async def authorize(self, call: ToolCall, context: RunContext) -> Decision:
        if call.tool_name in self._always_gate:
            return Decision(
                allowed=False,
                reason=f"Tool '{call.tool_name}' requires explicit human grant",
                requires_human=True,
            )

        schema = self._tool_schemas.get(call.tool_name)
        if schema is not None:
            scope_paths = _extract_paths_from_schema(schema, call.arguments)
        else:
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
        self._active_grants.pop(grant_id, None)
