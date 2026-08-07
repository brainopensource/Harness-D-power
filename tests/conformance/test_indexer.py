"""Indexer conformance: the mock and the real tree-sitter adapter must behave
identically against the same port contract (ADR-0005 rev. 2)."""

from __future__ import annotations

import pytest

from aether.adapters.indexer.tree_sitter import TreeSitterIndexer
from aether.domain.ids import RunId
from aether.domain.workspace import WorktreeRef
from aether.ports.indexer import Indexer
from tests.aether.mocks import InMemoryIndexer


@pytest.mark.parametrize("indexer", [InMemoryIndexer(), TreeSitterIndexer("/tmp")])
def test_indexer_satisfies_protocol(indexer: object) -> None:
    assert isinstance(indexer, Indexer)


@pytest.fixture
def worktree_with_python_file(tmp_path):  # noqa: ANN001
    worktrees_root = tmp_path / "worktrees"
    worktree_dir = worktrees_root / "run-1" / "wt-1"
    worktree_dir.mkdir(parents=True)
    (worktree_dir / "mod.py").write_text(
        "def greet(name):\n    return f'hi {name}'\n\n\nclass Greeter:\n    pass\n"
    )
    worktree = WorktreeRef(worktree_id="wt-1", run_id=RunId("run-1"), base_commit="a" * 40, abs_hint="/x")
    return str(worktrees_root), worktree


async def test_build_and_outline_finds_top_level_symbols(worktree_with_python_file) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_with_python_file
    indexer = TreeSitterIndexer(worktrees_root)

    await indexer.build(worktree)
    outline = await indexer.outline(worktree, "mod.py")

    names = {hit.name for hit in outline}
    assert names == {"greet", "Greeter"}
    kinds = {hit.name: hit.kind for hit in outline}
    assert kinds["greet"] == "function"
    assert kinds["Greeter"] == "class"


async def test_search_matches_by_substring(worktree_with_python_file) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_with_python_file
    indexer = TreeSitterIndexer(worktrees_root)
    await indexer.build(worktree)

    hits = await indexer.search(worktree, "greet", limit=20)

    assert {h.name for h in hits} == {"greet", "Greeter"}


async def test_search_respects_limit(worktree_with_python_file) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_with_python_file
    indexer = TreeSitterIndexer(worktrees_root)
    await indexer.build(worktree)

    hits = await indexer.search(worktree, "e", limit=1)

    assert len(hits) == 1
