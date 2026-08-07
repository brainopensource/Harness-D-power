"""ResourceGovernor real implementation (TASK-034) — reserve/commit/release/
remaining as an atomic, integer-only ledger.

Production counterpart to `InMemoryResourceGovernor` (tests/aether/mocks.py),
same shape plus real atomicity via one `asyncio.Lock` (spec.md §5,
tech_stack_and_infra.md §4.5) and overrun bookkeeping. `commit()` never
silently clamps: actuals exceeding the reservation debit reality *and* record
a typed `BudgetOverrun` — the ledger never lies. A child lease's release or
commit-remainder refunds into its *parent's* remaining balance, never the
global pool — what makes Best-of-N loser cancellation correct.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from aether.domain.budget import Actuals, BudgetDims, BudgetOverrun, Lease
from aether.domain.ids import LeaseId, RunId
from aether.ports.resource_governor import ReservationDenied


def _add(a: BudgetDims, b: BudgetDims) -> BudgetDims:
    return BudgetDims(
        usd_micros=a.usd_micros + b.usd_micros,
        prompt_tokens=a.prompt_tokens + b.prompt_tokens,
        completion_tokens=a.completion_tokens + b.completion_tokens,
        wall_clock_ms=a.wall_clock_ms + b.wall_clock_ms,
        concurrency_slots=a.concurrency_slots + b.concurrency_slots,
    )


def _sub(a: BudgetDims, b: BudgetDims) -> BudgetDims:
    return BudgetDims(
        usd_micros=a.usd_micros - b.usd_micros,
        prompt_tokens=a.prompt_tokens - b.prompt_tokens,
        completion_tokens=a.completion_tokens - b.completion_tokens,
        wall_clock_ms=a.wall_clock_ms - b.wall_clock_ms,
        concurrency_slots=a.concurrency_slots - b.concurrency_slots,
    )


def _exceeds(actual: BudgetDims, reserved: BudgetDims) -> bool:
    return (
        actual.usd_micros > reserved.usd_micros
        or actual.prompt_tokens > reserved.prompt_tokens
        or actual.completion_tokens > reserved.completion_tokens
        or actual.wall_clock_ms > reserved.wall_clock_ms
        or actual.concurrency_slots > reserved.concurrency_slots
    )


class ResourceGovernor:
    """Real reserve-before-effect ledger. `reserve()` at the root (no
    `parent=`) is unconstrained unless a caller seeds a ceiling via
    `seed_run_budget()` — there is no implicit infinite pool used by mistake
    for callers who *do* seed one; a fan-out's child leases (`parent=`) are
    always bounded by the parent's own reservation."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._leases: dict[LeaseId, Lease] = {}
        self._parent_remaining: dict[LeaseId, BudgetDims] = {}
        self._run_root_remaining: dict[RunId, BudgetDims] = {}
        self._spent: dict[RunId, BudgetDims] = {}
        self._overruns: list[BudgetOverrun] = []
        self._next_id = 0

    def seed_run_budget(self, run_id: RunId, dims: BudgetDims) -> None:
        """Configure a hard ceiling for a run's top-level (non-child) reservations."""
        self._run_root_remaining[run_id] = dims

    async def reserve(
        self, run_id: RunId, dims: BudgetDims, parent: LeaseId | None = None
    ) -> Lease | ReservationDenied:
        async with self._lock:
            if parent is not None:
                parent_lease = self._leases.get(parent)
                if parent_lease is None:
                    return ReservationDenied(shortfall=dims, rationale=f"unknown parent lease {parent}")
                available = self._parent_remaining.get(parent, parent_lease.reserved)
                if _exceeds(dims, available):
                    return ReservationDenied(
                        shortfall=_sub(dims, available), rationale="parent lease exhausted"
                    )
                self._parent_remaining[parent] = _sub(available, dims)
            else:
                available = self._run_root_remaining.get(run_id)
                if available is not None and _exceeds(dims, available):
                    return ReservationDenied(
                        shortfall=_sub(dims, available), rationale="run budget exhausted"
                    )
                if available is not None:
                    self._run_root_remaining[run_id] = _sub(available, dims)

            self._next_id += 1
            lease = Lease(
                lease_id=LeaseId(f"lease-{self._next_id}"),
                run_id=run_id,
                reserved=dims,
                parent=parent,
                issued_at=datetime.now(UTC),
            )
            self._leases[lease.lease_id] = lease
            return lease

    async def commit(self, lease_id: LeaseId, actuals: Actuals) -> None:
        async with self._lock:
            lease = self._leases.pop(lease_id, None)
            if lease is None:
                return

            overran = _exceeds(actuals.dims, lease.reserved)
            if overran:
                self._overruns.append(
                    BudgetOverrun(
                        lease_id=lease_id, run_id=lease.run_id, reserved=lease.reserved, actual=actuals.dims
                    )
                )

            prior = self._spent.get(lease.run_id, BudgetDims())
            self._spent[lease.run_id] = _add(prior, actuals.dims)

            refund = BudgetDims() if overran else _sub(lease.reserved, actuals.dims)
            self._refund(lease, refund)

    async def release(self, lease_id: LeaseId) -> None:
        async with self._lock:
            lease = self._leases.pop(lease_id, None)
            if lease is None:
                return  # idempotent
            self._refund(lease, lease.reserved)

    def _refund(self, lease: Lease, amount: BudgetDims) -> None:
        if lease.parent is not None:
            prior = self._parent_remaining.get(lease.parent, BudgetDims())
            self._parent_remaining[lease.parent] = _add(prior, amount)
        else:
            prior = self._run_root_remaining.get(lease.run_id)
            if prior is not None:
                self._run_root_remaining[lease.run_id] = _add(prior, amount)

    async def remaining(self, run_id: RunId) -> BudgetDims:
        async with self._lock:
            return self._spent.get(run_id, BudgetDims())

    def overruns(self) -> tuple[BudgetOverrun, ...]:
        """Not part of the `ResourceGovernor` protocol — read by the composition
        root / event bus wiring (Step 10/11) to surface `BudgetOverrun` events."""
        return tuple(self._overruns)
