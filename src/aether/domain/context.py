"""Prompt-assembly building blocks (T2/T4, ADR-0010, ADR-0015) — pure, zero
I/O (I1). `agency/` and `workflow/` both need these shapes; `domain/` is the
one layer both can import.
"""

from __future__ import annotations

from enum import IntEnum

from aether.domain.ids import Frozen
from aether.domain.taint import Provenance
from aether.domain.task import Task
from aether.domain.workspace import WorktreeRef


class Layer(IntEnum):
    """ADR-0010's five prefix layers. `IntEnum` so ordering IS the ordering —
    an assembler that sorts blocks by layer cannot emit L5 before L4 by
    accident."""

    L1_SYSTEM = 1  # system prompt, policy text, standing instructions
    L2_TOOLS = 2  # tool schemas (frozen at composition, I6) — not a message; see assembler
    L3_REPO = 3  # generated repo brief — THE ablated layer (ADR-0010)
    L4_TASK = 4  # task statement
    L5_DIALOGUE = 5  # dialogue, trajectory, tool output — the only layer that moves


class ContextBlock(Frozen):
    """One labelled slice of prompt content.

    `label` is set by the SOURCE that produced it and never by a node — that
    single rule is the whole of finding A4 (`capability_layer.md` §1):
    provenance was a decision made ad hoc at ten `TaintSpan(...)` call sites
    across three node files, which is how repository content and test
    tracebacks both came to be labelled `Provenance.AGENT`. A node that only
    ever holds `ContextBlock`s cannot launder provenance by concatenation,
    because it never touches a bare string until the assembler turns a block
    into a `TaintSpan` carrying the block's own label (T4).
    """

    layer: Layer
    label: Provenance
    heading: str = ""  # e.g. "=== mod.py ===" — rendered, so it is part of the golden
    text: str
    source_id: str  # which source produced this block; trajectory + ablation accounting


class ContextRequest(Frozen):
    """Everything a `ContextSource` may look at. A frozen, read-only
    projection of whatever payload `ModelNode` holds — not `RetrievedContext`
    or `EvaluatedCandidate`, which live in `workflow/nodes/` and which
    `agency/` may not import.

    Building this is `ModelNode`'s job (T5); a source never constructs one
    itself, which is what makes every source testable with no worktree, no
    executor and no topology (`sprint-05.md` §T2).
    """

    task: Task
    worktree: WorktreeRef
    instructions: str
    entry_files: tuple[str, ...] = ()
    plan: str = ""  # architect output, if any (TASK-048)
    previous_attempt: str = ""  # the patch text being repaired
    gate_detail: str = ""  # the failing test output
    iteration: int = 0
    max_bytes: int = 20_000


__all__ = ["ContextBlock", "ContextRequest", "Layer"]
