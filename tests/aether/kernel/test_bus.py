"""EventBus (TASK-022): drop_oldest is lossy under backpressure by design;
"never" consumers (TrajectoryStore, the harvester) must receive everything."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from aether.domain.events import NodeStarted
from aether.domain.ids import NodeId, RunId
from aether.kernel.bus import EventBus


def _event(i: int) -> NodeStarted:
    return NodeStarted(run_id=RunId("r1"), at=datetime.now(UTC), node_id=NodeId(f"n{i}"))


async def _drain(iterator, count: int) -> list:  # noqa: ANN001
    items = []
    for _ in range(count):
        items.append(await asyncio.wait_for(anext(iterator), timeout=1.0))
    return items


async def test_never_policy_consumer_receives_every_event() -> None:
    bus = EventBus()
    iterator = bus.subscribe("trajectory_store", drop_policy="never")

    for i in range(50):
        await bus.emit(_event(i))

    received = await _drain(iterator, 50)
    assert [e.node_id for e in received] == [f"n{i}" for i in range(50)]


async def test_drop_oldest_consumer_loses_earliest_events_under_backpressure() -> None:
    bus = EventBus()
    iterator = bus.subscribe("tui", drop_policy="drop_oldest", maxsize=5)

    for i in range(20):
        await bus.emit(_event(i))

    received = await _drain(iterator, 5)
    # The 5 most recent survive; the earliest 15 were dropped to make room.
    assert [e.node_id for e in received] == [f"n{i}" for i in range(15, 20)]


async def test_multiple_consumers_are_independent() -> None:
    bus = EventBus()
    never_iter = bus.subscribe("store", drop_policy="never")
    drop_iter = bus.subscribe("tui", drop_policy="drop_oldest", maxsize=2)

    for i in range(3):
        await bus.emit(_event(i))

    never_received = await _drain(never_iter, 3)
    drop_received = await _drain(drop_iter, 2)

    assert len(never_received) == 3
    assert [e.node_id for e in drop_received] == ["n1", "n2"]


async def test_unsubscribe_stops_future_delivery() -> None:
    bus = EventBus()
    bus.subscribe("store", drop_policy="never")
    bus.unsubscribe("store")

    await bus.emit(_event(0))  # must not raise despite no subscribers
