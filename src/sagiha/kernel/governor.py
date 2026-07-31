"""Default ResourceGovernor implementation — see docs/02-architecture/car-model.md#admission-control."""

from __future__ import annotations

import uuid


class ConcurrencyLimitError(RuntimeError):
    """Admission refused: a pool is exhausted, or the run is out of budget.

    Raised rather than returned so a caller cannot mistake refusal for a lease. The
    previous implementation had no refusal path at all — it always minted one (H2b).
    """


class DefaultResourceGovernor:
    """In-memory ResourceGovernor for admission control, spend limits, and leases."""

    def __init__(
        self,
        max_spend_usd_per_run: float = 5.0,
        max_concurrent_sandboxes: int = 4,
    ) -> None:
        self._max_spend_usd_per_run = max_spend_usd_per_run
        self._max_concurrent_sandboxes = max_concurrent_sandboxes
        self._spend_per_run: dict[str, float] = {}
        self._active_leases: dict[str, tuple[str, str]] = {}  # lease_id -> (kind, run_id)

    #: Pools with a configured ceiling. A `kind` absent from this map is unlimited,
    #: which is deliberate: inventing a default ceiling for an unknown resource would
    #: throttle callers on a number nobody chose.
    def _limit_for(self, kind: str) -> int | None:
        return {"sandbox": self._max_concurrent_sandboxes}.get(kind)

    async def acquire(self, kind: str, run_id: str) -> str:
        """Mint a lease, or refuse.

        Both constructor arguments were stored and never read before PR-1b: `acquire`
        minted a lease unconditionally, so neither the concurrency ceiling nor the spend
        limit constrained anything (H2b).
        """
        limit = self._limit_for(kind)

        # Budget refusal is scoped to POOLED resources, not to every dispatch.
        # Every local tool call — including the gate evaluator's own `git diff` and the
        # acceptance checks — goes through `acquire`. Refusing those on an exhausted
        # budget would mean a run that overspends cannot be graded, destroying the
        # record of what it did. The loop already stops on budget; this stops the
        # expensive resources from being handed out on top of that.
        if limit is not None and self._max_spend_usd_per_run > 0:
            if await self.remaining_budget(run_id) <= 0:
                raise ConcurrencyLimitError(
                    f"run {run_id} has exhausted its ${self._max_spend_usd_per_run:.2f} budget"
                )

        if limit is not None:
            # A live count of outstanding leases, not a high-water mark — `release`
            # frees the slot.
            in_use = sum(1 for lease_kind, _ in self._active_leases.values() if lease_kind == kind)
            if in_use >= limit:
                raise ConcurrencyLimitError(f"{kind} pool exhausted: {in_use}/{limit} leases outstanding")

        lease_id = str(uuid.uuid4())
        self._active_leases[lease_id] = (kind, run_id)
        return lease_id

    async def release(self, lease_id: str) -> None:
        self._active_leases.pop(lease_id, None)

    async def record_spend(self, run_id: str, usd: float) -> None:
        current = self._spend_per_run.get(run_id, 0.0)
        self._spend_per_run[run_id] = current + usd

    async def remaining_budget(self, run_id: str) -> float:
        spent = self._spend_per_run.get(run_id, 0.0)
        return max(0.0, self._max_spend_usd_per_run - spent)
