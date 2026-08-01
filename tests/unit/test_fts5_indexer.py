"""Unit tests for FTS5 indexer adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from sagiha.adapters.indexer.fts5 import FTS5Indexer

SAMPLE_PY = '''\
def greet(name: str) -> str:
    """Return a greeting."""
    return f"hello {name}"
'''


@pytest.fixture
def indexer(tmp_path) -> FTS5Indexer:
    db_path = str(tmp_path / "test_index.db")
    return FTS5Indexer(db_path=db_path)


@pytest.mark.asyncio
async def test_fts5_db_init_creates_virtual_table(indexer: FTS5Indexer) -> None:
    symbols = await indexer.find_symbols("test")
    assert symbols == []


@pytest.mark.asyncio
async def test_find_symbols_empty_db_returns_empty(indexer: FTS5Indexer) -> None:
    result = await indexer.find_symbols("nonexistent")
    assert result == []


@pytest.mark.asyncio
async def test_reindex_file_indexes_symbols(indexer: FTS5Indexer) -> None:
    indexer.reindex_file("pkg/util.py", SAMPLE_PY)
    syms = await indexer.find_symbols("greet", limit=10)
    assert any(s.ref.name == "greet" for s in syms)


@pytest.mark.asyncio
async def test_get_skeleton_strips_bodies(indexer: FTS5Indexer) -> None:
    indexer.reindex_file("pkg/util.py", SAMPLE_PY)
    skel = await indexer.get_skeleton("pkg/util.py")
    assert "def greet" in skel
    assert "return f" not in skel


@pytest.mark.asyncio
async def test_search_finds_indexed_chunks(indexer: FTS5Indexer) -> None:
    indexer.reindex_file("pkg/util.py", SAMPLE_PY)
    hits = await indexer.search("greet", limit=10)
    assert hits
    assert all(0.0 <= h.score <= 1.0 for h in hits)


@pytest.mark.asyncio
async def test_reindex_root_clears_excluded_markdown(tmp_path: Path) -> None:
    """Excluded markdown must clear prior index rows on reindex."""
    db_path = str(tmp_path / "test_index.db")
    indexer = FTS5Indexer(db_path=db_path)
    root = tmp_path / "docs"
    root.mkdir()
    doc = root / "note.md"
    token = "UNIQUE_CLEAR_ON_EXCLUDE_TOKEN"
    doc.write_text(f"---\nstatus: draft\n---\n{token}\n", encoding="utf-8")

    await indexer.reindex_root(root)
    assert await indexer.search(token, limit=10)

    doc.write_text(
        f"---\nstatus: draft\nretrieval: excluded\n---\n{token}\n",
        encoding="utf-8",
    )
    await indexer.reindex_root(root)
    assert await indexer.search(token, limit=10) == []
