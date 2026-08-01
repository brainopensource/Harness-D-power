"""Unit tests for Block 4 scaffolding — FTS5 indexer adapter."""

from __future__ import annotations

import pytest

from sagiha.adapters.indexer.fts5 import FTS5Indexer


@pytest.fixture
def indexer(tmp_path) -> FTS5Indexer:
    db_path = str(tmp_path / "test_index.db")
    return FTS5Indexer(db_path=db_path)


@pytest.mark.asyncio
async def test_fts5_db_init_creates_virtual_table(indexer: FTS5Indexer) -> None:
    # If init succeeded, the FTS5 virtual table was created
    symbols = await indexer.find_symbols("test")
    assert symbols == []


@pytest.mark.asyncio
async def test_find_symbols_empty_db_returns_empty(indexer: FTS5Indexer) -> None:
    result = await indexer.find_symbols("nonexistent")
    assert result == []


@pytest.mark.asyncio
async def test_get_skeleton_returns_empty(indexer: FTS5Indexer) -> None:
    skeleton = await indexer.get_skeleton("some/file.py")
    assert skeleton == ""


@pytest.mark.asyncio
async def test_neighbors_returns_empty(indexer: FTS5Indexer) -> None:
    result = await indexer.neighbors("some/file.py")
    assert result == []
