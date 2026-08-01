from __future__ import annotations

from pathlib import Path

import pytest

from sagiha.adapters.indexer.fts5 import FTS5Indexer

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_mini"


@pytest.mark.asyncio
async def test_reindex_finds_symbols_and_skeleton(tmp_path: Path) -> None:
    db = tmp_path / "index.db"
    idx = FTS5Indexer(db_path=str(db))
    n = await idx.reindex_root(FIXTURE)
    assert n >= 1
    syms = await idx.find_symbols("greet", limit=10)
    assert any(s.ref.name == "greet" for s in syms)
    skel = await idx.get_skeleton("pkg/util.py")
    assert "def greet" in skel
    assert "return f" not in skel
    hits = await idx.neighbors("greet", limit=10)
    assert hits
    assert all(0.0 <= h.score <= 1.0 for h in hits)


@pytest.mark.asyncio
async def test_excluded_frontmatter_not_indexed(tmp_path: Path) -> None:
    idx = FTS5Indexer(db_path=str(tmp_path / "index.db"))
    await idx.reindex_root(FIXTURE)
    hits = await idx.neighbors("UNIQUE_EXCLUDED_TOKEN_XYZ", limit=20)
    assert hits == []
    visible = await idx.neighbors("VISIBLE_DOC_TOKEN_ABC", limit=20)
    assert any("VISIBLE_DOC_TOKEN_ABC" in h.chunk for h in visible)
