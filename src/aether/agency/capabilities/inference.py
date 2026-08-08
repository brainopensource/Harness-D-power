"""`Inference` — how the model is called and how its stream is reduced
(`TASK-055`).

Collapses the model-call-and-collect idiom written four times
(`architect.py:88,142`, `repair.py:180`, `generate.py:146`) into one
implementation, twice — once for the common case, once for the tool loop —
and fixes the bug present in all four sites: `max_tokens` is a *completion*
ceiling, and every one of them reserved it in the `prompt_tokens` dimension.

`ToolLoop` is `generate.py:157-212`'s `MAX_ROUNDS` loop, promoted so any role
can use it — today a planner that wants to list the repository structurally
cannot, because the loop exists only inside `GenerateStep`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aether.agency.dispatch import EffectDispatch
from aether.agency.registry import Registry
from aether.domain.budget import BudgetDims
from aether.domain.effects import ShellArgs
from aether.domain.ids import Frozen
from aether.domain.model_io import (
    ModelMessage,
    ModelRequest,
    StopReason,
    TextDelta,
    ToolCallDelta,
    ToolCallRef,
)
from aether.domain.taint import TaintSpan
from aether.domain.tools import ToolCall
from aether.domain.workspace import WorktreeRef


class InferenceResult(Frozen):
    text: str
    stop_reason: StopReason = "end"
    rounds: int = 1


def _reserve(request: ModelRequest) -> BudgetDims:
    """`max_tokens` is a COMPLETION ceiling. All four pre-M1b sites reserved
    it as `prompt_tokens` — one bug, four copies (audit A3).

    The prompt estimate is a local heuristic (roughly 4 characters per
    token), not a provider round-trip: `agency/` has only the four
    `EffectDispatch` verbs, none of which is a tokenizer call, and the
    committed `Actuals` — filled by `composition.py`'s `_model` closure at
    the one place that knows both the model and the real token counts —
    remain the accounting of record regardless of how conservative this
    reservation is. `usd_micros` stays 0 here on purpose; moving the denial
    onto the offending call is `TASK-044`'s separate, additive scope.
    """
    prompt_chars = sum(len(span.text) for message in request.messages for span in message.spans)
    return BudgetDims(prompt_tokens=max(1, prompt_chars // 4), completion_tokens=request.max_tokens)


@runtime_checkable
class Inference(Protocol):
    """How the model is called and how its stream is reduced."""

    name: str

    async def invoke(
        self,
        dispatch: EffectDispatch,
        request: ModelRequest,
        *,
        worktree: WorktreeRef | None = None,
        justifying: tuple[TaintSpan, ...] = (),
    ) -> InferenceResult: ...


class SingleTurn:
    """One request, collect deltas, stop. Today's architect / reflector /
    repair idiom, minus the duplication."""

    name = "single_turn"

    async def invoke(
        self,
        dispatch: EffectDispatch,
        request: ModelRequest,
        *,
        worktree: WorktreeRef | None = None,
        justifying: tuple[TaintSpan, ...] = (),
    ) -> InferenceResult:
        events = await dispatch.model(request, _reserve(request))
        parts: list[str] = []
        stop_reason: StopReason = "end"
        for event in events:
            if isinstance(event, TextDelta):
                parts.append(event.text)
            elif event.kind == "stop":
                stop_reason = event.reason
        return InferenceResult(text="".join(parts), stop_reason=stop_reason)


class ToolLoop:
    """`generate.py:157-212`'s tool-calling loop, ported unchanged in
    behaviour: the assistant's own `tool_calls` message precedes the `tool`
    results answering it, and each result names the `tool_call_id` it
    answers — every OpenAI-compatible endpoint requires both, and Sprint 2
    shipped neither (the path had only run against mocks returning no tool
    calls).

    `justifying` accumulates each round's tool results before the next
    request (audit F5): tool output is `UNTRUSTED_EXTERNAL` at birth and is
    fed back to the model, so from round 2 it can steer a tool call, and the
    spans justifying the *next* call are not the spans that justified the
    first. A monotone accumulation is what makes I11's predicate reachable
    on this path at all.
    """

    name = "tool_loop"
    MAX_ROUNDS = 4

    async def invoke(
        self,
        dispatch: EffectDispatch,
        request: ModelRequest,
        *,
        worktree: WorktreeRef | None = None,
        justifying: tuple[TaintSpan, ...] = (),
    ) -> InferenceResult:
        if worktree is None:
            raise ValueError("ToolLoop needs a worktree to dispatch shell calls against")

        messages: list[ModelMessage] = list(request.messages)
        parts: list[str] = []
        stop_reason: StopReason = "end"
        rounds_run = 0

        for _round in range(self.MAX_ROUNDS):
            rounds_run += 1
            round_request = request.model_copy(update={"messages": tuple(messages)})
            events = await dispatch.model(round_request, _reserve(round_request))

            tool_calls: dict[str, dict[str, str]] = {}
            for event in events:
                if isinstance(event, TextDelta):
                    parts.append(event.text)
                elif isinstance(event, ToolCallDelta):
                    call = tool_calls.setdefault(event.call_id, {"name": "", "args": ""})
                    if event.name:
                        call["name"] = event.name
                    call["args"] += event.args_json_fragment
                elif event.kind == "stop":
                    stop_reason = event.reason

            if not tool_calls or stop_reason != "tool_use":
                break

            messages.append(
                ModelMessage(
                    role="assistant",
                    spans=(),
                    tool_calls=tuple(
                        ToolCallRef(call_id=call_id, name=info["name"], args_json=info["args"] or "{}")
                        for call_id, info in tool_calls.items()
                    ),
                )
            )

            for call_id, info in tool_calls.items():
                tool_call = ToolCall(
                    call_id=call_id,
                    name=info["name"],
                    args_json=info["args"] or "{}",
                    justifying_spans=tuple(s.span_id for s in justifying),
                )
                result = await dispatch.shell(
                    ShellArgs(worktree=worktree, call=tool_call),
                    BudgetDims(wall_clock_ms=30000),
                    justifying_spans=justifying,
                )
                messages.append(ModelMessage(role="tool", spans=result.spans, tool_call_id=call_id))
                justifying = (*justifying, *result.spans)

        return InferenceResult(text="".join(parts), stop_reason=stop_reason, rounds=rounds_run)


class UnknownInference(Exception):
    """Raised at construction. A role naming an inference strategy nobody
    implements must fail at load, not at the moment the first prompt is
    assembled."""


INFERENCE: dict[str, Inference] = {
    SingleTurn.name: SingleTurn(),
    ToolLoop.name: ToolLoop(),
}
_REGISTRY: Registry[Inference] = Registry("inference strategy", INFERENCE, unknown=UnknownInference)


def get_inference(name: str) -> Inference:
    return _REGISTRY.get(name)


__all__ = [
    "INFERENCE",
    "Inference",
    "InferenceResult",
    "SingleTurn",
    "ToolLoop",
    "UnknownInference",
    "get_inference",
]
