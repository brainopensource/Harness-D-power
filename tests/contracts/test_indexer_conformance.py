from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from sagiha.adapters.indexer.fts5 import FTS5Indexer, _fts_query

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
    hits = await idx.search("greet", limit=10)
    assert hits
    assert all(0.0 <= h.score <= 1.0 for h in hits)


@pytest.mark.asyncio
async def test_excluded_frontmatter_not_indexed(tmp_path: Path) -> None:
    idx = FTS5Indexer(db_path=str(tmp_path / "index.db"))
    await idx.reindex_root(FIXTURE)
    hits = await idx.search("UNIQUE_EXCLUDED_TOKEN_XYZ", limit=20)
    assert hits == []
    visible = await idx.search("VISIBLE_DOC_TOKEN_ABC", limit=20)
    assert any("VISIBLE_DOC_TOKEN_ABC" in h.chunk for h in visible)


# --- C-1 regression: goal-shaped queries are searches, not FTS5 syntax errors ---


@pytest.fixture
async def indexed(tmp_path: Path) -> FTS5Indexer:
    idx = FTS5Indexer(db_path=str(tmp_path / "index.db"))
    await idx.reindex_root(FIXTURE)
    return idx


@pytest.mark.asyncio
async def test_goal_shaped_query_returns_same_paths_as_bare_keyword(
    indexed: FTS5Indexer,
) -> None:
    """C-1: a realistic goal string must retrieve what its keyword does.

    Before the fix, FTS5 parsed `greet()` as query syntax and raised
    `fts5: syntax error near ")"`, which a bare `except` turned into `[]`.
    """
    bare = await indexed.search("greet", limit=10)
    goal = await indexed.search("Fix the bug in greet() so it returns a name", limit=10)

    assert bare, "fixture must contain a `greet` chunk for this test to mean anything"
    assert goal, "goal-shaped query returned nothing — C-1 has regressed"
    assert {h.path for h in bare} <= {h.path for h in goal}


@pytest.mark.parametrize(
    "query",
    [
        "handle greet's input",       # apostrophe
        "add greet - use Greeter",    # bare hyphen (column-syntax trap)
        "call greet() twice",         # parentheses
        "fix util:greet mapping",     # colon
        "greet AND shout",            # bare boolean operator
    ],
)
@pytest.mark.asyncio
async def test_punctuated_queries_search_instead_of_erroring(
    indexed: FTS5Indexer, query: str
) -> None:
    """Each of these raised `fts5: syntax error` before the fix, and the bare
    `except` converted it to `[]`. Every one carries a token the fixture has,
    so a non-empty result is the only honest answer.
    """
    assert await indexed.search(query, limit=10)


@pytest.mark.asyncio
async def test_punctuation_only_query_returns_empty_without_touching_the_db(
    indexed: FTS5Indexer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A query with no usable token is a true empty — answer it without SQL."""

    def _no_connections(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover - must not run
        raise AssertionError("search() opened the database for an unusable query")

    monkeypatch.setattr(sqlite3, "connect", _no_connections)
    assert await indexed.search("()  -- :: !", limit=10) == []


@pytest.mark.asyncio
async def test_real_operational_error_propagates_instead_of_returning_empty(
    indexed: FTS5Indexer,
) -> None:
    """Only `no such table` is a true empty. Everything else is a lying instrument."""
    with sqlite3.connect(indexed._db_path) as conn:
        conn.execute("DROP TABLE chunks")
        conn.execute("CREATE TABLE chunks (path TEXT, chunk TEXT)")  # exists, but not FTS5
        conn.commit()

    with pytest.raises(sqlite3.OperationalError):
        await indexed.search("greet", limit=10)


@pytest.mark.asyncio
async def test_cold_index_returns_empty_not_error(tmp_path: Path) -> None:
    idx = FTS5Indexer(db_path=str(tmp_path / "cold.db"))
    with sqlite3.connect(idx._db_path) as conn:
        conn.execute("DROP TABLE chunks")
        conn.commit()
    assert await idx.search("greet", limit=10) == []


def test_fts_query_quotes_terms_and_drops_operators() -> None:
    assert _fts_query("greet") == '"greet"'
    assert _fts_query("greet AND farewell") == '"greet" OR "farewell"'
    assert _fts_query("call greet() twice") == '"call" OR "greet" OR "twice"'
    assert _fts_query("()  -- ::") == ""
    assert _fts_query("a bc") == '"bc"'  # 1-char tokens dropped as noise
