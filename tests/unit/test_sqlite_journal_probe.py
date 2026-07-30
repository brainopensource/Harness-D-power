"""NFS / non-local filesystem SQLite journal mode probe (Sprint 3b).

WAL relies on shared memory and, with mmap enabled, on memory-mapped I/O — both can SIGBUS a
long unattended run on a network filesystem. `_configure_connection` disables mmap
unconditionally and probes whether SQLite actually granted WAL rather than trusting the request,
falling back to DELETE + synchronous=FULL when it didn't.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore, _configure_connection


def test_configure_connection_grants_wal_on_a_normal_local_file() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "t.db")
        conn = sqlite3.connect(db_path)
        try:
            mode = _configure_connection(conn, db_path)
            assert mode == "wal"
            assert conn.execute("PRAGMA journal_mode;").fetchone()[0].lower() == "wal"
        finally:
            conn.close()


def test_configure_connection_falls_back_when_wal_cannot_be_granted() -> None:
    # sqlite3 never grants WAL for an in-memory database — journal_mode stays "memory"
    # regardless of what is requested. This exercises the exact fallback path a network
    # filesystem that silently rejects WAL would take, without needing to mount one.
    conn = sqlite3.connect(":memory:")
    try:
        mode = _configure_connection(conn, ":memory:")
        assert mode == "delete"
        assert conn.execute("PRAGMA journal_mode;").fetchone()[0].lower() == "memory"
    finally:
        conn.close()


def test_configure_connection_always_disables_mmap() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "t.db")
        conn = sqlite3.connect(db_path)
        try:
            _configure_connection(conn, db_path)
            assert conn.execute("PRAGMA mmap_size;").fetchone()[0] == 0
        finally:
            conn.close()


async def test_trajectory_store_still_round_trips_after_probe(tmp_path: Path) -> None:
    from sagiha.domain.events import Event

    store = SQLiteTrajectoryStore(db_path=str(tmp_path / "traj.db"))
    await store.append_event(Event(event="probe.smoke", run_id="run-probe"))
    events = await store.events_for_run("run-probe")
    assert len(events) == 1
    assert events[0].event == "probe.smoke"
