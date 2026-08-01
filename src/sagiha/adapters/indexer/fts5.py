"""SQLite FTS5 indexer — full-text search over AST-bounded code chunks.

See ports/indexer.py and docs/08-decisions/0014-defer-dense-retrieval.md.
v1 retrieval is lexical + graph; dense tier deferred until recall@10 misses.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from anyio.to_thread import run_sync

from sagiha.adapters.indexer.chunking import Chunk, analyze_python_source
from sagiha.adapters.indexer.frontmatter import is_retrieval_excluded
from sagiha.domain.content import Symbol
from sagiha.domain.graph import RetrievalHit, SymbolRef

logger = logging.getLogger(__name__)

_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", ".sagiha"})
_TEXT_EXTENSIONS = frozenset({".md", ".mdx"})

_FTS_OPERATORS: Final = frozenset({"AND", "OR", "NOT", "NEAR"})


def _fts_query(text: str) -> str:
    """Convert free text into a safe FTS5 MATCH expression.

    FTS5 parses its argument as *query syntax*, not as literal text, so raw goal
    text containing `(`, `)`, `'`, `-` or `:` is a syntax error rather than a
    search (defect C-1). Tokenize on word characters, drop 1-char noise and bare
    boolean operators, quote every surviving term, and OR them together — seed
    retrieval is recall-oriented, so a disjunction is the right default.

    Returns `""` when no usable token survives; callers must treat that as a
    true empty and must not touch the database.
    """
    tokens = [
        token
        for token in re.findall(r"\w+", text)
        if len(token) >= 2 and token.upper() not in _FTS_OPERATORS
    ]
    return " OR ".join(f'"{token}"' for token in tokens)


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
                    path, chunk
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

    def chunk_count(self) -> int:
        """Return the number of indexed chunks (sync; safe before async reindex)."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
            return int(row[0]) if row else 0

    def _clear_path(self, conn: sqlite3.Connection, path: str) -> None:
        conn.execute("DELETE FROM chunks WHERE path = ?", (path,))
        conn.execute("DELETE FROM symbols WHERE path = ?", (path,))

    # --- public write surface (m-4) ------------------------------------------
    # `IndexService` used to open `sqlite3.connect(indexer._db_path)` and issue
    # its own DELETE/INSERT against the chunks/symbols schema. That coupled a
    # coordinator to this adapter's private storage layout. These two methods
    # are the whole surface it needs; the FTS schema stays in here.

    def clear_path(self, path: str) -> None:
        """Drop every chunk and symbol row recorded for *path*."""
        with sqlite3.connect(self._db_path) as conn:
            self._clear_path(conn, path)
            conn.commit()

    def replace_file_chunks(
        self,
        path: str,
        chunks: Sequence[Chunk],
        symbols: Sequence[tuple[str, str, str, int, str]],
    ) -> None:
        """Atomically replace all indexed content for *path*."""
        with sqlite3.connect(self._db_path) as conn:
            self._clear_path(conn, path)
            for chunk in chunks:
                conn.execute(
                    "INSERT INTO chunks(path, chunk) VALUES (?, ?)",
                    (path, chunk.text),
                )
            for sym_path, name, kind, line, signature in symbols:
                conn.execute(
                    "INSERT INTO symbols(path, name, kind, line, signature) VALUES (?, ?, ?, ?, ?)",
                    (sym_path, name, kind, line, signature),
                )
            conn.commit()

    def replace_file_text(self, path: str, body: str | None) -> None:
        """Replace *path* with a single text chunk, or with nothing when `body` is None."""
        with sqlite3.connect(self._db_path) as conn:
            self._clear_path(conn, path)
            if body is not None:
                conn.execute("INSERT INTO chunks(path, chunk) VALUES (?, ?)", (path, body))
            conn.commit()

    def _index_python(self, conn: sqlite3.Connection, path: str, source: str) -> None:
        chunks, symbols = analyze_python_source(path, source.encode("utf-8"), max_chunk_tokens=1024)
        for chunk in chunks:
            conn.execute(
                "INSERT INTO chunks(path, chunk) VALUES (?, ?)",
                (path, chunk.text),
            )
        for sym_path, name, kind, line, signature in symbols:
            conn.execute(
                "INSERT INTO symbols(path, name, kind, line, signature) VALUES (?, ?, ?, ?, ?)",
                (sym_path, name, kind, line, signature),
            )

    def _strip_frontmatter(self, text: str) -> str:
        if not text.startswith("---"):
            return text
        end = text.find("\n---", 3)
        if end == -1:
            return text
        return text[end + 4 :].lstrip("\n")

    def _index_markdown(self, conn: sqlite3.Connection, path: str, source: str) -> None:
        if is_retrieval_excluded(source):
            return
        body = self._strip_frontmatter(source)
        conn.execute(
            "INSERT INTO chunks(path, chunk) VALUES (?, ?)",
            (path, body),
        )

    def reindex_file(self, path: str, source: str) -> None:
        """Replace index entries for a single file."""
        with sqlite3.connect(self._db_path) as conn:
            self._clear_path(conn, path)
            if path.endswith(".py"):
                self._index_python(conn, path, source)
            elif path.endswith((".md", ".mdx")):
                self._index_markdown(conn, path, source)
            conn.commit()

    async def reindex_root(self, root: Path, *, max_chunk_tokens: int = 1024) -> int:
        """Walk *root* and index supported source files. Returns file count."""

        def _sync() -> int:
            count = 0
            for file_path in sorted(root.rglob("*")):
                if not file_path.is_file():
                    continue
                if any(part in _SKIP_DIRS for part in file_path.parts):
                    continue
                rel = file_path.relative_to(root).as_posix()
                if file_path.suffix == ".py":
                    source = file_path.read_text(encoding="utf-8")
                    with sqlite3.connect(self._db_path) as conn:
                        self._clear_path(conn, rel)
                        chunks, symbols = analyze_python_source(
                            rel, source.encode("utf-8"), max_chunk_tokens=max_chunk_tokens
                        )
                        for chunk in chunks:
                            conn.execute(
                                "INSERT INTO chunks(path, chunk) VALUES (?, ?)",
                                (rel, chunk.text),
                            )
                        for sym_path, name, kind, line, signature in symbols:
                            conn.execute(
                                (
                                    "INSERT INTO symbols(path, name, kind, line, signature) "
                                    "VALUES (?, ?, ?, ?, ?)"
                                ),
                                (sym_path, name, kind, line, signature),
                            )
                        conn.commit()
                    count += 1
                elif file_path.suffix in _TEXT_EXTENSIONS:
                    source = file_path.read_text(encoding="utf-8")
                    with sqlite3.connect(self._db_path) as conn:
                        self._clear_path(conn, rel)
                        self._index_markdown(conn, rel, source)
                        conn.commit()
                    if not is_retrieval_excluded(source):
                        count += 1
            return count

        return await run_sync(_sync)

    async def find_symbols(self, query: str, limit: int = 20) -> list[Symbol]:
        """Search symbols by name substring."""

        def _sync() -> list[Symbol]:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "SELECT path, name, kind, line, signature FROM symbols WHERE name LIKE ? LIMIT ?",
                    (f"%{query}%", limit),
                )
                return [
                    Symbol(
                        ref=SymbolRef(
                            path=row[0],
                            name=row[1],
                            kind=row[2],  # type: ignore[arg-type]
                            line=row[3],
                        ),
                        signature=row[4] or f"def {row[1]}()",
                    )
                    for row in cursor.fetchall()
                ]

        return await run_sync(_sync)

    async def get_skeleton(self, path: str) -> str:
        """Return structural signatures for a file (no bodies)."""

        def _sync() -> str:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "SELECT signature, kind, line FROM symbols WHERE path = ? ORDER BY line",
                    (path,),
                )
                lines: list[str] = []
                indent = 0
                for signature, kind, _line in cursor.fetchall():
                    if kind == "class":
                        lines.append(signature)
                        indent = 4
                    elif kind == "method":
                        lines.append(" " * indent + signature)
                    else:
                        lines.append(signature)
                return "\n".join(lines)

        return await run_sync(_sync)

    async def search(self, query: str, limit: int = 20) -> list[RetrievalHit]:
        """Find chunks matching free-text *query*, scored 0–1."""
        match_expr = _fts_query(query)
        if not match_expr:
            # No usable token survived tokenization. That is a true empty, and
            # answering it without a round-trip is honest, not a swallow.
            return []

        def _sync() -> list[RetrievalHit]:
            with sqlite3.connect(self._db_path) as conn:
                try:
                    cursor = conn.execute(
                        """
                        SELECT path, chunk, bm25(chunks) AS rank
                        FROM chunks
                        WHERE chunks MATCH ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (match_expr, limit),
                    )
                    rows = cursor.fetchall()
                except sqlite3.OperationalError as exc:
                    if "no such table" in str(exc):
                        return []  # cold index — a true empty
                    logger.warning("FTS5 query failed for %r: %s", query, exc)
                    raise
                if not rows:
                    return []
                ranks = [row[2] for row in rows]
                min_rank = min(ranks)
                max_rank = max(ranks)
                span = max_rank - min_rank
                hits: list[RetrievalHit] = []
                for path, chunk, rank in rows:
                    if span == 0:
                        score = 1.0
                    else:
                        score = (max_rank - rank) / span
                    hits.append(RetrievalHit(path=path, chunk=chunk, score=score))
                return hits

        return await run_sync(_sync)
