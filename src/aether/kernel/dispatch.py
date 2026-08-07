"""Dispatcher — THE single choke point (I5).

authorize -> verify grant -> acquire lease -> dispatch -> release.

M0-reduced scope: the skeleton in core_skeletons_and_protocols.md §5 bundles
concerns from out-of-scope tasks into this same class — a `bus: EventBus`
constructor argument (TASK-022, event-bus emission) and a deny-ledger with a
"3/20 bound" (ADR-0008, TASK-030a). Both are deliberately omitted here, the
same kind of reversible M0 scope cut ADR-0013 applies to WorkflowStep ("no
executor"). This class implements exactly the 5-stage choke point I5 names.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Literal

from aether.domain.budget import Actuals, BudgetDims, Lease
from aether.domain.ids import Frozen
from aether.ports.policy_engine import Decision, EffectRequest, PolicyDecision, PolicyEngine
from aether.ports.resource_governor import ReservationDenied, ResourceGovernor


class EffectOutcome(Frozen):
    status: Literal["ok", "denied", "budget_denied"]
    decision: PolicyDecision | None = None
    reservation_denied: ReservationDenied | None = None
    actuals: Actuals = Actuals(dims=BudgetDims())


AdapterFn = Callable[[EffectRequest, Lease], Awaitable[EffectOutcome]]
# Keyed by EffectRequest.effect_class. Real entries land as TASK-011/017/018/
# 019/026's adapters register into composition.py (out of scope); tests
# populate this directly with mock adapter functions.
AdapterTable = Mapping[str, AdapterFn]


class Dispatcher:
    def __init__(self, policy: PolicyEngine, governor: ResourceGovernor, adapters: AdapterTable) -> None:
        self._policy = policy
        self._governor = governor
        self._adapters = adapters

    def _verify(self, decision: PolicyDecision, request: EffectRequest) -> None:
        """Re-check the request passed to dispatch() still matches the grant issued
        moments ago, immediately before the effect (I5) — not merged into
        authorize(). Currently a precondition, not a real check: this M0
        dispatcher does not persist a Grant with its own expiry/binding, so
        within one dispatch() call there is no time gap in which `request`
        could go stale. The seam stays a distinct, named step so a future
        two-phase authorize-ahead-of-time flow (a persisted grant, verified
        against a possibly-different request at redemption time) doesn't
        require a different dispatch() shape."""
        assert decision.decision is Decision.GRANT, "verify() called without a live grant"

    async def dispatch(self, request: EffectRequest, cost_estimate: BudgetDims) -> EffectOutcome:
        decision = await self._policy.authorize(request)  # 1 authorize
        if decision.decision is not Decision.GRANT:
            return EffectOutcome(status="denied", decision=decision)

        self._verify(decision, request)  # 2 verify @ effect-time

        lease = await self._governor.reserve(request.run_id, cost_estimate)  # 3 lease
        if isinstance(lease, ReservationDenied):
            return EffectOutcome(status="budget_denied", reservation_denied=lease)

        adapter = self._adapters[request.effect_class]  # 4 dispatch
        try:
            outcome = await adapter(request, lease)
            await self._governor.commit(lease.lease_id, outcome.actuals)
            return outcome
        except Exception:
            await self._governor.release(lease.lease_id)  # 5 release
            raise  # stubs raise; never swallowed to a plausible-looking value
