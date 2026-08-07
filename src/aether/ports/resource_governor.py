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

    async def remaining(self, run_id: RunId) -> BudgetDims: ...
