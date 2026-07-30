"""Event schema upcasters — identity stub for forward-compatible trajectory reads (C7 / D6)."""

from __future__ import annotations

from typing import Any


def upcast_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply `(event, schema_version)` migrations. Identity until a breaking shape lands."""
    return payload
