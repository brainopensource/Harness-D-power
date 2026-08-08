"""Tool-call round trip (Sprint 3.5, A5).

The defect: `GenerateStep` appended the tool *result* and never the assistant
`tool_calls` message that requested it, and no `tool_call_id` was ever sent.
Every OpenAI-compatible endpoint requires both. It had only ever run against
respx mocks that returned no tool calls, so no test could see it — which is why
the fix ships with a wire-level assertion *and* a live round trip.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
import respx
from tests.live_support import LOCAL_BASE_URL, require_live_model

from aether.adapters.model_provider.openai_compatible import OpenAICompatibleProvider
from aether.domain.ids import SpanId
from aether.domain.model_io import ModelMessage, ModelRequest, TextDelta, ToolCallRef
from aether.domain.taint import Provenance, TaintSpan

BASE_URL = "http://model.invalid/v1"


def _span(text: str) -> TaintSpan:
    return TaintSpan(
        span_id=SpanId("s1"),
        label=Provenance.OPERATOR,
        text=text,
        source="test",
        created_at=datetime.now(UTC),
    )


def _sse(*chunks: dict[str, object]) -> bytes:
    body = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks)
    return (body + "data: [DONE]\n\n").encode()


def _captured_payload(route: Any) -> dict[str, Any]:
    return json.loads(route.calls.last.request.content)


async def _send(messages: tuple[ModelMessage, ...]) -> dict[str, Any]:
    provider = OpenAICompatibleProvider(BASE_URL, "test-model")
    request = ModelRequest(model="test-model", messages=messages, max_tokens=16)
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                200, content=_sse({"choices": [{"delta": {}, "finish_reason": "stop"}]})
            )
        )
        async for _ in provider.stream(request):
            pass
        return _captured_payload(route)


async def test_an_assistant_message_carries_its_tool_calls_on_the_wire() -> None:
    payload = await _send(
        (
            ModelMessage(role="user", spans=(_span("do it"),)),
            ModelMessage(
                role="assistant",
                spans=(),
                tool_calls=(ToolCallRef(call_id="call_1", name="shell", args_json='{"cmd":"ls"}'),),
            ),
        )
    )

    assistant = payload["messages"][1]
    assert assistant["role"] == "assistant"
    assert assistant["tool_calls"] == [
        {"id": "call_1", "type": "function", "function": {"name": "shell", "arguments": '{"cmd":"ls"}'}}
    ]


async def test_a_tool_result_names_the_call_it_answers() -> None:
    payload = await _send(
        (
            ModelMessage(role="user", spans=(_span("do it"),)),
            ModelMessage(role="tool", spans=(_span("output"),), tool_call_id="call_1"),
        )
    )

    assert payload["messages"][1]["tool_call_id"] == "call_1"


async def test_ordinary_messages_carry_no_tool_fields() -> None:
    """A plain user turn must not grow a null `tool_call_id` — some endpoints
    reject unknown or null keys outright."""
    payload = await _send((ModelMessage(role="user", spans=(_span("hello"),)),))

    assert "tool_call_id" not in payload["messages"][0]
    assert "tool_calls" not in payload["messages"][0]


async def test_cache_breakpoint_is_not_a_wire_field_here() -> None:
    """A6: OpenAI-compatible endpoints have no `cache_control` marker and cache
    implicitly on a stable prefix. Pinning that as a decision, so the field's
    absence from the payload is a choice rather than an omission (ADR-0010)."""
    payload = await _send((ModelMessage(role="user", spans=(_span("hello"),), cache_breakpoint=True),))

    assert "cache_breakpoint" not in payload["messages"][0]
    assert "cache_control" not in payload["messages"][0]


async def test_the_generate_node_emits_the_full_tool_sequence() -> None:
    """The sequence the provider requires: user → assistant(tool_calls) →
    tool(tool_call_id) → …, in that order."""
    from tests.aether.workflow.test_repair import TASK, WORKTREE  # reuse the fixtures

    from aether.domain.tools import ToolResult
    from aether.workflow.nodes.generate import GenerateStep
    from aether.workflow.nodes.retrieve import RetrievedContext
    from aether.workflow.step import StepContext

    class _Facade:
        def __init__(self) -> None:
            self.requests: list[ModelRequest] = []
            self.calls = 0

        async def model(self, request: ModelRequest, cost: Any) -> list[Any]:
            self.requests.append(request)
            self.calls += 1
            if self.calls == 1:
                from aether.domain.model_io import StopEvent, ToolCallDelta

                return [
                    ToolCallDelta(call_id="call_1", name="shell", args_json_fragment='{"cmd":"ls"}'),
                    StopEvent(reason="tool_use"),
                ]
            from aether.domain.model_io import StopEvent

            return [TextDelta(text="diff --git a/x b/x\n"), StopEvent(reason="end")]

        async def shell(self, args: Any, cost: Any, *, justifying_spans: Any = ()) -> ToolResult:
            return ToolResult(call_id="call_1", spans=(_span("total 0"),), exit_code=0)

    facade = _Facade()
    step = GenerateStep(facade, model_name="m")  # type: ignore[arg-type]
    ctx = StepContext(run_id=TASK.source.manifest_hash, node_id="generate", lease="l1")  # type: ignore[arg-type]

    await step.run(
        ctx,
        RetrievedContext(task=TASK, worktree=WORKTREE, instructions="fix it"),
    )

    second = facade.requests[1].messages
    roles = [m.role for m in second]
    # The system layer leads (Sprint 3.5 B4), then the required tool sequence.
    assert roles == ["system", "user", "assistant", "tool"]
    assert second[2].tool_calls[0].call_id == "call_1"
    assert second[3].tool_call_id == "call_1"


@pytest.mark.live
async def test_a_real_endpoint_accepts_the_tool_sequence() -> None:
    """The half no mock can give: a real server validating the message shape.

    Skips with no endpoint; hard-fails when `AETHER_REQUIRE_LIVE_MODEL=1`
    promised one. A malformed sequence comes back as `provider_error`.
    """
    model = require_live_model()
    provider = OpenAICompatibleProvider(LOCAL_BASE_URL, model)
    request = ModelRequest(
        model=model,
        messages=(
            ModelMessage(role="user", spans=(_span("List the files."),)),
            ModelMessage(
                role="assistant",
                spans=(),
                tool_calls=(ToolCallRef(call_id="call_1", name="shell", args_json='{"cmd":"ls"}'),),
            ),
            ModelMessage(role="tool", spans=(_span("README.md"),), tool_call_id="call_1"),
        ),
        max_tokens=32,
    )

    events = [event async for event in provider.stream(request)]

    assert events, "no events streamed"
    assert events[-1].kind == "stop"
    assert events[-1].reason != "provider_error", "the endpoint rejected the tool-call message sequence"
