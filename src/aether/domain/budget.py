"""Integer-only budget vector, leases, and actuals (spec.md §5)."""

from __future__ import annotations

from pydantic import AwareDatetime

from aether.domain.ids import Frozen, LeaseId, RunId


class BudgetDims(Frozen):
    """Integer-only budget vector. Currency in micro-USD; floats are banned
    from budget arithmetic by type."""

    usd_micros: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    wall_clock_ms: int = 0
    concurrency_slots: int = 0


class Lease(Frozen):
    lease_id: LeaseId
    run_id: RunId
    reserved: BudgetDims
    parent: LeaseId | None = None  # fan-out: child leases carve a parent
    issued_at: AwareDatetime


class Actuals(Frozen):
    dims: BudgetDims


class BudgetOverrun(Frozen):
    """Emitted when `commit()` actuals exceed the reservation. Reality is
    debited regardless — the ledger never silently clamps to the reservation."""

    lease_id: LeaseId
    run_id: RunId
    reserved: BudgetDims
    actual: BudgetDims
