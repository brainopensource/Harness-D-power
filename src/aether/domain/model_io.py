"""Model request/response wire shapes for the ModelProvider boundary."""

from __future__ import annotations

from typing import Literal

from aether.domain.ids import Frozen
from aether.domain.taint import TaintSpan
from aether.domain.tools import ToolSpec


class ToolCallRef(Frozen):
    """A tool call the *assistant* made, as it must be replayed to the provider.

    Every OpenAI-compatible endpoint requires the assistant's `tool_calls`
    message to precede the `tool` results answering it, and each result to name
    the `tool_call_id` it answers. Sprint 2 sent neither: it appended the tool
    output as a bare `{"role": "tool", "content": ...}` with nothing tying it to
    a call, which is malformed and had never run against a real endpoint — only
    against respx mocks that returned no tool calls at all.
    """

    call_id: str
    name: str
    args_json: str


class ModelMessage(Frozen):
    role: Literal["system", "user", "assistant", "tool"]
    spans: tuple[TaintSpan, ...]  # content carries provenance, always
    cache_breakpoint: bool = False  # <=4 true across a request (I10)
    #: Set on an `assistant` message that requested tools.
    tool_calls: tuple[ToolCallRef, ...] = ()
    #: Set on a `tool` message; names the call this result answers.
    tool_call_id: str | None = None


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


#: Why a completion stopped. Named because it is read outside the stream:
#: `provider_error` is an *instrument* failure and must reach the gate as
#: `GateStatus.NONE`, never as a task's `FAILED` (measurement.md §2 B4).
StopReason = Literal["end", "tool_use", "max_tokens", "provider_error"]


class StopEvent(Frozen):
    kind: Literal["stop"] = "stop"
    reason: StopReason


ModelStreamEvent = TextDelta | ToolCallDelta | UsageEvent | StopEvent
