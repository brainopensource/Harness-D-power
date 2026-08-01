"""Shared indexing walk — one parse feeds FTS5 chunks and code-graph edges."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from anyio.to_thread import run_sync

from sagiha.adapters.code_graph.treesitter import TreeSitterCodeGraph
from sagiha.adapters.indexer.chunking import analyze_python_source
from sagiha.adapters.indexer.frontmatter import is_retrieval_excluded
from sagiha.adapters.indexer.fts5 import FTS5Indexer

logger = logging.getLogger(__name__)

_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", ".sagiha"})
_TEXT_EXTENSIONS = frozenset({".md", ".mdx"})


class IndexService:
    """Coordinate a single workspace walk across the FTS5 indexer and code graph."""

    def __init__(
        self,
        root: Path,
        indexer: FTS5Indexer,
        graph: TreeSitterCodeGraph,
        *,
        max_chunk_tokens: int = 1024,
    ) -> None:
        self._root = root
        self._indexer = indexer
        self._graph = graph
        self._max_chunk_tokens = max_chunk_tokens

    def _should_skip(self, file_path: Path) -> bool:
        return any(part in _SKIP_DIRS for part in file_path.parts)

    def _reindex_python(self, rel: str, source: str) -> None:
        source_bytes = source.encode("utf-8")
        chunks, symbols = analyze_python_source(rel, source_bytes, max_chunk_tokens=self._max_chunk_tokens)
        edges = self._graph.index_file(rel, source_bytes)

        with sqlite3.connect(self._indexer._db_path) as conn:
            conn.execute("DELETE FROM chunks WHERE path = ?", (rel,))
            conn.execute("DELETE FROM symbols WHERE path = ?", (rel,))
            for chunk in chunks:
                conn.execute(
                    "INSERT INTO chunks(path, chunk) VALUES (?, ?)",
                    (rel, chunk.text),
                )
            for sym_path, name, kind, line, signature in symbols:
                conn.execute(
                    ("INSERT INTO symbols(path, name, kind, line, signature) VALUES (?, ?, ?, ?, ?)"),
                    (sym_path, name, kind, line, signature),
                )
            conn.commit()

        self._graph.replace_file_edges(rel, edges)

    def _strip_frontmatter(self, text: str) -> str:
        if not text.startswith("---"):
            return text
        end = text.find("\n---", 3)
        if end == -1:
            return text
        return text[end + 4 :].lstrip("\n")

    def _reindex_markdown(self, rel: str, source: str) -> None:
        with sqlite3.connect(self._indexer._db_path) as conn:
            conn.execute("DELETE FROM chunks WHERE path = ?", (rel,))
            conn.execute("DELETE FROM symbols WHERE path = ?", (rel,))
            if not is_retrieval_excluded(source):
                body = self._strip_frontmatter(source)
                conn.execute(
                    "INSERT INTO chunks(path, chunk) VALUES (?, ?)",
                    (rel, body),
                )
            conn.commit()

    def _reindex_path(self, rel: str) -> None:
        file_path = self._root / rel
        if not file_path.is_file():
            return
        source = file_path.read_text(encoding="utf-8")
        if rel.endswith(".py"):
            self._reindex_python(rel, source)
        elif rel.endswith(_TEXT_EXTENSIONS):
            self._reindex_markdown(rel, source)

    def _reindex_all(self) -> None:
        for file_path in sorted(self._root.rglob("*")):
            if not file_path.is_file() or self._should_skip(file_path):
                continue
            rel = file_path.relative_to(self._root).as_posix()
            if rel.endswith(".py") or rel.endswith(_TEXT_EXTENSIONS):
                self._reindex_path(rel)

    async def reindex(self, paths: list[str] | None = None) -> None:
        """Reindex the workspace or an explicit path list."""

        def _sync() -> None:
            if paths is None:
                self._reindex_all()
                return
            for rel in paths:
                self._reindex_path(rel)

        await run_sync(_sync)
