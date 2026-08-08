"""`Inference` (T3, `TASK-055`) — one model-call-and-collect idiom, the
`completion_tokens` reservation fix, and `ToolLoop` usable by any role.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from aether.agency.capabilities.inference import (
    INFERENCE,
    SingleTurn,
    ToolLoop,
    UnknownInference,
    get_inference,
)
from aether.domain.budget import BudgetDims
from aether.domain.effects import ShellArgs
from aether.domain.ids import RunId, SpanId
from aether.domain.model_io import ModelMessage, ModelRequest, StopEvent, TextDelta, ToolCallDelta
from aether.domain.taint import Provenance, TaintSpan
from aether.domain.tools import ToolResult
from aether.domain.workspace import WorktreeRef

_WORKTREE = WorktreeRef(worktree_id="wt-0", run_id=RunId("r1"), base_commit="0" * 40, abs_hint="fixture")
_ZERO_BUDGET = BudgetDims()  # Frozen/immutable — safe as a shared default (ruff B008)


def _span(text: str) -> TaintSpan:
    return TaintSpan(
        span_id=SpanId("s1"),
        label=Provenance.OPERATOR,
        text=text,
        source="test",
        created_at=datetime.now(UTC),
    )


def _request(max_tokens: int = 4096) -> ModelRequest:
    return ModelRequest(
        model="m", messages=(ModelMessage(role="user", spans=(_span("hello"),)),), max_tokens=max_tokens
    )


class _RecordingDispatch:
    """Captures every `cost_estimate` passed to `model()`, and scripts a
    canned sequence of stream results — one list of events per call."""

    def __init__(self, script: list[list[Any]]) -> None:
        self._script = script
        self.model_calls: list[BudgetDims] = []
        self.shell_calls: list[ShellArgs] = []

    async def model(self, request: ModelRequest, cost_estimate: BudgetDims) -> list[Any]:
        self.model_calls.append(cost_estimate)
        return self._script[len(self.model_calls) - 1]

    async def shell(self, args: ShellArgs, cost_estimate: BudgetDims = _ZERO_BUDGET, **kw: Any) -> ToolResult:
        self.shell_calls.append(args)
        return ToolResult(call_id=args.call.call_id, spans=(), exit_code=0)

    async def read(self, *a: Any, **kw: Any) -> Any:
        raise NotImplementedError

    async def index(self, *a: Any, **kw: Any) -> Any:
        raise NotImplementedError


# --------------------------------------------------------------- the bug fix


async def test_the_reservation_uses_completion_tokens_for_max_tokens() -> None:
    """Audit A3: `max_tokens` is a COMPLETION ceiling. All four pre-M1b sites
    reserved it as `prompt_tokens` — one bug, four copies."""
    request = _request(max_tokens=999)
    dispatch = _RecordingDispatch([[TextDelta(text="ok"), StopEvent(reason="end")]])

    await SingleTurn().invoke(dispatch, request)

    assert dispatch.model_calls[0].completion_tokens == 999
    assert dispatch.model_calls[0].prompt_tokens != 999  # not the bug's dimension mismatch


# ----------------------------------------------------------------- SingleTurn


async def test_single_turn_collects_text_and_stop_reason() -> None:
    dispatch = _RecordingDispatch(
        [[TextDelta(text="part "), TextDelta(text="two"), StopEvent(reason="max_tokens")]]
    )

    result = await SingleTurn().invoke(dispatch, _request())

    assert result.text == "part two"
    assert result.stop_reason == "max_tokens"
    assert result.rounds == 1
    assert len(dispatch.model_calls) == 1  # single turn, never loops


# -------------------------------------------------------------------- ToolLoop


async def test_tool_loop_requires_a_worktree() -> None:
    """A tool call must reach `dispatch.shell` against a real worktree — a
    role wiring ToolLoop without one is a configuration error, caught here."""
    with pytest.raises(ValueError, match="worktree"):
        await ToolLoop().invoke(_RecordingDispatch([]), _request())


async def test_tool_loop_stops_when_the_model_makes_no_tool_call() -> None:
    dispatch = _RecordingDispatch([[TextDelta(text="done"), StopEvent(reason="end")]])

    result = await ToolLoop().invoke(dispatch, _request(), worktree=_WORKTREE)

    assert result.text == "done"
    assert result.rounds == 1
    assert dispatch.shell_calls == []


async def test_tool_loop_round_trips_a_tool_call_correctly() -> None:
    """Sprint 2's malformed protocol, checked here: the assistant's own
    `tool_calls` message must precede the `tool` result, and the result must
    name the `tool_call_id` it answers."""
    dispatch = _RecordingDispatch(
        [
            [
                ToolCallDelta(call_id="c1", name="bash", args_json_fragment='{"cmd":"ls"}'),
                StopEvent(reason="tool_use"),
            ],
            [TextDelta(text="the file exists"), StopEvent(reason="end")],
        ]
    )

    result = await ToolLoop().invoke(dispatch, _request(), worktree=_WORKTREE)

    assert result.text == "the file exists"
    assert result.rounds == 2
    assert len(dispatch.shell_calls) == 1
    assert dispatch.shell_calls[0].call.call_id == "c1"


async def test_tool_loop_justifying_spans_accumulate_across_rounds() -> None:
    """Audit F5: tool output is UNTRUSTED_EXTERNAL at birth and is fed back
    to the model, so from round 2 the spans justifying the NEXT call must
    include what the FIRST round's tool produced — not just the initial
    context. Monotone, never shrinking."""
    tool_span = TaintSpan(
        span_id=SpanId("tool-1"),
        label=Provenance.UNTRUSTED_EXTERNAL,
        text="ls output",
        source="tool:bash",
        created_at=datetime.now(UTC),
    )

    class _TwoCallDispatch(_RecordingDispatch):
        async def shell(
            self, args: ShellArgs, cost_estimate: BudgetDims = _ZERO_BUDGET, **kw: Any
        ) -> ToolResult:
            self.shell_calls.append(args)
            return ToolResult(call_id=args.call.call_id, spans=(tool_span,), exit_code=0)

    dispatch = _TwoCallDispatch(
        [
            [ToolCallDelta(call_id="c1", name="bash", args_json_fragment="{}"), StopEvent(reason="tool_use")],
            [ToolCallDelta(call_id="c2", name="bash", args_json_fragment="{}"), StopEvent(reason="tool_use")],
            [TextDelta(text="done"), StopEvent(reason="end")],
        ]
    )

    seed = _span("seed")
    await ToolLoop().invoke(dispatch, _request(), worktree=_WORKTREE, justifying=(seed,))

    # ToolCall.justifying_spans is tuple[SpanId, ...]; round 2's call must
    # name both the seed span AND round 1's tool span — never just the seed.
    first_call_ids = set(dispatch.shell_calls[0].call.justifying_spans)
    second_call_ids = set(dispatch.shell_calls[1].call.justifying_spans)
    assert first_call_ids == {seed.span_id}
    assert second_call_ids == {seed.span_id, tool_span.span_id}


# ------------------------------------------------------------------ registry


def test_get_inference_raises_at_the_name_resolution_call_site() -> None:
    with pytest.raises(UnknownInference, match="nope"):
        get_inference("nope")


def test_registry_round_trips_every_registered_name() -> None:
    for name in INFERENCE:
        assert get_inference(name) is INFERENCE[name]
