"""OpenAI-compatible ModelProvider adapter (TASK-011) — closes B2b.

First real adapter for the `ModelProvider` port (ADR-0005 rev. 2). Streams an
OpenAI-compatible `/chat/completions` SSE body over `httpx` and translates
provider deltas into the wire-serializable `ModelStreamEvent` union.

The stream always terminates in a `StopEvent`, even on a transport or HTTP
error — mapped to `reason="provider_error"`. Nothing here ever raises past the
async generator or silently returns an empty stream (measurement.md §2 B2).
Token-ceiling enforcement is conservation-of-request, not courtesy: `max_tokens`
is always sent on the outgoing call.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, Literal

import httpx

from aether.domain.model_io import (
    ModelMessage,
    ModelRequest,
    ModelStreamEvent,
    StopEvent,
    TextDelta,
    ToolCallDelta,
    UsageEvent,
)
from aether.domain.tools import ToolSpec


def _message_text(message: ModelMessage) -> str:
    return "".join(span.text for span in message.spans)


def _to_openai_message(message: ModelMessage) -> dict[str, str]:
    return {"role": message.role, "content": _message_text(message)}


def _to_openai_tool(tool: ToolSpec) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": json.loads(tool.params_json_schema),
        },
    }


_StopReason = Literal["end", "tool_use", "max_tokens", "provider_error"]

_FINISH_REASON_MAP: dict[str, _StopReason] = {
    "stop": "end",
    "tool_calls": "tool_use",
    "function_call": "tool_use",
    "length": "max_tokens",
}


class OpenAICompatibleProvider:
    """One adapter per OpenAI-compatible endpoint (a `RoutingModelProvider`
    composite handles multi-model roles, ADR-0007)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=timeout_s)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _payload(self, request: ModelRequest) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": request.model or self._model,
            "messages": [_to_openai_message(m) for m in request.messages],
            "max_tokens": request.max_tokens,  # hard ceiling — conservation is kernel policy (spec.md §5)
            "temperature": request.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if request.tools:
            payload["tools"] = [_to_openai_tool(t) for t in request.tools]
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        tool_call_buffers: dict[int, dict[str, str | None]] = {}
        try:
            async with self._client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=self._payload(request),
                headers=self._headers(),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        return
                    chunk: dict[str, Any] = json.loads(data)

                    usage: dict[str, Any] | None = chunk.get("usage")
                    if usage:
                        cached_details: dict[str, Any] = usage.get("prompt_tokens_details") or {}
                        yield UsageEvent(
                            prompt_tokens=usage.get("prompt_tokens", 0) or 0,
                            completion_tokens=usage.get("completion_tokens", 0) or 0,
                            cached_prompt_tokens=cached_details.get("cached_tokens", 0) or 0,
                        )

                    choices: list[dict[str, Any]] = chunk.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    delta: dict[str, Any] = choice.get("delta") or {}

                    if delta.get("content"):
                        yield TextDelta(text=delta["content"])

                    tool_calls: list[dict[str, Any]] = delta.get("tool_calls") or []
                    for tool_call in tool_calls:
                        idx: int = tool_call.get("index", 0)
                        buf = tool_call_buffers.setdefault(idx, {"id": None, "name": None})
                        if tool_call.get("id"):
                            buf["id"] = tool_call["id"]
                        function: dict[str, Any] = tool_call.get("function") or {}
                        if function.get("name"):
                            buf["name"] = function["name"]
                        yield ToolCallDelta(
                            call_id=buf["id"] or f"call-{idx}",
                            name=buf["name"] or "",
                            args_json_fragment=function.get("arguments", "") or "",
                        )

                    finish_reason: str | None = choice.get("finish_reason")
                    if finish_reason:
                        yield StopEvent(reason=_FINISH_REASON_MAP.get(finish_reason, "end"))
                        return
        except Exception:
            yield StopEvent(reason="provider_error")
            return

        # Body ended without an explicit finish_reason or [DONE] — still a
        # defined outcome, never a silently empty generator.
        yield StopEvent(reason="provider_error")

    async def count_tokens(self, request: ModelRequest) -> int:
        """Local heuristic (whitespace-token count) — no provider round-trip.
        OpenAI-compatible endpoints expose no standard tokenization endpoint;
        this is an estimate, not exact provider tokenization."""
        total = sum(len(_message_text(m).split()) for m in request.messages)
        return total or 1
