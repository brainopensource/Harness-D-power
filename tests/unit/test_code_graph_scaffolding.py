"""Unit tests for code graph adapter."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sagiha.adapters.code_graph.treesitter import TreeSitterCodeGraph, _parse_symbol_ref
from sagiha.adapters.indexer.chunking import parse_python
from sagiha.domain.graph import GraphEdge, SymbolRef

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_mini"


@pytest.fixture
def code_graph(tmp_path) -> TreeSitterCodeGraph:
    db_path = str(tmp_path / "test_graph.db")
    return TreeSitterCodeGraph(db_path=db_path)


@pytest.mark.asyncio
async def test_code_graph_db_init_creates_tables(code_graph: TreeSitterCodeGraph) -> None:
    result = await code_graph.impacted_by("nonexistent.py")
    assert result == []


@pytest.mark.asyncio
async def test_upsert_and_query_edges(code_graph: TreeSitterCodeGraph) -> None:
    edges = [
        GraphEdge(src="a.py", dst="b.py", kind="imports"),
        GraphEdge(src="a.py", dst="c.py", kind="calls"),
    ]
    await code_graph.upsert_edges(edges)
    assert set(await code_graph.impacted_by("b.py", hops=1)) == {"a.py"}
    assert set(await code_graph.impacted_by("c.py", hops=1)) == {"a.py"}


@pytest.mark.asyncio
async def test_impacted_by_hop_limited_bfs(code_graph: TreeSitterCodeGraph) -> None:
    edges = [
        GraphEdge(src="x.py", dst="y.py", kind="imports"),
        GraphEdge(src="y.py", dst="z.py", kind="imports"),
    ]
    await code_graph.upsert_edges(edges)
    assert await code_graph.impacted_by("z.py", hops=1) == ["y.py"]
    assert set(await code_graph.impacted_by("z.py", hops=2)) == {"y.py", "x.py"}


@pytest.mark.asyncio
async def test_index_file_extracts_import_and_define_edges(code_graph: TreeSitterCodeGraph) -> None:
    source = b"from pkg.util import greet\n\ndef main() -> None:\n    greet('x')\n"
    edges = code_graph.index_file("pkg/client.py", source)
    kinds = {e.kind for e in edges}
    assert "imports" in kinds
    assert "defines" in kinds


@pytest.mark.asyncio
async def test_rebuild_from_root_indexes_fixture(code_graph: TreeSitterCodeGraph) -> None:
    n = await code_graph.rebuild_from_root(FIXTURE)
    assert n >= 2
    impacted = await code_graph.impacted_by("pkg/util.py", hops=2)
    assert "pkg/client.py" in impacted


@pytest.mark.asyncio
async def test_callers_of_same_file(code_graph: TreeSitterCodeGraph) -> None:
    await code_graph.rebuild_from_root(FIXTURE)
    target = SymbolRef(path="pkg/util.py", name="greet", kind="function", line=3)
    callers = await code_graph.callers_of(target)
    shout = next(c for c in callers if c.name == "shout")
    assert shout.path == "pkg/util.py"
    assert shout.kind == "method"
    assert shout.line > 1


def test_parse_symbol_ref_nested_method_resolves_module_path() -> None:
    ref = _parse_symbol_ref("pkg.util.Greeter.shout", module="pkg.util")
    assert ref is not None
    assert ref.path == "pkg/util.py"
    assert ref.name == "shout"
    assert ref.kind == "method"


@pytest.mark.asyncio
async def test_index_file_stores_class_kind(code_graph: TreeSitterCodeGraph) -> None:
    source = (
        b"class Greeter:\n"
        b"    def shout(self, name: str) -> str:\n"
        b"        return name.upper()\n"
    )
    tree = parse_python(source)
    edges, symbol_meta = code_graph.index_file_from_tree("pkg/util.py", source, tree)
    code_graph.replace_file_edges("pkg/util.py", edges, symbol_meta)
    with sqlite3.connect(code_graph._db_path) as conn:
        row = conn.execute(
            "SELECT kind, line FROM symbols WHERE path = ? AND name = ?",
            ("pkg/util.py", "Greeter"),
        ).fetchone()
    assert row is not None
    assert row[0] == "class"
    assert row[1] == 1


@pytest.mark.asyncio
async def test_co_changed_with_non_git_returns_empty(code_graph: TreeSitterCodeGraph) -> None:
    result = await code_graph.co_changed_with("a.py", since=datetime.now(UTC))
    assert result == []
