"""Evaluator — runs a TaskSpec against a pristine injected test suite. Optional; in the TCB.

See docs/03-contracts-and-models/hexagonal-ports.md#orchestration--improvement and
docs/08-decisions/0007-trusted-computing-base.md. Unbound under `gates = "none"`, in which case
**no `GateReport` exists** — not an empty one. Has no degraded mode: it aborts rather than
serving a partial verdict (docs/03-contracts-and-models/error-taxonomy.md).
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.control import RunContext
from sagiha.domain.work import GateReport, TaskSpec

PORT_VERSION: Final = 2
STABILITY: Final = "provisional"


class Evaluator(Protocol):
    """Optional — unbound under profiles with `gates = "none"`.

    Takes a `RunContext`, not a bare branch id (v2, R4): acceptance criteria run through the
    same dispatch choke point as every other tool call, which requires `run_id`,
    `workspace_root`, `autonomy_level`, and remaining budget — a branch identifier alone
    cannot authorize or lease anything.
    """

    async def evaluate(self, task: TaskSpec, ctx: RunContext) -> GateReport: ...
