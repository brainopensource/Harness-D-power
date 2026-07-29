"""CodeGraph — deterministic code structure from Tree-sitter and git.

See docs/03-contracts-and-models/hexagonal-ports.md#memory--retrieval and
docs/08-decisions/0011-split-code-and-episodic-graphs.md: built directly by the indexer, exact,
fully rebuildable from HEAD — a cache, not a system of record.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final, Protocol

from sagiha.domain.graph import CoChange, GraphEdge, SymbolRef

PORT_VERSION: Final = 1
STABILITY: Final = "provisional"


class CodeGraph(Protocol):
    async def upsert_edges(self, edges: list[GraphEdge]) -> None: ...

    async def impacted_by(self, file_path: str, hops: int = 2) -> list[str]: ...

    async def callers_of(self, symbol: SymbolRef) -> list[SymbolRef]: ...

    async def co_changed_with(self, path: str, since: datetime) -> list[CoChange]: ...
