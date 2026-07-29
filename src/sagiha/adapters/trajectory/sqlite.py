"""Append-only SQLite-WAL TrajectoryStore implementation — see docs/05-tech-stack/control-plane-python.md."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from anyio.to_thread import run_sync

from sagiha.domain.events import Event
from sagiha.domain.trajectory import TrajectoryStep


def _init_db(db_path: str) -> None:
    path = Path(db_path)
    if path.parent and not path.parent.exists():
        os.makedirs(path.parent, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")

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
        conn.commit()


class SQLiteTrajectoryStore:
    """Append-only TrajectoryStore backed by SQLite in WAL mode."""

    def __init__(self, db_path: str = ".sagiha/trajectories.db") -> None:
        self._db_path = db_path
        _init_db(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")
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
                return [Event.model_validate_json(row[0]) for row in rows]

        return await run_sync(_sync_fetch)
