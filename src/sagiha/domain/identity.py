"""Time and trajectory identity — see docs/03-contracts-and-models/domain-schemas.md#identity--time."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict


def utc_now() -> datetime:
    """The single source of time. Always timezone-aware UTC."""
    return datetime.now(UTC)


class StepId(BaseModel):
    """Trajectory identity is a DAG, not a counter — parallel candidates branch from a shared ancestor."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    branch_id: str
    seq: int
    parent: str | None = None
