"""Default ResourceGovernor implementation — see docs/02-architecture/car-model.md#admission-control."""

from __future__ import annotations

import time
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
        max_wall_clock_s: int = 7200,
        max_steps_per_run: int = 200,
    ) -> None:
        self._max_spend_usd_per_run = max_spend_usd_per_run
        self._max_concurrent_sandboxes = max_concurrent_sandboxes
        self._max_wall_clock_s = max_wall_clock_s
        self._max_steps_per_run = max_steps_per_run
        self._spend_per_run: dict[str, float] = {}
        self._active_leases: dict[str, tuple[str, str]] = {}  # lease_id -> (kind, run_id)
        #: Monotonic start stamp per run, set on the first `acquire`/`record_spend`/
        #: `start_run` seen for that run. Wall clock is measured from first activity
        #: rather than from process start, because one process may serve many runs.
        self._run_started: dict[str, float] = {}

    # --- Wall clock (RC-2) ---------------------------------------------------
    #
    # `max_wall_clock_s` and `max_steps_per_run` were accepted by `GovernorConfig`
    # and read by nothing. A limit nothing reads is not a limit; these three
    # concrete-class helpers are what make them enforceable. They are deliberately
    # NOT on the `ResourceGovernor` Protocol — adding them would be a port bump for
    # what is admission-control bookkeeping, and `RunLoop` holds the concrete
    # governor via composition.

    def start_run(self, run_id: str) -> None:
        """Stamp the wall-clock origin for `run_id` if it has not been stamped yet."""
        self._run_started.setdefault(run_id, time.monotonic())

    def elapsed_s(self, run_id: str) -> float:
        started = self._run_started.get(run_id)
        return 0.0 if started is None else time.monotonic() - started

    def remaining_wall_clock_s(self, run_id: str) -> float:
        """Seconds left before `max_wall_clock_s`. `<= 0` means the run must stop."""
        if self._max_wall_clock_s <= 0:
            return float("inf")
        return self._max_wall_clock_s - self.elapsed_s(run_id)

    @property
    def max_steps_per_run(self) -> int:
        return self._max_steps_per_run

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
        self.start_run(run_id)
        limit = self._limit_for(kind)

        # Wall clock is scoped to POOLED resources for the same reason the budget
        # check below is: refusing the gate evaluator's own `git diff` on an
        # overrunning run would destroy the record of what the run did.
        if limit is not None and self.remaining_wall_clock_s(run_id) <= 0:
            raise ConcurrencyLimitError(
                f"run {run_id} exceeded its {self._max_wall_clock_s}s wall-clock limit"
            )

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
        self.start_run(run_id)
        current = self._spend_per_run.get(run_id, 0.0)
        self._spend_per_run[run_id] = current + usd

    async def remaining_budget(self, run_id: str) -> float:
        spent = self._spend_per_run.get(run_id, 0.0)
        return max(0.0, self._max_spend_usd_per_run - spent)
