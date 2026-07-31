"""Unit tests for FTS5 indexer (v2-S6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sagiha.adapters.indexer.frontmatter import is_retrieval_excluded
from sagiha.adapters.indexer.fts5 import FTS5Indexer


@pytest.fixture
def indexer(tmp_path: Path) -> FTS5Indexer:
    return FTS5Indexer(db_path=str(tmp_path / "test_index.db"))


def test_frontmatter_excluded() -> None:
    assert is_retrieval_excluded("---\nretrieval: excluded\n---\nbody\n")
    assert not is_retrieval_excluded("---\nstatus: rationale\n---\nbody\n")
    assert not is_retrieval_excluded("no frontmatter\n")


@pytest.mark.asyncio
async def test_fts5_db_init_creates_virtual_table(indexer: FTS5Indexer) -> None:
    symbols = await indexer.find_symbols("test")
    assert symbols == []


@pytest.mark.asyncio
async def test_reindex_file_finds_symbol_and_skeleton(indexer: FTS5Indexer) -> None:
    src = "def alpha(x):\n    return x + 1\n"
    await indexer.reindex_file("mod.py", src)
    syms = await indexer.find_symbols("alpha")
    assert any(s.ref.name == "alpha" for s in syms)
    skel = await indexer.get_skeleton("mod.py")
    assert "def alpha" in skel
    assert "return x" not in skel
    hits = await indexer.neighbors("alpha", limit=5)
    assert hits
    assert all(0.0 <= h.score <= 1.0 for h in hits)


@pytest.mark.asyncio
async def test_find_symbols_empty_db_returns_empty(indexer: FTS5Indexer) -> None:
    result = await indexer.find_symbols("nonexistent")
    assert result == []
