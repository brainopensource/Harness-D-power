"""`Envelope` — the fields every node payload carries.

`RetrievedContext`, `GeneratedPatch`, `AppliedPatch` and `EvaluatedCandidate`
(`workflow/nodes/*.py`) each independently re-declared `task: Task` and
`worktree: WorktreeRef` — the task being attempted and the worktree it is
being attempted in never change as a candidate flows through the DAG. This
base collects that shared pair so a field added to it is a one-file change.

`iteration: int` is deliberately NOT here: only three of the four types carry
it (`RetrievedContext` does not — retrieval happens once, before any repair
loop), so folding it into the envelope would give `RetrievedContext` a field
it has no use for. Each node keeps declaring it itself.

The four payload types must stay structurally and nominally distinct —
`workflow/validator.py::check_socket_compatibility` tells node kinds apart by
their socket type, and collapsing them onto one concrete class would defeat
that check. Subclassing (rather than, say, a single parametrized type) keeps
each one its own class.
"""

from __future__ import annotations

from aether.domain.ids import Frozen
from aether.domain.task import Task
from aether.domain.workspace import WorktreeRef


class Envelope(Frozen):
    task: Task
    worktree: WorktreeRef
