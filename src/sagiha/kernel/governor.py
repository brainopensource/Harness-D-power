"""Default ResourceGovernor implementation — see docs/02-architecture/car-model.md#admission-control."""

from __future__ import annotations

import uuid


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

    async def acquire(self, kind: str, run_id: str) -> str:
        # Generate lease_id
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
