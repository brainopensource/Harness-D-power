"""Memory — see docs/03-contracts-and-models/hexagonal-ports.md#memory--retrieval
and docs/02-architecture/neural-symbolic-memory.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final, Protocol

from sagiha.domain.memory import MemoryRecord, Recall, RecallQuery

PORT_VERSION: Final = 1
STABILITY: Final = "provisional"


class Memory(Protocol):
    """Durable knowledge: remember / recall / invalidate with trust-provenance tagging.

    No raw vectors in the signature — ports speak domain language, not storage language.
    """

    async def remember(self, record: MemoryRecord) -> str: ...

    async def recall(self, query: RecallQuery) -> list[Recall]: ...

    async def invalidate(self, memory_id: str, at: datetime) -> None: ...
