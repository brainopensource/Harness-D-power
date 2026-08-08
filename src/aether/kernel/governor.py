"""ResourceGovernor real implementation (TASK-034) — reserve/commit/release/
remaining as an atomic, integer-only ledger.

Production counterpart to `InMemoryResourceGovernor` (tests/aether/mocks.py),
same shape plus real atomicity via one `asyncio.Lock` (spec.md §5,
tech_stack_and_infra.md §4.5) and overrun bookkeeping. `commit()` never
silently clamps: actuals exceeding the reservation debit reality *and* record
a typed `BudgetOverrun`, which is emitted to the bus as `BudgetOverrunEmitted`
so the ledger's honesty signal reaches a client instead of dying in a private
list — the ledger never lies, and now it does not whisper either. A child lease's release or
commit-remainder refunds into its *parent's* remaining balance, never the
global pool — what makes Best-of-N loser cancellation correct.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from aether.domain.budget import Actuals, BudgetDims, BudgetOverrun, Lease
from aether.domain.events import BudgetOverrunEmitted
from aether.domain.ids import LeaseId, RunId
from aether.kernel.bus import EventBus
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

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus
        self._lock = asyncio.Lock()
        self._leases: dict[LeaseId, Lease] = {}
        self._parent_remaining: dict[LeaseId, BudgetDims] = {}
        self._run_root_remaining: dict[RunId, BudgetDims] = {}
        #: Which dimensions a run's ceiling actually names. See seed_run_budget.
        self._run_constrained: dict[RunId, set[str]] = {}
        self._spent: dict[RunId, BudgetDims] = {}
        self._overruns: list[BudgetOverrun] = []
        self._next_id = 0

    def seed_run_budget(self, run_id: RunId, dims: BudgetDims) -> None:
        """Configure a hard ceiling for a run's top-level (non-child) reservations.

        **A ceiling constrains only the dimensions it names.** A dimension left
        at zero is unconstrained, not "zero allowed": seeding a $0.20 cap and
        nothing else must not deny a node that asked for wall-clock. The tier-2
        run of the Sprint 3.5 ladder was refused at its first node for exactly
        that reason, before spending anything, which is the right failure mode
        to have found in a rehearsal and the wrong one to ship.

        The cost of that reading: a genuine hard zero in one dimension is not
        expressible here. Nothing needs one today, and `reserve()` with an
        explicit parent lease still enforces every dimension exactly.
        """
        self._run_root_remaining[run_id] = dims
        self._run_constrained[run_id] = {name for name, value in dims.model_dump().items() if value > 0}

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
                if available is not None:
                    constrained = self._run_constrained.get(run_id, set())
                    over = [name for name in constrained if getattr(dims, name) > getattr(available, name)]
                    if over:
                        return ReservationDenied(
                            shortfall=_sub(dims, available),
                            rationale=f"run budget exhausted ({', '.join(sorted(over))})",
                        )
                    # Only the constrained dimensions are drawn down; the rest
                    # are not being tracked and must not go negative.
                    self._run_root_remaining[run_id] = available.model_copy(
                        update={name: getattr(available, name) - getattr(dims, name) for name in constrained}
                    )

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
        overrun: BudgetOverrun | None = None
        async with self._lock:
            lease = self._leases.pop(lease_id, None)
            if lease is None:
                return

            overran = _exceeds(actuals.dims, lease.reserved)
            if overran:
                overrun = BudgetOverrun(
                    lease_id=lease_id, run_id=lease.run_id, reserved=lease.reserved, actual=actuals.dims
                )
                self._overruns.append(overrun)

            prior = self._spent.get(lease.run_id, BudgetDims())
            self._spent[lease.run_id] = _add(prior, actuals.dims)

            # `reserved - actual`, **including when that is negative**. This is
            # the line that makes the ceiling real, and until 2026-08-07 it read
            # `BudgetDims() if overran else ...`, which clamped an overrun's
            # refund to zero and therefore never debited the excess from the
            # pool. Combined with every call site estimating `usd_micros=0`,
            # `_run_root_remaining[run].usd_micros` stayed at exactly the seeded
            # value for the whole run no matter what was spent — a dollar cap
            # that could not fire, which is the same defect class as a contract
            # that selects no files. `BudgetOverrun`'s own docstring already
            # said "reality is debited regardless"; the ledger now agrees with it.
            #
            # A negative remainder is the intended terminal state, not a bug: it
            # is what makes the *next* reserve() fail closed. Reserving the
            # priced estimate up front (`TASK-044`) is what moves the denial from
            # the next call to this one; it is a separate, additive change.
            refund = _sub(lease.reserved, actuals.dims)
            self._refund(lease, refund)

        # Emitted outside the lock: the bus is another component, and awaiting
        # one while holding the ledger's lock is how a deadlock gets designed in.
        if overrun is not None and self._bus is not None:
            await self._bus.emit(
                BudgetOverrunEmitted(run_id=overrun.run_id, at=datetime.now(UTC), overrun=overrun)
            )

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
            return

        prior = self._run_root_remaining.get(lease.run_id)
        if prior is None:
            return
        constrained = self._run_constrained.get(lease.run_id, set())
        self._run_root_remaining[lease.run_id] = prior.model_copy(
            update={name: getattr(prior, name) + getattr(amount, name) for name in constrained}
        )

    async def spent(self, run_id: RunId) -> BudgetDims:
        async with self._lock:
            return self._spent.get(run_id, BudgetDims())

    async def remaining(self, run_id: RunId) -> BudgetDims | None:
        """Unallocated remainder of the seeded ceiling, or `None` when this run
        has no ceiling. `None` is not zero: an unbounded run has no remainder,
        and returning zeros would read as "exhausted" to every caller."""
        async with self._lock:
            return self._run_root_remaining.get(run_id)

    def overruns(self) -> tuple[BudgetOverrun, ...]:
        """Not part of the `ResourceGovernor` protocol — read by the composition
        root / event bus wiring (Step 10/11) to surface `BudgetOverrun` events."""
        return tuple(self._overruns)
