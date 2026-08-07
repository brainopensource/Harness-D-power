"""The in-memory mocks in tests/aether/mocks.py must actually satisfy their Protocols."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.aether.mocks import (
    FakeEvaluator,
    FakeModelProvider,
    FixedCatalogToolRegistry,
    InMemoryIndexer,
    InMemoryResourceGovernor,
    InMemoryTrajectoryStore,
    InMemoryWorkspace,
    InMemoryWorktreeManager,
)

from aether.domain.budget import Actuals, BudgetDims
from aether.domain.ids import RunId, TaskId
from aether.domain.model_io import ModelMessage, ModelRequest, StopEvent
from aether.domain.workspace import WorktreeRef
from aether.ports.evaluator import Evaluator
from aether.ports.indexer import Indexer
from aether.ports.model_provider import ModelProvider
from aether.ports.resource_governor import ResourceGovernor
from aether.ports.tool_registry import ToolRegistry
from aether.ports.trajectory_store import StoredEvent, TrajectoryStore
from aether.ports.workspace import Workspace, WorktreeManager


@pytest.mark.parametrize(
    "instance,protocol",
    [
        (FakeModelProvider(), ModelProvider),
        (InMemoryWorkspace(), Workspace),
        (InMemoryWorktreeManager(), WorktreeManager),
        (FixedCatalogToolRegistry(), ToolRegistry),
        (InMemoryIndexer(), Indexer),
        (InMemoryResourceGovernor(), ResourceGovernor),
        (InMemoryTrajectoryStore(), TrajectoryStore),
        (FakeEvaluator(), Evaluator),
    ],
)
def test_mock_satisfies_its_protocol(instance: object, protocol: type) -> None:
    assert isinstance(instance, protocol)


async def test_fake_model_provider_streams_to_a_stop_event() -> None:
    provider = FakeModelProvider()
    request = ModelRequest(model="m", messages=(ModelMessage(role="user", spans=()),), max_tokens=10)
    events = [event async for event in provider.stream(request)]
    assert isinstance(events[-1], StopEvent)


async def test_in_memory_resource_governor_reserve_commit_release() -> None:
    governor = InMemoryResourceGovernor()
    run_id = RunId("run-1")
    lease = await governor.reserve(run_id, BudgetDims(usd_micros=100))
    assert not hasattr(lease, "shortfall")  # i.e. a real Lease, not ReservationDenied
    await governor.commit(lease.lease_id, Actuals(dims=BudgetDims(usd_micros=40)))  # type: ignore[union-attr]
    remaining = await governor.remaining(run_id)
    assert remaining.usd_micros == 40


async def test_in_memory_trajectory_store_replay_filters_by_seq() -> None:
    store = InMemoryTrajectoryStore()
    run_id = RunId("run-1")
    for seq in range(3):
        await store.append(
            StoredEvent(seq=seq, run_id=run_id, event_type="x", payload_json="{}", at=datetime.now(UTC))
        )
    replayed = [event.seq async for event in store.replay(run_id, from_seq=1)]
    assert replayed == [1, 2]
    assert await store.latest_seq(run_id) == 2


async def test_fake_evaluator_passes() -> None:
    from aether.ports.evaluator import EvalSpec

    evaluator = FakeEvaluator()
    report = await evaluator.evaluate(
        EvalSpec(
            task_id=TaskId("t1"),
            worktree=WorktreeRef(worktree_id="w1", run_id=RunId("r1"), base_commit="a" * 40, abs_hint="/x"),
            image_digest="sha256:" + "a" * 64,
            test_command_hash="sha256:" + "b" * 64,
            timeout_ms=1000,
        )
    )
    assert report.status.value == "passed"
