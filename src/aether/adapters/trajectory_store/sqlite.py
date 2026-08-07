"""SQLite TrajectoryStore adapter (TASK-026) — durable append-only event log.

First real adapter for the `TrajectoryStore` port (ADR-0005 rev. 2). WAL mode,
stdlib sqlite3, no ORM. Blocking calls are pushed to a thread via
`asyncio.to_thread` so this async port never blocks the event loop.
"""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import AsyncIterator
from datetime import datetime

from aether.domain.ids import RunId
from aether.ports.trajectory_store import StoredEvent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    at TEXT NOT NULL,
    PRIMARY KEY (run_id, seq)
)
"""


class SqliteTrajectoryStore:
    """One append-only table keyed by `(run_id, seq)`. `db_path` may be `:memory:`
    for tests, but `:memory:` connections are per-connection — callers wanting
    an in-process durable double should prefer `InMemoryTrajectoryStore`
    (tests/aether/mocks.py) instead."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        conn = self._connect()
        try:
            conn.execute(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    async def append(self, event: StoredEvent) -> None:
        def _write() -> None:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO events (run_id, seq, event_type, payload_json, at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (event.run_id, event.seq, event.event_type, event.payload_json, event.at.isoformat()),
                )
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_write)

    async def replay(self, run_id: RunId, from_seq: int = 0) -> AsyncIterator[StoredEvent]:
        def _read() -> list[StoredEvent]:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT seq, run_id, event_type, payload_json, at FROM events "
                    "WHERE run_id = ? AND seq >= ? ORDER BY seq ASC",
                    (run_id, from_seq),
                ).fetchall()
            finally:
                conn.close()
            return [
                StoredEvent(
                    seq=seq,
                    run_id=RunId(row_run_id),
                    event_type=event_type,
                    payload_json=payload_json,
                    at=datetime.fromisoformat(at),
                )
                for seq, row_run_id, event_type, payload_json, at in rows
            ]

        for event in await asyncio.to_thread(_read):
            yield event

    async def latest_seq(self, run_id: RunId) -> int:
        def _read() -> int:
            conn = self._connect()
            try:
                row = conn.execute("SELECT MAX(seq) FROM events WHERE run_id = ?", (run_id,)).fetchone()
            finally:
                conn.close()
            return row[0] if row and row[0] is not None else 0

        return await asyncio.to_thread(_read)
