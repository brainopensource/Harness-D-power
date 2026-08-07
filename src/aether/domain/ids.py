"""NewType identifiers and the shared immutable base class for all domain/port models."""

from __future__ import annotations

from typing import NewType

from pydantic import BaseModel, ConfigDict

RunId = NewType("RunId", str)
TaskId = NewType("TaskId", str)
LeaseId = NewType("LeaseId", str)
SpanId = NewType("SpanId", str)
NodeId = NewType("NodeId", str)


class Frozen(BaseModel):
    """Immutable, closed-schema base. Every domain and port model derives from this."""

    model_config = ConfigDict(frozen=True, extra="forbid")
