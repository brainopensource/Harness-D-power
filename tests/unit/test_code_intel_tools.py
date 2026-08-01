"""Unit tests for code-intelligence tools (v2-S6 Task 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sagiha.adapters.code_graph.treesitter import TreeSitterCodeGraph
from sagiha.adapters.indexer.fts5 import FTS5Indexer
from sagiha.adapters.indexer.service import IndexService
from sagiha.adapters.tools.builtins import register_builtin_tools
from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.composition import build_retrieval_seed
from sagiha.domain.content import EffectClass, ToolCall

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_mini"


@pytest.fixture
async def indexed_workspace(tmp_path: Path) -> tuple[LocalWorkspace, FTS5Indexer, TreeSitterCodeGraph]:
    root = FIXTURE
    indexer = FTS5Indexer(db_path=str(tmp_path / "index.db"))
    graph = TreeSitterCodeGraph(db_path=str(tmp_path / "graph.db"), workspace_root=root)
    service = IndexService(root, indexer, graph)
    await service.reindex(None)
    return LocalWorkspace(str(root)), indexer, graph


@pytest.mark.asyncio
async def test_register_code_intel_tools_when_indexer_and_graph_provided(
    indexed_workspace: tuple[LocalWorkspace, FTS5Indexer, TreeSitterCodeGraph],
) -> None:
    workspace, indexer, graph = indexed_workspace
    registry = DefaultToolRegistry()
    schemas = register_builtin_tools(registry, workspace, indexer=indexer, code_graph=graph)

    assert len(schemas) == 9
    assert "find_symbols" in schemas
    assert "get_skeleton" in schemas
    assert "impacted_by" in schemas
    assert await registry.get_effect_class("find_symbols") is EffectClass.PURE
    assert await registry.trusted_output("find_symbols") is True
    assert await registry.trusted_output("get_skeleton") is True
    assert await registry.trusted_output("impacted_by") is True


@pytest.mark.asyncio
async def test_find_symbols_tool_returns_symbol_json(
    indexed_workspace: tuple[LocalWorkspace, FTS5Indexer, TreeSitterCodeGraph],
) -> None:
    workspace, indexer, graph = indexed_workspace
    registry = DefaultToolRegistry()
    register_builtin_tools(registry, workspace, indexer=indexer, code_graph=graph)

    result = await registry.dispatch(
        ToolCall(
            call_id="c1",
            tool_name="find_symbols",
            arguments={"query": "greet"},
            effect=EffectClass.PURE,
        )
    )
    assert not result.is_error
    payload = json.loads(result.content[0].text)
    assert any(item["ref"]["name"] == "greet" for item in payload)


@pytest.mark.asyncio
async def test_get_skeleton_tool_returns_signatures(
    indexed_workspace: tuple[LocalWorkspace, FTS5Indexer, TreeSitterCodeGraph],
) -> None:
    workspace, indexer, graph = indexed_workspace
    registry = DefaultToolRegistry()
    register_builtin_tools(registry, workspace, indexer=indexer, code_graph=graph)

    result = await registry.dispatch(
        ToolCall(
            call_id="c2",
            tool_name="get_skeleton",
            arguments={"path": "pkg/util.py"},
            effect=EffectClass.PURE,
        )
    )
    assert not result.is_error
    assert "Greeter" in result.content[0].text


@pytest.mark.asyncio
async def test_impacted_by_tool_returns_paths(
    indexed_workspace: tuple[LocalWorkspace, FTS5Indexer, TreeSitterCodeGraph],
) -> None:
    workspace, indexer, graph = indexed_workspace
    registry = DefaultToolRegistry()
    register_builtin_tools(registry, workspace, indexer=indexer, code_graph=graph)

    result = await registry.dispatch(
        ToolCall(
            call_id="c3",
            tool_name="impacted_by",
            arguments={"path": "pkg/util.py", "hops": 2},
            effect=EffectClass.PURE,
        )
    )
    assert not result.is_error
    payload = json.loads(result.content[0].text)
    assert "pkg/client.py" in payload


@pytest.mark.asyncio
async def test_build_retrieval_seed_returns_hits(
    indexed_workspace: tuple[LocalWorkspace, FTS5Indexer, TreeSitterCodeGraph],
) -> None:
    _workspace, indexer, _graph = indexed_workspace
    seed = await build_retrieval_seed(indexer, "greet", top_k=5)
    assert len(seed) >= 1
    assert all(0.0 <= hit.score <= 1.0 for hit in seed)
