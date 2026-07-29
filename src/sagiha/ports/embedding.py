"""EmbeddingProvider — text to vectors, swappable independently of the store.

Marked Experimental per docs/03-contracts-and-models/port-stability-and-versioning.md and
docs/08-decisions/0014-defer-dense-retrieval.md: the port exists so a future dense-retrieval
backend fuses without a shape change, but ships with **no adapter** in v0.1. v1 retrieval is
lexical (BM25/FTS5) + graph expansion only.
"""

from __future__ import annotations

from typing import Final, Protocol

PORT_VERSION: Final = 1
STABILITY: Final = "experimental"


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
