"""ResourceGovernor — global admission control: concurrency, spend, rate limits, pool sizes.

See docs/02-architecture/car-model.md#admission-control.

Deliberately exposes `acquire`/`release` rather than an async-context-manager `lease()`: a live
context-manager object cannot cross a port boundary (see docs/02-architecture/remoteable-ports.md
— locks/queues/connections are process-local by definition). `kernel/dispatch.py` wraps these two
calls in an `async with`-friendly helper for ergonomics; that helper is kernel-internal, not part
of this port.
"""

from __future__ import annotations

from typing import Final, Protocol

PORT_VERSION: Final = 1
STABILITY: Final = "provisional"


class ResourceGovernor(Protocol):
    async def acquire(self, kind: str, run_id: str) -> str: ...  # returns a lease_id

    async def release(self, lease_id: str) -> None: ...

    async def record_spend(self, run_id: str, usd: float) -> None: ...

    async def remaining_budget(self, run_id: str) -> float: ...
