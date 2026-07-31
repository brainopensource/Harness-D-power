"""SQLite FTS5 indexer — full-text search over AST-bounded code chunks.

See ports/indexer.py and docs/08-decisions/0014-defer-dense-retrieval.md.
v1 retrieval is lexical + graph; dense tier deferred until recall@10 misses.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

from anyio.to_thread import run_sync

from sagiha.adapters.indexer.chunking import analyze_python_source, skeleton_from_symbols
from sagiha.adapters.indexer.frontmatter import is_retrieval_excluded
from sagiha.domain.content import Symbol
from sagiha.domain.graph import RetrievalHit, SymbolRef

logger = logging.getLogger(__name__)

_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", ".sagiha"})
_CODE_SUFFIXES = frozenset({".py"})
_DOC_SUFFIXES = frozenset({".md", ".mdx"})


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _fts_query(raw: str) -> str:
    """Escape user text into a safe FTS5 MATCH query (AND of quoted tokens)."""
    tokens = re.findall(r"[A-Za-z0-9_]+", raw)
    if not tokens:
        return '""'
    return " AND ".join(f'"{t}"' for t in tokens)


class FTS5Indexer:
    """SQLite FTS5-backed code indexer with AST-bounded chunking."""

    def __init__(self, db_path: str = ".sagiha/index.db") -> None:
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chunks_meta (
                    id INTEGER PRIMARY KEY,
                    path TEXT NOT NULL,
                    symbol_path TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    chunk TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    path,
                    symbol_path,
                    chunk,
                    content='chunks_meta',
                    content_rowid='id'
                );
                CREATE TABLE IF NOT EXISTS symbols (
                    path TEXT NOT NULL,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    signature TEXT DEFAULT '',
                    PRIMARY KEY (path, name, line)
                );
                CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
                """
            )
            conn.commit()

    def _clear_path(self, conn: sqlite3.Connection, path: str) -> None:
        rows = conn.execute("SELECT id FROM chunks_meta WHERE path = ?", (path,)).fetchall()
        for row in rows:
            rowid = int(row["id"])
            conn.execute("DELETE FROM chunks_fts WHERE rowid = ?", (rowid,))
            conn.execute("DELETE FROM chunks_meta WHERE id = ?", (rowid,))
        conn.execute("DELETE FROM symbols WHERE path = ?", (path,))

    def _insert_chunk(
        self,
        conn: sqlite3.Connection,
        *,
        path: str,
        symbol_path: str,
        start_line: int,
        end_line: int,
        chunk: str,
    ) -> None:
        cur = conn.execute(
            """
            INSERT INTO chunks_meta (path, symbol_path, start_line, end_line, chunk)
            VALUES (?, ?, ?, ?, ?)
            """,
            (path, symbol_path, start_line, end_line, chunk),
        )
        rowid = cur.lastrowid
        if rowid is None:
            raise RuntimeError("sqlite insert into chunks_meta returned no rowid")
        rowid_i = int(rowid)
        conn.execute(
            """
            INSERT INTO chunks_fts (rowid, path, symbol_path, chunk)
            VALUES (?, ?, ?, ?)
            """,
            (rowid_i, path, symbol_path, chunk),
        )

    def _index_python(
        self, conn: sqlite3.Connection, path: str, source: bytes, *, max_chunk_tokens: int
    ) -> None:
        self._clear_path(conn, path)
        chunks, symbols = analyze_python_source(path, source, max_chunk_tokens=max_chunk_tokens)
        for ch in chunks:
            self._insert_chunk(
                conn,
                path=ch.path,
                symbol_path=ch.symbol_path,
                start_line=ch.start_line,
                end_line=ch.end_line,
                chunk=ch.text,
            )
        for p, name, kind, line, sig in symbols:
            # Symbol.kind is a closed Literal — map unknowns to function
            kind_lit = kind if kind in ("function", "class", "method", "module", "variable") else "function"
            conn.execute(
                """
                INSERT OR REPLACE INTO symbols (path, name, kind, line, signature)
                VALUES (?, ?, ?, ?, ?)
                """,
                (p, name, kind_lit, line, sig),
            )

    def _index_doc(self, conn: sqlite3.Connection, path: str, source: str) -> None:
        if is_retrieval_excluded(source):
            self._clear_path(conn, path)
            return
        self._clear_path(conn, path)
        self._insert_chunk(
            conn,
            path=path,
            symbol_path=path,
            start_line=1,
            end_line=source.count("\n") + 1,
            chunk=source,
        )

    async def reindex_file(self, path: str, source: str, *, max_chunk_tokens: int = 1024) -> None:
        def _sync() -> None:
            with self._connect() as conn:
                if path.endswith(tuple(_CODE_SUFFIXES)):
                    self._index_python(conn, path, source.encode("utf-8"), max_chunk_tokens=max_chunk_tokens)
                elif path.endswith(tuple(_DOC_SUFFIXES)):
                    self._index_doc(conn, path, source)
                else:
                    self._clear_path(conn, path)
                    self._insert_chunk(
                        conn,
                        path=path,
                        symbol_path=path,
                        start_line=1,
                        end_line=1,
                        chunk=source,
                    )
                conn.commit()

        await run_sync(_sync)

    async def reindex_root(self, root: Path, *, max_chunk_tokens: int = 1024) -> int:
        def _sync() -> int:
            resolved = root.resolve()
            counted = 0
            with self._connect() as conn:
                for path in sorted(resolved.rglob("*")):
                    if not path.is_file():
                        continue
                    if any(part in _SKIP_DIRS for part in path.parts):
                        continue
                    rel = _rel(resolved, path)
                    suffix = path.suffix.lower()
                    try:
                        text = path.read_text(encoding="utf-8")
                    except (UnicodeDecodeError, OSError):
                        logger.debug("skip unreadable %s", rel)
                        continue
                    if suffix in _CODE_SUFFIXES:
                        self._index_python(
                            conn, rel, text.encode("utf-8"), max_chunk_tokens=max_chunk_tokens
                        )
                        counted += 1
                    elif suffix in _DOC_SUFFIXES:
                        if is_retrieval_excluded(text):
                            self._clear_path(conn, rel)
                            continue
                        self._index_doc(conn, rel, text)
                        counted += 1
                conn.commit()
            return counted

        return await run_sync(_sync)

    async def find_symbols(self, query: str, limit: int = 20) -> list[Symbol]:
        def _sync() -> list[Symbol]:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    SELECT path, name, kind, line, signature
                    FROM symbols
                    WHERE name LIKE ?
                    ORDER BY LENGTH(name) ASC, name ASC
                    LIMIT ?
                    """,
                    (f"%{query}%", limit),
                )
                out: list[Symbol] = []
                for row in cursor.fetchall():
                    kind = row["kind"]
                    if kind not in ("function", "class", "method", "module", "variable"):
                        kind = "function"
                    out.append(
                        Symbol(
                            ref=SymbolRef(
                                path=row["path"],
                                name=row["name"],
                                kind=kind,  # type: ignore[arg-type]
                                line=int(row["line"]),
                            ),
                            signature=row["signature"] or f"def {row['name']}()",
                        )
                    )
                return out

        return await run_sync(_sync)

    async def get_skeleton(self, path: str) -> str:
        def _sync() -> str:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT signature FROM symbols
                    WHERE path = ?
                    ORDER BY line ASC
                    """,
                    (path,),
                ).fetchall()
            sigs = [str(r["signature"]) for r in rows if r["signature"]]
            return skeleton_from_symbols(sigs)

        return await run_sync(_sync)

    async def neighbors(self, path: str, limit: int = 20) -> list[RetrievalHit]:
        """FTS5 search. `path` is treated as the query string (port name is historical)."""
        q = _fts_query(path)

        def _sync() -> list[RetrievalHit]:
            with self._connect() as conn:
                try:
                    rows = conn.execute(
                        """
                        SELECT path, chunk, bm25(chunks_fts) AS rank
                        FROM chunks_fts
                        WHERE chunks_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (q, limit),
                    ).fetchall()
                except sqlite3.OperationalError:
                    return []
            if not rows:
                return []
            # bm25: lower is better; normalize to 0–1 within the batch (best → 1.0).
            ranks = [float(r["rank"]) for r in rows]
            lo, hi = min(ranks), max(ranks)
            span = (hi - lo) if hi > lo else 1.0
            hits: list[RetrievalHit] = []
            for r in rows:
                rank = float(r["rank"])
                score = 1.0 - ((rank - lo) / span)
                hits.append(
                    RetrievalHit(
                        path=str(r["path"]),
                        chunk=str(r["chunk"]),
                        score=score,
                        metadata={"symbol_query": path},
                    )
                )
            return hits

        return await run_sync(_sync)
