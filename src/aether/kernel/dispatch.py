"""Dispatcher — THE single choke point (I5).

authorize -> verify grant -> acquire lease -> dispatch -> release.

Sprint 3.5 added the `bus` this class was always specified to take. Without
it `EffectDispatched` was a catalog entry with no producer: the event existed
in `domain/events.py`, appeared in the generated catalog, and no client could
ever receive one. A deny-ledger with a "3/20 bound" (ADR-0008, TASK-030a) is
still deliberately out of scope.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from typing import Literal

from aether.domain.budget import Actuals, BudgetDims, Lease
from aether.domain.events import EffectDispatched
from aether.domain.ids import Frozen
from aether.kernel.bus import EventBus
from aether.ports.policy_engine import Decision, EffectRequest, PolicyDecision, PolicyEngine
from aether.ports.resource_governor import ReservationDenied, ResourceGovernor


class EffectOutcome(Frozen):
    status: Literal["ok", "denied", "budget_denied"]
    decision: PolicyDecision | None = None
    reservation_denied: ReservationDenied | None = None
    actuals: Actuals = Actuals(dims=BudgetDims())
    # The adapter's real result, JSON-encoded (Frozen models are JSON round-trippable
    # by construction, I2/I3 — no live object crosses this boundary). Populated by
    # composition.py's adapter closures (Sprint 2); callers deserialize the type
    # they know their effect_class returns (e.g. FileSlice for "read").
    result_json: str | None = None


AdapterFn = Callable[[EffectRequest, Lease], Awaitable[EffectOutcome]]
# Keyed by EffectRequest.effect_class. Real entries land as TASK-011/017/018/
# 019/026's adapters register into composition.py (out of scope); tests
# populate this directly with mock adapter functions.
AdapterTable = Mapping[str, AdapterFn]


class Dispatcher:
    def __init__(
        self,
        policy: PolicyEngine,
        governor: ResourceGovernor,
        adapters: AdapterTable,
        bus: EventBus | None = None,
    ) -> None:
        self._policy = policy
        self._governor = governor
        self._adapters = adapters
        self._bus = bus

    async def _emit(self, request: EffectRequest, status: str) -> None:
        """Observation only — an event never schedules anything (spec.md §8)."""
        if self._bus is None:
            return
        await self._bus.emit(
            EffectDispatched(
                run_id=request.run_id,
                at=datetime.now(UTC),
                effect_class=request.effect_class,
                status=status,  # type: ignore[arg-type]
            )
        )

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
            await self._emit(request, "denied")
            return EffectOutcome(status="denied", decision=decision)

        self._verify(decision, request)  # 2 verify @ effect-time

        lease = await self._governor.reserve(request.run_id, cost_estimate)  # 3 lease
        if isinstance(lease, ReservationDenied):
            await self._emit(request, "budget_denied")
            return EffectOutcome(status="budget_denied", reservation_denied=lease)

        adapter = self._adapters[request.effect_class]  # 4 dispatch
        try:
            outcome = await adapter(request, lease)
            await self._governor.commit(lease.lease_id, outcome.actuals)
            await self._emit(request, outcome.status)
            return outcome
        except Exception:
            await self._governor.release(lease.lease_id)  # 5 release
            raise  # stubs raise; never swallowed to a plausible-looking value
