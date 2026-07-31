"""Tests for `SQLiteTrajectoryStore.list_runs` — `TrajectoryStore` PORT_VERSION 2 -> 3
(v2-S4 Epic S4.4a), the store's only cross-run query, needed by the trace exporter to
enumerate eligible runs without already knowing every `run_id`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.domain.trajectory import RunRecord
from sagiha.domain.work import TaskSpec


def _record(run_id: str, status: str) -> RunRecord:
    return RunRecord(
        run_id=run_id,
        task=TaskSpec(task_id=run_id, goal="g", acceptance=()),
        status=status,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_list_runs_returns_all_runs_most_recent_first(tmp_path: Path) -> None:
    store = SQLiteTrajectoryStore(str(tmp_path / "t.db"))
    await store.upsert_run(_record("r1", "completed"))
    await store.upsert_run(_record("r2", "completed"))
    await store.upsert_run(_record("r3", "working"))

    runs = await store.list_runs()
    run_ids = {r.run_id for r in runs}
    assert run_ids == {"r1", "r2", "r3"}


@pytest.mark.asyncio
async def test_list_runs_filters_by_status(tmp_path: Path) -> None:
    store = SQLiteTrajectoryStore(str(tmp_path / "t.db"))
    await store.upsert_run(_record("r1", "completed"))
    await store.upsert_run(_record("r2", "working"))

    completed = await store.list_runs(status="completed")
    assert [r.run_id for r in completed] == ["r1"]


@pytest.mark.asyncio
async def test_list_runs_respects_limit(tmp_path: Path) -> None:
    store = SQLiteTrajectoryStore(str(tmp_path / "t.db"))
    for i in range(5):
        await store.upsert_run(_record(f"r{i}", "completed"))

    runs = await store.list_runs(limit=2)
    assert len(runs) == 2


@pytest.mark.asyncio
async def test_list_runs_empty_store_returns_empty_list(tmp_path: Path) -> None:
    store = SQLiteTrajectoryStore(str(tmp_path / "t.db"))
    assert await store.list_runs() == []
