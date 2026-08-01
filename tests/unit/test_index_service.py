"""Unit tests for IndexService shared indexing walk."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sagiha.adapters.code_graph.treesitter import TreeSitterCodeGraph
from sagiha.adapters.indexer.fts5 import FTS5Indexer
from sagiha.adapters.indexer.service import IndexService

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_mini"


@pytest.fixture
def index_service(tmp_path) -> IndexService:
    root = FIXTURE
    indexer = FTS5Indexer(db_path=str(tmp_path / "index.db"))
    graph = TreeSitterCodeGraph(db_path=str(tmp_path / "graph.db"), workspace_root=root)
    return IndexService(root, indexer, graph)


@pytest.mark.asyncio
async def test_reindex_fixture_populates_indexer_and_graph(index_service: IndexService) -> None:
    await index_service.reindex(None)

    symbols = await index_service._indexer.find_symbols("greet")
    assert any(s.ref.name == "greet" for s in symbols)

    with sqlite3.connect(index_service._graph._db_path) as conn:
        imports = conn.execute(
            "SELECT src, dst FROM edges WHERE kind = 'imports'",
        ).fetchall()
    assert ("pkg/client.py", "pkg/util.py") in set(imports)


@pytest.mark.asyncio
async def test_reindex_skips_excluded_markdown(index_service: IndexService) -> None:
    await index_service.reindex(["docs/secret.md", "docs/visible.md"])

    hits = await index_service._indexer.neighbors("UNIQUE_EXCLUDED_TOKEN_XYZ")
    assert hits == []

    visible_hits = await index_service._indexer.neighbors("VISIBLE_DOC_TOKEN_ABC")
    assert len(visible_hits) >= 1


@pytest.mark.asyncio
async def test_reindex_single_python_path(index_service: IndexService) -> None:
    await index_service.reindex(["pkg/util.py"])

    symbols = await index_service._indexer.find_symbols("Greeter")
    assert any(s.ref.kind == "class" for s in symbols)

    with sqlite3.connect(index_service._graph._db_path) as conn:
        row = conn.execute(
            "SELECT kind, line FROM symbols WHERE path = ? AND name = ?",
            ("pkg/util.py", "Greeter"),
        ).fetchone()
    assert row is not None
    assert row[0] == "class"
    assert row[1] > 1
