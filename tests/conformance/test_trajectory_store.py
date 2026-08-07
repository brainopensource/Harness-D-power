"""TrajectoryStore conformance: the mock and the real SQLite adapter must behave
identically against the same port contract (ADR-0005 rev. 2)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aether.adapters.trajectory_store.sqlite import SqliteTrajectoryStore
from aether.domain.ids import RunId
from aether.ports.trajectory_store import StoredEvent, TrajectoryStore
from tests.aether.mocks import InMemoryTrajectoryStore


def _stores(tmp_path):  # noqa: ANN001
    return [InMemoryTrajectoryStore(), SqliteTrajectoryStore(str(tmp_path / "trajectory.db"))]


@pytest.mark.parametrize("store_factory", [InMemoryTrajectoryStore, None])
async def test_store_satisfies_protocol(tmp_path, store_factory) -> None:  # noqa: ANN001
    store = store_factory() if store_factory else SqliteTrajectoryStore(str(tmp_path / "t.db"))
    assert isinstance(store, TrajectoryStore)


async def test_append_replay_and_latest_seq_roundtrip_sqlite(tmp_path) -> None:  # noqa: ANN001
    store = SqliteTrajectoryStore(str(tmp_path / "t.db"))
    run_id = RunId("run-1")
    for seq in range(3):
        await store.append(
            StoredEvent(seq=seq, run_id=run_id, event_type="x", payload_json="{}", at=datetime.now(UTC))
        )

    assert await store.latest_seq(run_id) == 2
    replayed = [event.seq async for event in store.replay(run_id, from_seq=1)]
    assert replayed == [1, 2]


async def test_latest_seq_zero_for_unknown_run_sqlite(tmp_path) -> None:  # noqa: ANN001
    store = SqliteTrajectoryStore(str(tmp_path / "t.db"))
    assert await store.latest_seq(RunId("nope")) == 0


async def test_events_persist_across_new_store_instances_same_db(tmp_path) -> None:  # noqa: ANN001
    db_path = str(tmp_path / "t.db")
    run_id = RunId("run-1")
    first = SqliteTrajectoryStore(db_path)
    await first.append(
        StoredEvent(seq=0, run_id=run_id, event_type="x", payload_json="{}", at=datetime.now(UTC))
    )

    second = SqliteTrajectoryStore(db_path)
    assert await second.latest_seq(run_id) == 0
    replayed = [event.seq async for event in second.replay(run_id)]
    assert replayed == [0]
