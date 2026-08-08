"""Effect payload shapes dispatched through `EffectRequest.descriptor`.

`EffectRequest.descriptor` carries each effect's payload as JSON — Frozen
models are JSON round-trippable by construction (I2/I3), so the `*Args`
models below are exactly that payload shape, not a new port. They used to
live in `composition.py`, the module that wires the concrete adapter
closures (`OpenAICompatibleProvider`, `BuiltinToolRegistry`,
`GitCliWorkspace`) — every workflow node imported them from there, which
dragged the whole adapter stack (and `httpx`, transitively) into node
modules that should be pure (spec.md §2 I1). Moving them here removes that
import edge; `composition.py` now imports them like everyone else.
"""

from __future__ import annotations

from typing import Literal

from aether.domain.ids import Frozen
from aether.domain.tools import ToolCall
from aether.domain.workspace import SymbolHit, WorktreeRef


class ReadArgs(Frozen):
    worktree: WorktreeRef
    repo_rel_path: str
    start_line: int = 1
    end_line: int = -1


class WriteArgs(Frozen):
    # "write" effect_class covers both a plain file write and a unified-diff
    # apply — `kind` discriminates which payload the `_write` closure in
    # composition.py deserializes, since EffectRequest.effect_class has no
    # third bucket.
    kind: Literal["write_file"] = "write_file"
    worktree: WorktreeRef
    repo_rel_path: str
    text: str


class ApplyPatchArgs(Frozen):
    kind: Literal["apply_patch"] = "apply_patch"
    worktree: WorktreeRef
    unified_diff: str


class ShellArgs(Frozen):
    worktree: WorktreeRef
    call: ToolCall


class IndexArgs(Frozen):
    """T2.4: the additive `effect_class` that makes `SymbolSource` reachable
    through the dispatcher instead of holding an `Indexer` handle directly —
    which I5 forbids (every effect passes the choke point)."""

    worktree: WorktreeRef
    query: str
    limit: int = 20


class IndexResult(Frozen):
    hits: tuple[SymbolHit, ...] = ()
