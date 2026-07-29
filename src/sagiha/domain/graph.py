"""Retrieval & code graph models — see docs/03-contracts-and-models/domain-schemas.md#retrieval--graph."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class RetrievalHit(BaseModel):
    path: str
    chunk: str
    score: float  # backend-agnostic relevance, normalized 0-1
    metadata: dict[str, Any] = {}  # exempt: open-shaped backend annotations


class SymbolRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    name: str
    kind: Literal["function", "class", "method", "module", "variable"]
    line: int


class GraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    src: str
    dst: str
    kind: Literal["imports", "calls", "defines", "inherits", "owns", "co_changed"]
    weight: float = 1.0


class CoChange(BaseModel):
    path: str
    commits: int  # how often it changed alongside the query path
    last_seen: datetime


class DiagnosticItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    line: int
    column: int
    severity: Literal["error", "warning", "information", "hint"]
    code: str | None = None
    message: str
    source: str  # which server or tool produced it
