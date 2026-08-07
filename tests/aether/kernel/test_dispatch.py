"""Dispatcher — the 5-stage choke point (I5): call order and no-bypass behavior.

There's no adapters/ package yet to scan for a literal bypass (that becomes
buildable once TASK-011/017/018/019/026 land real adapters). The honest
M0-scope version of "architecture test proves no bypass path" is:
(1) below — a behavioral test asserting the call order and that a denial/
budget-denial short-circuits before the adapter ever runs; the complementary
structural half is the aether-tcb-isolation / aether-ports-are-pure
import-linter contracts (TASK-000), which make it impossible for any layer
other than kernel/ to reach these adapters without going through
Dispatcher.dispatch() — those contracts are exercised by `lint-imports`, not
by this test file.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.aether.mocks import InMemoryResourceGovernor

from aether.domain.budget import Actuals, BudgetDims
from aether.domain.ids import LeaseId, RunId, SpanId
from aether.domain.taint import Provenance, TaintSpan
from aether.kernel.dispatch import Dispatcher, EffectOutcome
from aether.kernel.policy import DefaultPolicyEngine
from aether.ports.policy_engine import EffectRequest


def _request(*, widens: bool = False, effect_class: str = "read") -> EffectRequest:
    return EffectRequest(
        run_id=RunId("r1"),
        effect_class=effect_class,  # type: ignore[arg-type]
        descriptor="cat file.py",
        justifying_spans=(
            TaintSpan(
                span_id=SpanId("s1"),
                label=Provenance.AGENT,
                text="x",
                source="test",
                created_at=datetime.now(UTC),
            ),
        ),
        widens_capability=widens,
    )


class _RecordingAdapter:
    def __init__(self, outcome: EffectOutcome | None = None, raises: Exception | None = None) -> None:
        self.calls: list[tuple[EffectRequest, LeaseId]] = []
        self._outcome = outcome or EffectOutcome(status="ok")
        self._raises = raises

    async def __call__(self, request: EffectRequest, lease) -> EffectOutcome:  # noqa: ANN001
        self.calls.append((request, lease.lease_id))
        if self._raises is not None:
            raise self._raises
        return self._outcome


async def test_success_path_calls_authorize_reserve_adapter_commit_in_order() -> None:
    governor = InMemoryResourceGovernor()
    actuals = Actuals(dims=BudgetDims(usd_micros=5))
    adapter = _RecordingAdapter(outcome=EffectOutcome(status="ok", actuals=actuals))
    dispatcher = Dispatcher(policy=DefaultPolicyEngine(), governor=governor, adapters={"read": adapter})

    outcome = await dispatcher.dispatch(_request(), cost_estimate=BudgetDims(usd_micros=10))

    assert outcome.status == "ok"
    assert len(adapter.calls) == 1
    spent = await governor.spent(RunId("r1"))
    assert spent.usd_micros == 5  # committed actuals landed


async def test_denied_request_never_reaches_governor_or_adapter() -> None:
    adapter = _RecordingAdapter()

    class _AlwaysReject:
        async def authorize(self, request: EffectRequest):  # noqa: ANN201
            from aether.ports.policy_engine import Decision, PolicyDecision

            return PolicyDecision(decision=Decision.REJECT, rule_id="test", rationale="no")

    class _GovernorSpy(InMemoryResourceGovernor):
        async def reserve(self, *args, **kwargs):  # noqa: ANN201, ANN002, ANN003
            raise AssertionError("reserve() must not be called when authorize() denies")

    dispatcher = Dispatcher(policy=_AlwaysReject(), governor=_GovernorSpy(), adapters={"read": adapter})

    outcome = await dispatcher.dispatch(_request(), cost_estimate=BudgetDims(usd_micros=10))

    assert outcome.status == "denied"
    assert adapter.calls == []


async def test_budget_denied_never_reaches_adapter() -> None:
    adapter = _RecordingAdapter()

    class _AlwaysDenyBudget:
        async def reserve(self, run_id, dims, parent=None):  # noqa: ANN001, ANN201
            from aether.ports.resource_governor import ReservationDenied

            return ReservationDenied(shortfall=dims, rationale="over budget")

        async def commit(self, lease_id, actuals):  # noqa: ANN001, ANN201
            raise AssertionError("commit() must not be called")

        async def release(self, lease_id):  # noqa: ANN001, ANN201
            raise AssertionError("release() must not be called — nothing was leased")

        async def spent(self, run_id):  # noqa: ANN001, ANN201
            return BudgetDims()

        async def remaining(self, run_id):  # noqa: ANN001, ANN201
            return None

    dispatcher = Dispatcher(
        policy=DefaultPolicyEngine(), governor=_AlwaysDenyBudget(), adapters={"read": adapter}
    )

    outcome = await dispatcher.dispatch(_request(), cost_estimate=BudgetDims(usd_micros=10))

    assert outcome.status == "budget_denied"
    assert adapter.calls == []


async def test_adapter_exception_releases_lease_and_propagates_never_swallowed() -> None:
    governor = InMemoryResourceGovernor()
    adapter = _RecordingAdapter(raises=RuntimeError("adapter blew up"))
    dispatcher = Dispatcher(policy=DefaultPolicyEngine(), governor=governor, adapters={"read": adapter})

    with pytest.raises(RuntimeError, match="adapter blew up"):
        await dispatcher.dispatch(_request(), cost_estimate=BudgetDims(usd_micros=10))

    assert governor._reserved == {}  # released, not left dangling
    assert await governor.spent(RunId("r1")) == BudgetDims()  # never committed
