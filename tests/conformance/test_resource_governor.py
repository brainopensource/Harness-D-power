"""ResourceGovernor conformance: mock and real ledger share the reserve/commit/
release/remaining contract (ADR-0005 rev. 2); the real ledger additionally
proves atomic overrun bookkeeping and parent-refund semantics (TASK-034)."""

from __future__ import annotations

import asyncio

import pytest
from tests.aether.mocks import InMemoryResourceGovernor

from aether.domain.budget import Actuals, BudgetDims
from aether.domain.ids import RunId
from aether.kernel.governor import ResourceGovernor
from aether.ports.resource_governor import ReservationDenied, ResourceGovernor as ResourceGovernorProtocol


@pytest.mark.parametrize("governor", [InMemoryResourceGovernor(), ResourceGovernor()])
def test_governor_satisfies_protocol(governor: object) -> None:
    assert isinstance(governor, ResourceGovernorProtocol)


@pytest.mark.parametrize("governor_factory", [InMemoryResourceGovernor, ResourceGovernor])
async def test_reserve_commit_updates_remaining(governor_factory) -> None:  # noqa: ANN001
    governor = governor_factory()
    run_id = RunId("run-1")
    lease = await governor.reserve(run_id, BudgetDims(usd_micros=100))
    assert not isinstance(lease, ReservationDenied)

    await governor.commit(lease.lease_id, Actuals(dims=BudgetDims(usd_micros=40)))

    remaining = await governor.remaining(run_id)
    assert remaining.usd_micros == 40


@pytest.mark.parametrize("governor_factory", [InMemoryResourceGovernor, ResourceGovernor])
async def test_release_is_idempotent(governor_factory) -> None:  # noqa: ANN001
    governor = governor_factory()
    run_id = RunId("run-1")
    lease = await governor.reserve(run_id, BudgetDims(usd_micros=10))
    assert not isinstance(lease, ReservationDenied)

    await governor.release(lease.lease_id)
    await governor.release(lease.lease_id)  # must not raise


async def test_real_governor_overrun_debits_reality_and_is_recorded() -> None:
    governor = ResourceGovernor()
    run_id = RunId("run-1")
    lease = await governor.reserve(run_id, BudgetDims(usd_micros=10))
    assert not isinstance(lease, ReservationDenied)

    await governor.commit(lease.lease_id, Actuals(dims=BudgetDims(usd_micros=25)))

    remaining = await governor.remaining(run_id)
    assert remaining.usd_micros == 25  # reality debited exactly as spent, not clamped
    overruns = governor.overruns()
    assert len(overruns) == 1
    assert overruns[0].reserved.usd_micros == 10
    assert overruns[0].actual.usd_micros == 25


async def test_real_governor_root_reservation_denied_when_ceiling_seeded() -> None:
    governor = ResourceGovernor()
    run_id = RunId("run-1")
    governor.seed_run_budget(run_id, BudgetDims(usd_micros=50))

    denied = await governor.reserve(run_id, BudgetDims(usd_micros=100))

    assert isinstance(denied, ReservationDenied)
    assert denied.shortfall.usd_micros == 50


async def test_real_governor_child_lease_release_refunds_parent_not_global_pool() -> None:
    governor = ResourceGovernor()
    run_id = RunId("run-1")
    parent = await governor.reserve(run_id, BudgetDims(usd_micros=100))
    assert not isinstance(parent, ReservationDenied)

    child_a = await governor.reserve(run_id, BudgetDims(usd_micros=60), parent=parent.lease_id)
    assert not isinstance(child_a, ReservationDenied)

    # Parent has 40 left; a second 60-cost child must be denied until the first releases.
    child_b_denied = await governor.reserve(run_id, BudgetDims(usd_micros=60), parent=parent.lease_id)
    assert isinstance(child_b_denied, ReservationDenied)

    await governor.release(child_a.lease_id)  # refunds into the parent, not a global pool

    child_b = await governor.reserve(run_id, BudgetDims(usd_micros=60), parent=parent.lease_id)
    assert not isinstance(child_b, ReservationDenied)


async def test_real_governor_concurrent_reserves_are_atomic() -> None:
    governor = ResourceGovernor()
    run_id = RunId("run-1")
    governor.seed_run_budget(run_id, BudgetDims(usd_micros=100))

    results = await asyncio.gather(
        *(governor.reserve(run_id, BudgetDims(usd_micros=10)) for _ in range(20))
    )

    granted = [r for r in results if not isinstance(r, ReservationDenied)]
    denied = [r for r in results if isinstance(r, ReservationDenied)]
    assert len(granted) == 10  # exactly 100/10, never over-granted under concurrency
    assert len(denied) == 10
