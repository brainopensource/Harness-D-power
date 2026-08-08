"""I10's mechanism — harness-side, byte-identical-prefix stability over a
fixed replay (ADR-0010, `spec.md` §2 I10), **not** a provider-reported
cache-hit rate: `cache_control` semantics are provider-specific,
`adapters/model_provider/openai_compatible.py:40` records that breakpoints
are not emitted on the wire there at all, and the local B2 endpoint may
expose no cache metric whatsoever — a gate keyed to a provider metric would
be unmeasurable on the reference instrument.

Operates on the **wire form** of a `ModelRequest` (`wire_form()` below), not
on `ModelRequest` objects directly: a `TaintSpan`'s `span_id` and
`created_at` differ on every run by construction, so comparing spans
object-for-object would test the clock rather than the prompt. `label` is
kept — a provenance change is a real content change (T2.5). This is the same
translation `scripts/gen_prompt_replay.py` uses to build the checked-in
golden-prompt replay (T0); that script imports it from here rather than
keeping a second copy.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from aether.domain.model_io import ModelRequest


def wire_form(request: ModelRequest) -> dict[str, Any]:
    """The bytes that reach the endpoint, and nothing else."""
    return {
        "model": request.model,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "seed": request.seed,
        "tools": [t.model_dump(mode="json") for t in request.tools],
        "messages": [
            {
                "role": m.role,
                "text": "".join(s.text for s in m.spans),
                "labels": [s.label.value for s in m.spans],
                "cache_breakpoint": m.cache_breakpoint,
                "tool_calls": [c.model_dump(mode="json") for c in m.tool_calls],
                "tool_call_id": m.tool_call_id,
            }
            for m in request.messages
        ],
    }


def stable_prefix(wire: dict[str, Any]) -> str:
    """The canonical bytes of everything through the **last** cache
    breakpoint — L1-L4 by construction, since `LayeredAssembler` marks
    exactly those three layer boundaries and nothing else. Messages after the
    last breakpoint are L5, the only layer ADR-0010 permits to mutate within
    a run, and are deliberately excluded from this comparison."""
    messages = wire["messages"]
    last_boundary = -1
    for index, message in enumerate(messages):
        if message.get("cache_breakpoint"):
            last_boundary = index
    stable_messages = messages[: last_boundary + 1]
    canonical = {
        "model": wire["model"],
        "max_tokens": wire["max_tokens"],
        "tools": wire["tools"],
        "messages": [{"role": m["role"], "text": m["text"], "labels": m["labels"]} for m in stable_messages],
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"))


def prefix_stability(wires: Sequence[dict[str, Any]]) -> float:
    """Fraction of `wires` whose stable prefix is byte-identical to the
    first's. L1-L4 do not mutate within a run **by construction**, so the
    gated rate is exactly 1.0 and anything less is a defect, not a tuning
    knob (`sprint-05-dev-prompt.md` T4.3)."""
    if not wires:
        return 1.0
    reference = stable_prefix(wires[0])
    matches = sum(1 for wire in wires if stable_prefix(wire) == reference)
    return matches / len(wires)


__all__ = ["prefix_stability", "stable_prefix", "wire_form"]
