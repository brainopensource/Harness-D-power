"""ModelProvider conformance: mock and real adapter share the same wire contract
(ADR-0005 rev. 2) — the stream always ends in a StopEvent, ceilings are enforced,
provider errors are a typed StopEvent reason, never an empty generator."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from tests.aether.mocks import FakeModelProvider

from aether.adapters.model_provider.openai_compatible import OpenAICompatibleProvider
from aether.domain.model_io import ModelMessage, ModelRequest, StopEvent, TextDelta
from aether.domain.taint import Provenance, TaintSpan
from datetime import UTC, datetime

BASE_URL = "http://localhost:11434/v1"


def _span(text: str) -> TaintSpan:
    from aether.domain.ids import SpanId

    return TaintSpan(
        span_id=SpanId("s1"), label=Provenance.AGENT, text=text, source="test", created_at=datetime.now(UTC)
    )


def _request(max_tokens: int = 100) -> ModelRequest:
    return ModelRequest(
        model="qwen2.5-coder-32b",
        messages=(ModelMessage(role="user", spans=(_span("hello"),)),),
        max_tokens=max_tokens,
    )


def _sse(*chunks: dict[str, object]) -> str:
    body = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks)
    return body + "data: [DONE]\n\n"


@pytest.mark.parametrize(
    "provider",
    [
        FakeModelProvider(),
        OpenAICompatibleProvider(BASE_URL, "qwen2.5-coder-32b"),
    ],
)
async def test_stream_always_terminates_with_stop_event(provider: object) -> None:
    if isinstance(provider, OpenAICompatibleProvider):
        with respx.mock:
            respx.post(f"{BASE_URL}/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    content=_sse(
                        {"choices": [{"delta": {"content": "ok"}, "finish_reason": None}]},
                        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
                    ),
                )
            )
            events = [event async for event in provider.stream(_request())]
    else:
        events = [event async for event in provider.stream(_request())]

    assert isinstance(events[-1], StopEvent)


async def test_openai_compatible_happy_path_emits_text_delta_then_stop() -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                200,
                content=_sse(
                    {"choices": [{"delta": {"content": "hel"}, "finish_reason": None}]},
                    {"choices": [{"delta": {"content": "lo"}, "finish_reason": None}]},
                    {
                        "choices": [{"delta": {}, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 5, "completion_tokens": 2},
                    },
                ),
            )
        )
        provider = OpenAICompatibleProvider(BASE_URL, "qwen2.5-coder-32b")
        events = [event async for event in provider.stream(_request())]

    text = "".join(e.text for e in events if isinstance(e, TextDelta))
    assert text == "hello"
    assert isinstance(events[-1], StopEvent)
    assert events[-1].reason == "end"


async def test_openai_compatible_mid_stream_http_error_yields_provider_error_stop() -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/chat/completions").mock(return_value=httpx.Response(500, content=b"boom"))
        provider = OpenAICompatibleProvider(BASE_URL, "qwen2.5-coder-32b")
        events = [event async for event in provider.stream(_request())]

    assert len(events) == 1
    assert isinstance(events[0], StopEvent)
    assert events[0].reason == "provider_error"


async def test_openai_compatible_transport_error_yields_provider_error_stop() -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/chat/completions").mock(side_effect=httpx.ConnectError("refused"))
        provider = OpenAICompatibleProvider(BASE_URL, "qwen2.5-coder-32b")
        events = [event async for event in provider.stream(_request())]

    assert events == [StopEvent(reason="provider_error")]


async def test_openai_compatible_enforces_max_tokens_ceiling_on_outgoing_request() -> None:
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                200, content=_sse({"choices": [{"delta": {}, "finish_reason": "stop"}]})
            )
        )
        provider = OpenAICompatibleProvider(BASE_URL, "qwen2.5-coder-32b")
        [event async for event in provider.stream(_request(max_tokens=42))]

    sent = json.loads(route.calls[0].request.content)
    assert sent["max_tokens"] == 42


async def test_count_tokens_never_calls_network() -> None:
    with respx.mock:  # no routes registered — any HTTP call raises
        provider = OpenAICompatibleProvider(BASE_URL, "qwen2.5-coder-32b")
        n = await provider.count_tokens(_request())

    assert n > 0
