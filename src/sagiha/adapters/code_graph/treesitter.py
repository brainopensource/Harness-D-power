"""Tree-sitter-backed CodeGraph adapter — AST parsing, edge extraction, SQLite storage.

See ports/code_graph.py and docs/08-decisions/0011-split-code-and-episodic-graphs.md.
The code graph is a cache rebuilt from HEAD, not a system of record.

SENIOR TODO: Incremental re-indexing on file change, co-change mining from git log,
             multi-language grammar selection, import-resolution for cross-file edges.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from anyio.to_thread import run_sync

from sagiha.domain.graph import CoChange, GraphEdge, SymbolRef

logger = logging.getLogger(__name__)


class TreeSitterCodeGraph:
    """SQLite-backed code graph with Tree-sitter AST edge extraction."""

    def __init__(self, db_path: str = ".sagiha/code_graph.db") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    src TEXT NOT NULL,
                    dst TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    PRIMARY KEY (src, dst, kind)
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
                    PRIMARY KEY (path, name, line)
                );
                """
            )
            conn.commit()

    async def upsert_edges(self, edges: list[GraphEdge]) -> None:
        def _sync() -> None:
            with sqlite3.connect(self._db_path) as conn:
                conn.executemany(
                    """
                    INSERT INTO edges (src, dst, kind, weight)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(src, dst, kind) DO UPDATE SET weight = excluded.weight
                    """,
                    [(e.src, e.dst, e.kind, e.weight) for e in edges],
                )
                conn.commit()

        await run_sync(_sync)

    async def impacted_by(self, file_path: str, hops: int = 2) -> list[str]:
        """BFS traversal of edges from file_path up to `hops` depth.

        SENIOR TODO: Proper graph traversal with cycle detection, hop-limited BFS,
                     edge-kind weighting, result deduplication.
        """

        def _sync() -> list[str]:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute("SELECT DISTINCT dst FROM edges WHERE src = ?", (file_path,))
                return [row[0] for row in cursor.fetchall()]

        return await run_sync(_sync)

    async def callers_of(self, symbol: SymbolRef) -> list[SymbolRef]:
        """Find all callers of a symbol.

        SENIOR TODO: Tree-sitter call-site resolution, cross-file symbol lookup.
        """
        return []

    async def co_changed_with(self, path: str, since: datetime) -> list[CoChange]:
        """Find files that frequently change alongside `path` in git history.

        SENIOR TODO: Git log mining, co-change frequency counting.
        """
        return []
