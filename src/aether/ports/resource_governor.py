"""ResourceGovernor — reserve-before-effect budget ledger boundary."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aether.domain.budget import Actuals, BudgetDims, Lease
from aether.domain.ids import Frozen, LeaseId, RunId


class ReservationDenied(Frozen):
    shortfall: BudgetDims
    rationale: str


@runtime_checkable
class ResourceGovernor(Protocol):
    """Reserve-before-effect ledger (spec §5). The dispatcher refuses any effect
    without a live lease, which makes after-the-fact accounting structurally
    unrepresentable. Integer arithmetic only; atomic under one asyncio.Lock now,
    protocol unchanged if the governor ever moves out of process (I3)."""

    async def reserve(
        self, run_id: RunId, dims: BudgetDims, parent: LeaseId | None = None
    ) -> Lease | ReservationDenied: ...

    async def commit(self, lease_id: LeaseId, actuals: Actuals) -> None:
        """actuals <= reserved => remainder released; actuals > reserved => typed
        BudgetOverrun event emitted AND reality debited (the ledger never lies)."""
        ...

    async def release(self, lease_id: LeaseId) -> None:
        """Cancel path; idempotent. Child release refunds the parent lease,
        not the global pool — Best-of-N loser cancellation refunds correctly."""
        ...

    async def spent(self, run_id: RunId) -> BudgetDims:
        """Total committed actuals for the run.

        Added in Sprint 3.5 because `remaining()` had been *returning* this
        since TASK-034 while being named the opposite. Two names for two facts
        is the fix; one name for the wrong fact is how a caller writing
        `if remaining < cost: stop` gets the inverted answer and stops when it
        has budget, or spends when it does not.
        """
        ...

    async def remaining(self, run_id: RunId) -> BudgetDims | None:
        """What is left of the run's seeded ceiling, or `None` when no ceiling
        was seeded — an unbounded run has no remainder, and reporting zeros for
        it would read as "exhausted".

        Informational. The *decision* to spend belongs to `reserve()`, which
        answers with a typed `ReservationDenied`; that is the reserve-before-
        effect design and this method is not a second, weaker gate.
        """
        ...
