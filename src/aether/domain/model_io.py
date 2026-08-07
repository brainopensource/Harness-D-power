"""Model request/response wire shapes for the ModelProvider boundary."""

from __future__ import annotations

from typing import Literal

from aether.domain.ids import Frozen
from aether.domain.taint import TaintSpan
from aether.domain.tools import ToolSpec


class ModelMessage(Frozen):
    role: Literal["system", "user", "assistant", "tool"]
    spans: tuple[TaintSpan, ...]  # content carries provenance, always
    cache_breakpoint: bool = False  # <=4 true across a request (I10)


class ModelRequest(Frozen):
    model: str
    messages: tuple[ModelMessage, ...]
    tools: tuple[ToolSpec, ...] = ()
    max_tokens: int
    temperature: float = 0.0
    seed: int | None = None


class TextDelta(Frozen):
    kind: Literal["text"] = "text"
    text: str


class ToolCallDelta(Frozen):
    kind: Literal["tool_call"] = "tool_call"
    call_id: str
    name: str
    args_json_fragment: str


class UsageEvent(Frozen):
    kind: Literal["usage"] = "usage"
    prompt_tokens: int
    completion_tokens: int
    cached_prompt_tokens: int = 0


class StopEvent(Frozen):
    kind: Literal["stop"] = "stop"
    reason: Literal["end", "tool_use", "max_tokens", "provider_error"]


ModelStreamEvent = TextDelta | ToolCallDelta | UsageEvent | StopEvent
