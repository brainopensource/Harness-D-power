"""Tool catalog, call, and result shapes."""

from __future__ import annotations

from typing import Literal

from aether.domain.ids import Frozen, SpanId
from aether.domain.taint import TaintSpan


class ToolSpec(Frozen):
    name: str
    description: str
    params_json_schema: str  # schema as JSON string
    effect_class: Literal["read", "write", "shell", "network", "model"]


class ToolCall(Frozen):
    call_id: str
    name: str
    args_json: str
    justifying_spans: tuple[SpanId, ...]  # what the TaintGate audits


class ToolResult(Frozen):
    call_id: str
    spans: tuple[TaintSpan, ...]  # outputs are labeled at birth: tool output => UNTRUSTED_EXTERNAL
    exit_code: int | None = None
