"""Indexer — query-shaped code search. See docs/03-contracts-and-models/hexagonal-ports.md#memory--retrieval.

Returns ranked RetrievalHit / Symbol; never raw ASTs or bulk tables.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.content import Symbol
from sagiha.domain.graph import RetrievalHit

PORT_VERSION: Final = 1
STABILITY: Final = "provisional"


class Indexer(Protocol):
    async def find_symbols(self, query: str, limit: int = 20) -> list[Symbol]: ...

    async def get_skeleton(self, path: str) -> str: ...

    async def neighbors(self, path: str, limit: int = 20) -> list[RetrievalHit]: ...
