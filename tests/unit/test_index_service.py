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

    hits = await index_service._indexer.search("UNIQUE_EXCLUDED_TOKEN_XYZ")
    assert hits == []

    visible_hits = await index_service._indexer.search("VISIBLE_DOC_TOKEN_ABC")
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


@pytest.mark.asyncio
async def test_full_reindex_prunes_deleted_files(tmp_path: Path) -> None:
    """m-5: a full reindex must forget files that no longer exist.

    Before this, `_reindex_all` only updated the files it walked. A deleted
    source kept its chunks, symbols and graph edges indefinitely, so retrieval
    surfaced content that was not on disk.
    """
    import shutil

    root = tmp_path / "workspace"
    shutil.copytree(FIXTURE, root)
    indexer = FTS5Indexer(db_path=str(tmp_path / "index.db"))
    graph = TreeSitterCodeGraph(db_path=str(tmp_path / "graph.db"), workspace_root=root)
    service = IndexService(root, indexer, graph)

    await service.reindex(None)
    assert any(h.path == "pkg/client.py" for h in await indexer.search("client", limit=50))
    assert "pkg/client.py" in indexer.indexed_paths()

    (root / "pkg" / "client.py").unlink()
    await service.reindex(None)

    assert "pkg/client.py" not in indexer.indexed_paths(), "deleted file kept its index rows"
    assert "pkg/client.py" not in graph.graphed_paths(), "deleted file kept its graph rows"
    # The surviving file is untouched.
    assert "pkg/util.py" in indexer.indexed_paths()
    assert any(h.path == "pkg/util.py" for h in await indexer.search("greet", limit=50))
