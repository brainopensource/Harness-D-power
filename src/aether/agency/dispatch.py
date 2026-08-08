"""`EffectDispatch` — the verbs `agency/` needs from the choke point, declared
where they are consumed.

`agency/` sits below `workflow/` (ADR-0018) and cannot import
`workflow.dispatch_facade.DispatchFacade` — that would be an upward import.
So this is a **structural Protocol**, the same pattern `measurement/evaluator
.py`'s `SandboxRunner` already uses for the same reason: *"Not a port (ADR-0005
rev. 2 ratifies eight port areas); a structural collaborator."* Python's
structural typing means neither module imports the other — `DispatchFacade`
satisfies this Protocol without ever importing it, and no new port and no ADR
are needed (`coding_guidelines.md` §2.4).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aether.domain.budget import BudgetDims
from aether.domain.effects import IndexArgs, IndexResult, ReadArgs, ShellArgs
from aether.domain.model_io import ModelRequest, ModelStreamEvent
from aether.domain.taint import TaintSpan
from aether.domain.tools import ToolResult
from aether.domain.workspace import FileSlice

_ZERO_BUDGET = BudgetDims()  # Frozen/immutable — safe as a shared default (ruff B008)


@runtime_checkable
class EffectDispatch(Protocol):
    """The four verbs a capability may need. Every one of them still passes
    the real dispatch choke point (I5) — this Protocol is a narrower *view*
    of `DispatchFacade`, not a second path around it."""

    async def read(self, args: ReadArgs, cost_estimate: BudgetDims = _ZERO_BUDGET) -> FileSlice: ...

    async def index(self, args: IndexArgs, cost_estimate: BudgetDims = _ZERO_BUDGET) -> IndexResult: ...

    async def shell(
        self,
        args: ShellArgs,
        cost_estimate: BudgetDims = _ZERO_BUDGET,
        *,
        justifying_spans: tuple[TaintSpan, ...] = (),
    ) -> ToolResult: ...

    async def model(self, request: ModelRequest, cost_estimate: BudgetDims) -> list[ModelStreamEvent]: ...


__all__ = ["EffectDispatch"]
