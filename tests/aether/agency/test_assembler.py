"""`LayeredAssembler` (T4, `TASK-056`) — ADR-0010's five layers, one
`TaintSpan` construction site, and the four-breakpoint ceiling.
"""

from __future__ import annotations

import pytest

from aether.agency.context.assembler import (
    MAX_CACHE_BREAKPOINTS,
    LayeredAssembler,
    TooManyCacheBreakpoints,
    _check_breakpoint_budget,
)
from aether.domain.context import ContextBlock, Layer
from aether.domain.taint import Provenance


def _block(layer: Layer, label: Provenance, text: str, source_id: str, heading: str = "") -> ContextBlock:
    return ContextBlock(layer=layer, label=label, text=text, source_id=source_id, heading=heading)


def test_layers_render_in_order_l1_through_l5() -> None:
    blocks = (
        _block(Layer.L5_DIALOGUE, Provenance.AGENT, "dialogue", "d"),
        _block(Layer.L3_REPO, Provenance.AGENT, "repo", "r"),
        _block(Layer.L4_TASK, Provenance.OPERATOR, "task", "t"),
    )

    request = LayeredAssembler().assemble(
        role="you are a bot", blocks=blocks, contract="reply in X", model="m", max_tokens=100, node_id="n1"
    )

    texts = ["".join(s.text for s in m.spans) for m in request.messages]
    assert "you are a bot" in texts[0] and "reply in X" in texts[0]  # L1
    assert texts[1] == "repo"  # L3
    assert texts[2] == "task"  # L4
    assert texts[3] == "dialogue"  # L5


def test_l1_is_the_only_system_message() -> None:
    request = LayeredAssembler().assemble(
        role="r", blocks=(), contract="c", model="m", max_tokens=10, node_id="n1"
    )
    assert [m.role for m in request.messages] == ["system"]


def test_l2_tools_ride_on_model_request_not_a_message() -> None:
    from aether.domain.tools import ToolSpec

    tool = ToolSpec(name="bash", description="run a command", params_json_schema="{}", effect_class="shell")
    request = LayeredAssembler().assemble(
        role="r", blocks=(), contract="c", model="m", max_tokens=10, tools=(tool,), node_id="n1"
    )
    assert request.tools == (tool,)
    assert all(m.role != "tool" for m in request.messages)  # no message carries the schema


def test_exactly_three_breakpoints_at_l1_l3_l4() -> None:
    blocks = (
        _block(Layer.L3_REPO, Provenance.AGENT, "repo", "r"),
        _block(Layer.L4_TASK, Provenance.OPERATOR, "task", "t"),
        _block(Layer.L5_DIALOGUE, Provenance.AGENT, "dialogue", "d"),
    )
    request = LayeredAssembler().assemble(
        role="r", blocks=blocks, contract="c", model="m", max_tokens=10, node_id="n1"
    )

    breakpoints = [m.cache_breakpoint for m in request.messages]
    assert breakpoints == [True, True, True, False]  # L1, L3, L4 marked; L5 is not


def test_a_layer_with_no_blocks_produces_no_message() -> None:
    """Only L1 has content: L2-L5 must not appear as empty messages."""
    request = LayeredAssembler().assemble(
        role="r", blocks=(), contract="c", model="m", max_tokens=10, node_id="n1"
    )
    assert len(request.messages) == 1


def test_missing_gate_output_style_note_reaches_the_wire_via_heading() -> None:
    """Headings are part of the rendered text — `=== mod.py ===` style
    markers must survive assembly, since T5's golden-prompt equivalence
    depends on them matching byte-for-byte."""
    block = _block(Layer.L3_REPO, Provenance.AGENT, "def add(): ...", "entry_files", heading="=== mod.py ===")
    request = LayeredAssembler().assemble(
        role="r", blocks=(block,), contract="c", model="m", max_tokens=10, node_id="n1"
    )
    text = "".join(s.text for s in request.messages[1].spans)
    assert text == "=== mod.py ===\ndef add(): ..."


# --------------------------------------------------- provenance, one construction site


def test_the_span_carries_the_blocks_own_label_not_a_guess() -> None:
    """Closes A4: the label on the wire is exactly the label the source
    declared on the block, never re-decided by the assembler."""
    block = _block(Layer.L4_TASK, Provenance.AGENT, "a plan", "plan")
    request = LayeredAssembler().assemble(
        role="r", blocks=(block,), contract="c", model="m", max_tokens=10, node_id="n1"
    )
    span = request.messages[1].spans[0]
    assert span.label is Provenance.AGENT
    assert span.source == "plan"


def test_only_one_taint_span_construction_site_exists_in_the_module() -> None:
    """A6 is closed structurally, not by convention: grep the module for the
    literal construction and assert it appears exactly once."""
    import inspect

    from aether.agency.context import assembler as assembler_module

    source = inspect.getsource(assembler_module)
    assert source.count("TaintSpan(") == 1


# ---------------------------------------------------------- the breakpoint ceiling


def test_the_ceiling_is_four() -> None:
    assert MAX_CACHE_BREAKPOINTS == 4


def test_the_ceiling_rejects_a_fifth_breakpoint() -> None:
    """ADR-0010's stated cap, proven able to fail. `assemble()` cannot
    naturally produce a fifth breakpoint with today's three fixed layer
    boundaries (L1, L3, L4) — this calls the enforcement function directly,
    the same way `check_bounded_iteration`'s malformed fixtures test rules
    no live topology happens to violate yet."""
    with pytest.raises(TooManyCacheBreakpoints, match="5"):
        _check_breakpoint_budget(5)


def test_the_ceiling_admits_the_real_maximum() -> None:
    _check_breakpoint_budget(4)  # must not raise
