"""Append-only SQLite-WAL TrajectoryStore implementation — see docs/05-tech-stack/control-plane-python.md."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path

from anyio.to_thread import run_sync

from sagiha.domain.events import ALL_EVENTS, Event
from sagiha.domain.trajectory import RunRecord, TrajectoryStep
from sagiha.domain.upcasters import upcast_event

logger = logging.getLogger(__name__)

_EVENT_BY_NAME: dict[str, type[Event]] = {
    cls.model_fields["event"].default: cls  # type: ignore[misc]
    for cls in ALL_EVENTS
}


def _configure_connection(conn: sqlite3.Connection, db_path: str) -> str:
    """Probe and configure journal mode + mmap for the connection's filesystem.

    WAL relies on shared-memory (`-shm`) and, if `mmap_size` is nonzero, on memory-mapped I/O.
    Both can SIGBUS a long unattended run on a non-local filesystem (NFS/SMB) — a crash Python
    cannot catch or recover from. Two mitigations:

    1. `mmap_size = 0` unconditionally disables memory-mapped I/O, removing that vector
       regardless of journal mode.
    2. SQLite does not raise when it cannot actually grant WAL on an incompatible VFS — it
       silently falls back and `PRAGMA journal_mode` returns the mode it actually applied. This
       probes that return value rather than trusting the request, and falls back explicitly to
       `DELETE` + `synchronous=FULL` (durable, journal-file-based, no shared memory) when WAL was
       not granted, so callers never believe they have WAL guarantees they don't.
    """
    conn.execute("PRAGMA mmap_size = 0;")
    cursor = conn.execute("PRAGMA journal_mode = WAL;")
    row = cursor.fetchone()
    granted = str(row[0]).lower() if row else "unknown"
    if granted != "wal":
        logger.warning(
            "SQLite could not grant WAL journal mode for %s (got %r instead) — likely a "
            "non-local filesystem; falling back to DELETE journal mode with synchronous=FULL",
            db_path,
            granted,
        )
        conn.execute("PRAGMA journal_mode = DELETE;")
        conn.execute("PRAGMA synchronous = FULL;")
        granted = "delete"
    else:
        conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return granted


def _init_db(db_path: str) -> None:
    path = Path(db_path)
    if path.parent and not path.parent.exists():
        os.makedirs(path.parent, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        _configure_connection(conn, db_path)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS steps (
                run_id TEXT NOT NULL,
                branch_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                parent_seq TEXT,
                step_json TEXT NOT NULL,
                PRIMARY KEY (run_id, branch_id, seq)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_json TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                task_json TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.commit()


def _deserialize_event(raw_json: str) -> Event:
    data = upcast_event(json.loads(raw_json))
    event_name = data.get("event")
    cls = _EVENT_BY_NAME.get(event_name) if isinstance(event_name, str) else None
    if cls is None:
        return Event.model_validate(data)
    return cls.model_validate(data)


class SQLiteTrajectoryStore:
    """Append-only TrajectoryStore backed by SQLite in WAL mode."""

    def __init__(self, db_path: str = ".sagiha/trajectories.db") -> None:
        self._db_path = db_path
        _init_db(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        _configure_connection(conn, self._db_path)
        return conn

    async def append_step(self, step: TrajectoryStep) -> None:
        def _sync_append() -> None:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO steps (run_id, branch_id, seq, parent_seq, step_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        step.step_id.run_id,
                        step.step_id.branch_id,
                        step.step_id.seq,
                        step.step_id.parent,
                        step.model_dump_json(),
                    ),
                )
                conn.commit()

        await run_sync(_sync_append)

    async def append_event(self, event: Event) -> None:
        def _sync_append() -> None:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO events (run_id, event_type, timestamp, event_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        event.run_id,
                        event.event,
                        event.timestamp.isoformat(),
                        event.model_dump_json(),
                    ),
                )
                conn.commit()

        await run_sync(_sync_append)

    async def steps_for_run(self, run_id: str) -> list[TrajectoryStep]:
        def _sync_fetch() -> list[TrajectoryStep]:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT step_json FROM steps
                    WHERE run_id = ?
                    ORDER BY seq ASC
                    """,
                    (run_id,),
                )
                rows = cursor.fetchall()
                return [TrajectoryStep.model_validate_json(row[0]) for row in rows]

        return await run_sync(_sync_fetch)

    async def events_for_run(self, run_id: str) -> list[Event]:
        def _sync_fetch() -> list[Event]:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT event_json FROM events
                    WHERE run_id = ?
                    ORDER BY rowid ASC
                    """,
                    (run_id,),
                )
                rows = cursor.fetchall()
                return [_deserialize_event(row[0]) for row in rows]

        return await run_sync(_sync_fetch)

    async def upsert_run(self, record: RunRecord) -> None:
        def _sync_upsert() -> None:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO runs (run_id, task_json, status, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        task_json = excluded.task_json,
                        status = excluded.status,
                        updated_at = excluded.updated_at
                    """,
                    (
                        record.run_id,
                        record.task.model_dump_json(),
                        record.status,
                        record.updated_at.isoformat(),
                    ),
                )
                conn.commit()

        await run_sync(_sync_upsert)

    async def get_run(self, run_id: str) -> RunRecord | None:
        def _sync_fetch() -> RunRecord | None:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT task_json, status, updated_at FROM runs WHERE run_id = ?",
                    (run_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                task_json, status, updated_at = row
                return RunRecord.model_validate(
                    {
                        "run_id": run_id,
                        "task": json.loads(task_json),
                        "status": status,
                        "updated_at": updated_at,
                    }
                )

        return await run_sync(_sync_fetch)
