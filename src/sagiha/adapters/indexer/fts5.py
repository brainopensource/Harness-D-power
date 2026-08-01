"""SQLite FTS5 indexer — full-text search over AST-bounded code chunks.

See ports/indexer.py and docs/08-decisions/0014-defer-dense-retrieval.md.
v1 retrieval is lexical + graph; dense tier deferred until recall@10 misses.

SENIOR TODO: AST-bounded chunking (tree-sitter node boundaries), incremental re-indexing,
             BM25 parameter tuning, graph expansion integration.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from anyio.to_thread import run_sync

from sagiha.domain.content import Symbol
from sagiha.domain.graph import RetrievalHit, SymbolRef

logger = logging.getLogger(__name__)


class FTS5Indexer:
    """SQLite FTS5-backed code indexer with AST-bounded chunking."""

    def __init__(self, db_path: str = ".sagiha/index.db") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                    path, chunk, content='', content_rowid='rowid'
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS symbols (
                    path TEXT NOT NULL,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    signature TEXT DEFAULT ''
                );
                """
            )
            conn.commit()

    async def find_symbols(self, query: str, limit: int = 20) -> list[Symbol]:
        """Search symbols by name substring.

        SENIOR TODO: Fuzzy matching, kind-aware ranking, scope-aware filtering.
        """

        def _sync() -> list[Symbol]:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "SELECT path, name FROM symbols WHERE name LIKE ? LIMIT ?",
                    (f"%{query}%", limit),
                )
                return [
                    Symbol(
                        ref=SymbolRef(path=row[0], name=row[1], kind="function", line=1),
                        signature=f"def {row[1]}()",
                    )
                    for row in cursor.fetchall()
                ]

        return await run_sync(_sync)

    async def get_skeleton(self, path: str) -> str:
        """Return the structural skeleton of a file (class/function signatures).

        SENIOR TODO: Tree-sitter-based skeleton extraction (strip bodies, keep signatures).
        """
        return ""

    async def neighbors(self, path: str, limit: int = 20) -> list[RetrievalHit]:
        """Find chunks related to a file path.

        SENIOR TODO: FTS5 query construction, graph-expansion integration,
                     BM25 scoring normalization.
        """
        return []
