"""Unit tests for Block 4 scaffolding — code graph adapter."""

from __future__ import annotations

from datetime import UTC

import pytest

from sagiha.adapters.code_graph.treesitter import TreeSitterCodeGraph
from sagiha.domain.graph import GraphEdge, SymbolRef


@pytest.fixture
def code_graph(tmp_path) -> TreeSitterCodeGraph:
    db_path = str(tmp_path / "test_graph.db")
    return TreeSitterCodeGraph(db_path=db_path)


@pytest.mark.asyncio
async def test_code_graph_db_init_creates_tables(code_graph: TreeSitterCodeGraph) -> None:
    # If init succeeded without error, tables were created
    result = await code_graph.impacted_by("nonexistent.py")
    assert result == []


@pytest.mark.asyncio
async def test_upsert_and_query_edges(code_graph: TreeSitterCodeGraph) -> None:
    edges = [
        GraphEdge(src="a.py", dst="b.py", kind="imports"),
        GraphEdge(src="a.py", dst="c.py", kind="calls"),
    ]
    await code_graph.upsert_edges(edges)
    neighbors = await code_graph.impacted_by("a.py")
    assert set(neighbors) == {"b.py", "c.py"}


@pytest.mark.asyncio
async def test_impacted_by_returns_direct_neighbors(code_graph: TreeSitterCodeGraph) -> None:
    edges = [
        GraphEdge(src="x.py", dst="y.py", kind="imports"),
        GraphEdge(src="y.py", dst="z.py", kind="imports"),
    ]
    await code_graph.upsert_edges(edges)
    # Current implementation only returns direct neighbors (1 hop)
    result = await code_graph.impacted_by("x.py")
    assert result == ["y.py"]


@pytest.mark.asyncio
async def test_callers_of_returns_empty(code_graph: TreeSitterCodeGraph) -> None:
    sym = SymbolRef(path="a.py", name="foo", kind="function", line=10)
    callers = await code_graph.callers_of(sym)
    assert callers == []


@pytest.mark.asyncio
async def test_co_changed_with_returns_empty(code_graph: TreeSitterCodeGraph) -> None:
    from datetime import datetime

    result = await code_graph.co_changed_with("a.py", since=datetime.now(UTC))
    assert result == []
