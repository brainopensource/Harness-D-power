"""Event schema upcasters — identity stub for forward-compatible trajectory reads (C7 / D6)."""

from __future__ import annotations

from typing import Any


def upcast_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply `(event, schema_version)` migrations. Identity until a breaking shape lands."""
    return payload


def upcast_trajectory_step(payload: dict[str, Any]) -> dict[str, Any]:
    """Migration point for `TrajectoryStep` rows. Identity until a breaking shape lands.

    A pre-S2.5 row has no `message` key — `TrajectoryStep.message` defaults to `None` on
    validation, which is already the honest answer: reconstructing a synthetic `Message`
    from `tool_calls` would fabricate content the model never necessarily produced in that
    shape (block ordering, accompanying text). Nothing to backfill, so this is identity —
    kept as an explicit seam rather than an implicit default for the next real migration.
    """
    return payload
