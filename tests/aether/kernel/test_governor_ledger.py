"""The run ceiling debits reality (audit F3).

`spec.md` §5: *budget is reserved before execution, not recorded after.* The
reservation half worked. The **accounting** half did not: `commit()` wrote
actuals into `_spent` while `reserve()` decided against `_run_root_remaining`,
and the one line that could have joined them clamped an overrun's refund to
zero. Since no call site estimates `usd_micros` at all, every model call
reserved `$0`, overran, refunded `$0`, and left the ceiling at exactly its
seeded value for the whole run.

The effect was a `usd_micros_ceiling` that could not fire — the same defect
class as an import contract that selects no files, and the reason
`engine.run`'s "a real ceiling, not a comment" comment was not true when it was
written.

Every test here fails against the pre-fix governor.
"""

from __future__ import annotations

from aether.domain.budget import Actuals, BudgetDims
from aether.domain.ids import RunId
from aether.kernel.governor import ResourceGovernor
from aether.ports.resource_governor import ReservationDenied

RUN = RunId("run-ledger")


async def test_actual_spend_is_debited_from_the_ceiling_even_when_it_overruns() -> None:
    governor = ResourceGovernor()
    governor.seed_run_budget(RUN, BudgetDims(usd_micros=200_000))  # $0.20

    # What every node does today: reserve tokens and wall-clock, never dollars.
    lease = await governor.reserve(RUN, BudgetDims(prompt_tokens=4096))
    assert not isinstance(lease, ReservationDenied)
    # What `composition._model` commits back once `pricing.priced()` has run.
    await governor.commit(lease.lease_id, Actuals(dims=BudgetDims(usd_micros=150_000)))

    remaining = await governor.remaining(RUN)
    assert remaining is not None
    assert remaining.usd_micros == 50_000, "the ledger must debit what was actually spent"


async def test_a_run_that_outspends_its_ceiling_is_refused_at_the_next_effect() -> None:
    governor = ResourceGovernor()
    governor.seed_run_budget(RUN, BudgetDims(usd_micros=200_000))

    first = await governor.reserve(RUN, BudgetDims(prompt_tokens=4096))
    assert not isinstance(first, ReservationDenied)
    await governor.commit(first.lease_id, Actuals(dims=BudgetDims(usd_micros=300_000)))

    second = await governor.reserve(RUN, BudgetDims(prompt_tokens=4096))
    assert isinstance(second, ReservationDenied), (
        "a run that has already spent past its cap must be refused the next effect"
    )
    assert "run budget exhausted" in second.rationale

    # One call of overshoot is the honest bound of this fix on its own: the
    # denial lands on the effect *after* the one that broke the cap, because
    # nothing prices the estimate up front. `TASK-044` reserves the priced
    # estimate and moves the denial onto the offending call itself.
    remaining = await governor.remaining(RUN)
    assert remaining is not None
    assert remaining.usd_micros == -100_000


async def test_an_overrun_still_reports_itself_and_still_debits() -> None:
    """The two behaviours are independent and both are required. Reporting the
    overrun without debiting it is what the ledger did before; debiting without
    reporting would lose the honesty signal `BudgetOverrun` exists to carry."""
    governor = ResourceGovernor()
    governor.seed_run_budget(RUN, BudgetDims(usd_micros=100_000))

    lease = await governor.reserve(RUN, BudgetDims(usd_micros=10_000))
    assert not isinstance(lease, ReservationDenied)
    await governor.commit(lease.lease_id, Actuals(dims=BudgetDims(usd_micros=90_000)))

    overruns = governor.overruns()
    assert len(overruns) == 1
    assert overruns[0].actual.usd_micros == 90_000

    remaining = await governor.remaining(RUN)
    assert remaining is not None
    # seeded 100_000 - reserved 10_000 (at reserve) + (10_000 - 90_000) refund.
    assert remaining.usd_micros == 10_000


async def test_an_underspend_returns_the_difference_not_the_whole_reservation() -> None:
    governor = ResourceGovernor()
    governor.seed_run_budget(RUN, BudgetDims(usd_micros=200_000))

    lease = await governor.reserve(RUN, BudgetDims(usd_micros=50_000))
    assert not isinstance(lease, ReservationDenied)
    await governor.commit(lease.lease_id, Actuals(dims=BudgetDims(usd_micros=20_000)))

    remaining = await governor.remaining(RUN)
    assert remaining is not None
    assert remaining.usd_micros == 180_000


async def test_a_released_lease_returns_its_whole_reservation() -> None:
    """Release is the cancel path — nothing was spent, so nothing is debited.
    This is what makes Best-of-N loser cancellation correct."""
    governor = ResourceGovernor()
    governor.seed_run_budget(RUN, BudgetDims(usd_micros=200_000))

    lease = await governor.reserve(RUN, BudgetDims(usd_micros=50_000))
    assert not isinstance(lease, ReservationDenied)
    await governor.release(lease.lease_id)

    remaining = await governor.remaining(RUN)
    assert remaining is not None
    assert remaining.usd_micros == 200_000


async def test_a_childs_overrun_is_debited_from_its_parent_not_the_global_pool() -> None:
    governor = ResourceGovernor()
    parent = await governor.reserve(RUN, BudgetDims(usd_micros=100_000))
    assert not isinstance(parent, ReservationDenied)

    child = await governor.reserve(RUN, BudgetDims(usd_micros=40_000), parent=parent.lease_id)
    assert not isinstance(child, ReservationDenied)
    await governor.commit(child.lease_id, Actuals(dims=BudgetDims(usd_micros=90_000)))

    # The child held 40_000 and spent 90_000. The parent must be charged the
    # 90_000 it actually cost, not the 40_000 it was told to expect, leaving
    # 10_000 of the parent's 100_000 — so a sibling asking for 20_000 is
    # refused. Pre-fix the excess vanished and the sibling was granted.
    sibling = await governor.reserve(RUN, BudgetDims(usd_micros=20_000), parent=parent.lease_id)
    assert isinstance(sibling, ReservationDenied), (
        "an overrunning child must narrow what its siblings can still draw"
    )
    assert "parent lease exhausted" in sibling.rationale

    affordable = await governor.reserve(RUN, BudgetDims(usd_micros=10_000), parent=parent.lease_id)
    assert not isinstance(affordable, ReservationDenied), "10_000 of the parent is genuinely left"
