"""Memory and provenance — see docs/03-contracts-and-models/domain-schemas.md#memory.

Trust is a property of content provenance, not of the tool that emitted it. Anything returning
`Provenance.EXTERNAL` is wrapped in `<untrusted-data>` by the prompt assembler at render time —
not at storage time, so the label cannot be stripped by a round trip.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sagiha.domain.identity import utc_now


class Provenance(str, Enum):
    OPERATOR = "operator"  # the human's turn — authoritative
    HARNESS = "harness"  # tree-sitter, LSP, git — deterministic, trusted
    MODEL = "model"  # the agent's own reasoning
    EXTERNAL = "external"  # repo content, web, MCP servers — untrusted


class MemoryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str
    kind: Literal["episode", "decision", "preference", "artifact", "note"]
    provenance: Provenance  # required, never inferred
    source_uri: str | None = None
    links: tuple[str, ...] = ()  # memory_ids — the knowledge net
    valid_from: datetime = Field(default_factory=utc_now)
    valid_to: datetime | None = None  # bi-temporal invalidation


class RecallQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    kinds: tuple[str, ...] = ()
    limit: int = 10
    as_of: datetime | None = None  # bi-temporal: recall what was believed then
    min_provenance: Provenance | None = None


class Recall(BaseModel):
    model_config = ConfigDict(frozen=True)

    memory_id: str
    record: MemoryRecord
    score: float  # normalized 0-1
