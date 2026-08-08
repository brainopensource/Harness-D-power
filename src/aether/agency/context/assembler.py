"""`LayeredAssembler` — ADR-0010's five prefix layers, implemented exactly
(`TASK-056`, was `TASK-031`). Closes I10 and audit finding **A6**.

Prompt layering is `f"{instructions}\\n\\n## Header\\n{text}"` string
concatenation inside `architect.py:92-96,145-152` today, so there is no
object that holds the layers and nothing to enforce order over. This module
is that object, and it makes A6 (provenance laundering by concatenation)
**structurally impossible**: a node passes `ContextBlock`s to `assemble()`
and never touches a bare string itself, so it cannot merge model output into
an operator-labelled instruction the way `architect.py:92` does today.
"""

from __future__ import annotations

from datetime import UTC, datetime

from aether.domain.context import ContextBlock, Layer
from aether.domain.ids import SpanId
from aether.domain.model_io import ModelMessage, ModelRequest
from aether.domain.taint import Provenance, TaintSpan
from aether.domain.tools import ToolSpec

#: ADR-0010: "at most four `cache_control` breakpoints, one per L1-L4
#: boundary." L2 (tool schemas) is never a message — it rides on
#: `ModelRequest.tools` — so only L1, L3 and L4 ever carry one; the fourth is
#: spare by design, not an oversight.
MAX_CACHE_BREAKPOINTS = 4

#: The layers that mark a cache boundary, in wire order. L5 is deliberately
#: absent: it is the only layer ADR-0010 permits to mutate within a run, and
#: marking a breakpoint on a layer that moves every turn would be a lie to
#: the provider about what is stable.
_BOUNDARY_LAYERS = (Layer.L1_SYSTEM, Layer.L3_REPO, Layer.L4_TASK)


class TooManyCacheBreakpoints(Exception):
    """Raised at assembly, never discovered from a provider's cache-hit
    telemetry after the fact (ADR-0010's ceiling)."""


class LayeredAssembler:
    """`role` and `contract` become the L1 system block; every other
    `ContextBlock` is grouped by its own declared layer and rendered as one
    `ModelMessage` per non-empty layer, in L1→L5 order."""

    name = "layered_v1"

    def assemble(
        self,
        *,
        role: str,
        blocks: tuple[ContextBlock, ...],
        contract: str,
        model: str,
        max_tokens: int,
        tools: tuple[ToolSpec, ...] = (),
        node_id: str,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> ModelRequest:
        system_text = f"{role}\n\n{contract}" if contract else role
        system_block = ContextBlock(
            layer=Layer.L1_SYSTEM, label=Provenance.TRUSTED_SYSTEM, text=system_text, source_id="system"
        )

        by_layer: dict[Layer, list[ContextBlock]] = {}
        for block in (system_block, *blocks):
            by_layer.setdefault(block.layer, []).append(block)

        messages: list[ModelMessage] = []
        breakpoints_used = 0
        for layer in Layer:
            layer_blocks = by_layer.get(layer, [])
            if not layer_blocks:
                continue
            spans = tuple(
                self._span_from_block(block, node_id, ordinal) for ordinal, block in enumerate(layer_blocks)
            )
            is_boundary = layer in _BOUNDARY_LAYERS
            if is_boundary:
                breakpoints_used += 1
            messages.append(
                ModelMessage(
                    role="system" if layer is Layer.L1_SYSTEM else "user",
                    spans=spans,
                    cache_breakpoint=is_boundary,
                )
            )

        _check_breakpoint_budget(breakpoints_used)

        return ModelRequest(
            model=model,
            messages=tuple(messages),
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )

    def _span_from_block(self, block: ContextBlock, node_id: str, ordinal: int) -> TaintSpan:
        """The ONLY place a `TaintSpan` is constructed from context in this
        tree. It carries the block's own label — set by the source that
        produced the block, never decided here — which is what closes A4 and
        makes A6 structurally impossible (module docstring).
        """
        text = f"{block.heading}\n{block.text}" if block.heading else block.text
        return TaintSpan(
            span_id=SpanId(f"{node_id}-{block.layer.name.lower()}-{ordinal}"),
            label=block.label,
            text=text,
            source=block.source_id,
            created_at=datetime.now(UTC),
        )


def _check_breakpoint_budget(count: int) -> None:
    """A separate function so the ceiling is testable directly: with only
    three fixed boundary layers (L1, L3, L4) `assemble()` can never actually
    reach five breakpoints today, but the check is the enforcement mechanism
    for ADR-0010's stated ceiling, and `coding_guidelines.md` §1.2 requires
    every gate to ship with a negative test proving it can fail — this
    function is what that test calls directly."""
    if count > MAX_CACHE_BREAKPOINTS:
        raise TooManyCacheBreakpoints(
            f"{count} cache breakpoints requested; ADR-0010 caps this at {MAX_CACHE_BREAKPOINTS}"
        )


__all__ = ["MAX_CACHE_BREAKPOINTS", "LayeredAssembler", "TooManyCacheBreakpoints"]
