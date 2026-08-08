"""I10's CI floor (T4, `TASK-056`): harness-side, byte-identical-prefix
stability over a fixed replay.

**Why this replay is built here, not read from
`tests/fixtures/aether_prompt_replay/`.** T0's fixtures record one prompt
per *node kind* across a heterogeneous topology (retrieve → architect →
generate → apply → evaluate → repair), and different node kinds legitimately
have different L1 system text and L4 task framing — comparing *across* node
kinds would fail by design and prove nothing about I10. ADR-0010's guarantee
is that L1-L4 do not mutate *within* a run of the *same* role — the shape a
bounded repair unroll or a `ToolLoop` round actually produces, calling the
same role repeatedly while only L5 (the growing dialogue) changes. This
module builds exactly that shape directly through `LayeredAssembler`, with a
fixed, deterministic script, and is the "fixed replay" the floor is taken
over. T0's fixtures remain the *right* fixture for T5's separate concern —
prompts staying byte-identical across a refactor — and the two are not
interchangeable.
"""

from __future__ import annotations

from aether.agency.context.assembler import LayeredAssembler
from aether.agency.context.stability import prefix_stability, wire_form
from aether.domain.context import ContextBlock, Layer
from aether.domain.taint import Provenance


def _repair_iteration_request(iteration: int):
    """The shape of one repair iteration: L1 (system) and L4 (task) are
    fixed; L5 (previous attempt + gate output) grows every call — exactly
    ADR-0010's table."""
    blocks = (
        ContextBlock(
            layer=Layer.L4_TASK, label=Provenance.OPERATOR, text="fix add()", source_id="instructions"
        ),
        ContextBlock(
            layer=Layer.L5_DIALOGUE,
            label=Provenance.AGENT,
            text=f"attempt #{iteration}: still failing",
            source_id="gate_output",
        ),
    )
    return LayeredAssembler().assemble(
        role="You are a precise software engineer.",
        blocks=blocks,
        contract="Reply with a unified diff.",
        model="m",
        max_tokens=4096,
        node_id="repair",
    )


def test_l1_l4_prefix_is_byte_identical_across_every_request_in_a_run() -> None:
    """I10's mechanism, gated at exactly 1.0 — not a calibration target.
    L1-L4 do not mutate within a run by construction, so anything less than
    1.0 here is a defect in the assembler, not a metric to tune."""
    replay = [wire_form(_repair_iteration_request(i)) for i in range(1, 4)]

    assert prefix_stability(replay) == 1.0


def test_prefix_stability_goes_red_when_a_layer_mutates() -> None:
    """The negative test `measurement.md` §5 requires: mutate an L4 block
    between two requests in the replay and assert the rate drops below 1.0."""
    stable = [wire_form(_repair_iteration_request(i)) for i in range(1, 3)]

    mutated_request = LayeredAssembler().assemble(
        role="You are a precise software engineer.",
        blocks=(
            ContextBlock(
                layer=Layer.L4_TASK,
                label=Provenance.OPERATOR,
                text="fix add() DIFFERENTLY",  # L4 mutated — must not happen within a run
                source_id="instructions",
            ),
            ContextBlock(
                layer=Layer.L5_DIALOGUE, label=Provenance.AGENT, text="attempt #3", source_id="gate_output"
            ),
        ),
        contract="Reply with a unified diff.",
        model="m",
        max_tokens=4096,
        node_id="repair",
    )
    replay = [*stable, wire_form(mutated_request)]

    assert prefix_stability(replay) < 1.0


def test_an_empty_replay_is_vacuously_stable() -> None:
    assert prefix_stability([]) == 1.0


def test_a_single_request_replay_is_stable() -> None:
    assert prefix_stability([wire_form(_repair_iteration_request(1))]) == 1.0
