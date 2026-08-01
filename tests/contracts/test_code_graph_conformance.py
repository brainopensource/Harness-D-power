from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sagiha.adapters.code_graph.treesitter import TreeSitterCodeGraph

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_mini"


def _edge_set(db_path: str) -> set[tuple[str, str, str]]:
    with sqlite3.connect(db_path) as c:
        return set(c.execute("SELECT src, dst, kind FROM edges").fetchall())


@pytest.mark.asyncio
async def test_import_edges_and_impacted_by(tmp_path: Path) -> None:
    g = TreeSitterCodeGraph(db_path=str(tmp_path / "g.db"))
    n = await g.rebuild_from_root(FIXTURE)
    assert n >= 1

    with sqlite3.connect(str(tmp_path / "g.db")) as conn:
        imports = set(conn.execute("SELECT src, dst FROM edges WHERE kind = 'imports'").fetchall())
    assert ("pkg/client.py", "pkg/util.py") in imports

    impacted = await g.impacted_by("pkg/util.py", hops=2)
    assert "pkg/client.py" in impacted


@pytest.mark.asyncio
async def test_rebuild_from_head_deterministic(tmp_path: Path) -> None:
    db1 = str(tmp_path / "g1.db")
    db2 = str(tmp_path / "g2.db")
    g1 = TreeSitterCodeGraph(db_path=db1)
    g2 = TreeSitterCodeGraph(db_path=db2)
    await g1.rebuild_from_root(FIXTURE)
    await g2.rebuild_from_root(FIXTURE)
    assert _edge_set(db1) == _edge_set(db2)
