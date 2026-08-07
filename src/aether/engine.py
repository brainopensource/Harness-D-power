"""Headless engine API (TASK-022) — the one entrypoint every client (TUI,
CLI, CI, a future GUI) consumes with no privileged access (spec.md §8).

Wires composition (real adapters + `Dispatcher`), the topology validator, the
event bus, and the executor, and exposes one `async def run(...) ->
RunResult`. Not itself a port — this is the M1a walking skeleton's assembly
root; `src/aether/composition.py` is the wiring root it calls into.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from aether.adapters.model_provider.openai_compatible import OpenAICompatibleProvider
from aether.adapters.tools.builtin import BuiltinToolRegistry
from aether.adapters.trajectory_store.sqlite import SqliteTrajectoryStore
from aether.adapters.workspace.git_cli import GitCliWorkspace, GitCliWorktreeManager
from aether.composition import build_dispatcher
from aether.domain.events import RunCompleted, RunStarted
from aether.domain.gate import GateReport
from aether.domain.ids import Frozen, RunId
from aether.domain.task import Task
from aether.kernel.bus import EventBus
from aether.kernel.governor import ResourceGovernor
from aether.measurement.evaluator import RealEvaluator
from aether.ports.evaluator import EvalSpec
from aether.ports.trajectory_store import StoredEvent
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.executor import WorkflowExecutor
from aether.workflow.nodes.apply import ApplyStep
from aether.workflow.nodes.evaluate import EvaluateStep
from aether.workflow.nodes.generate import GenerateStep
from aether.workflow.nodes.retrieve import RetrieveStep, TaskInput
from aether.workflow.step import WorkflowStep
from aether.workflow.validator import load_topology, validate_topology

# The M1a walking skeleton's node registry (I6 — registered at composition).
# Matches `workflows/linear_v1.yaml`'s four `kind`s.
NODE_SOCKETS: dict[str, tuple[str, str]] = {
    "retrieve": ("TaskInput", "RetrievedContext"),
    "generate": ("RetrievedContext", "GeneratedPatch"),
    "apply": ("GeneratedPatch", "AppliedPatch"),
    "evaluate": ("AppliedPatch", "GateReport"),
}


class RunResult(Frozen):
    run_id: RunId
    gate_report: GateReport


async def run(
    task: Task,
    *,
    repo_path: str,
    worktrees_root: str,
    topology_path: str,
    resolve_command: Callable[[EvalSpec], str],
    model_base_url: str = "http://localhost:11434/v1",
    model_name: str = "qwen2.5-coder-32b",
    trajectory_db_path: str = ":memory:",
    entry_file: str = "README.md",
) -> RunResult:
    run_id = RunId(f"run-{uuid4().hex[:12]}")

    workspace = GitCliWorkspace(worktrees_root)
    worktree_manager = GitCliWorktreeManager(repo_path, worktrees_root)
    tool_registry = BuiltinToolRegistry(workspace, worktrees_root)
    model_provider = OpenAICompatibleProvider(model_base_url, model_name)
    evaluator = RealEvaluator(worktrees_root, resolve_command)
    governor = ResourceGovernor()
    dispatcher = build_dispatcher(workspace, tool_registry, model_provider, evaluator, governor)
    trajectory_store = SqliteTrajectoryStore(trajectory_db_path)
    bus = EventBus()
    bus.subscribe("trajectory_store", drop_policy="never")

    topology_text = await asyncio.to_thread(Path(topology_path).read_text, encoding="utf-8")
    topology = load_topology(topology_text)
    validate_topology(topology, NODE_SOCKETS)

    worktree = await worktree_manager.create(run_id, task.base_commit)
    facade = DispatchFacade(dispatcher, run_id)
    tool_catalog = await tool_registry.catalog()

    steps: dict[str, WorkflowStep[Any, Any]] = {
        "retrieve": RetrieveStep(facade, entry_file=entry_file),
        "generate": GenerateStep(facade, model_name=model_name, tool_catalog=tool_catalog),
        "apply": ApplyStep(facade),
        "evaluate": EvaluateStep(facade),
    }
    executor = WorkflowExecutor(topology, steps, bus, governor)

    await bus.emit(RunStarted(run_id=run_id, at=datetime.now(UTC), task_id=task.task_id))
    initial = TaskInput(task=task, worktree=worktree)

    try:
        gate_report = await executor.execute(run_id, initial)
    finally:
        await _drain_to_trajectory_store(bus, trajectory_store, "trajectory_store")

    await bus.emit(RunCompleted(run_id=run_id, at=datetime.now(UTC), final_status=gate_report.status.value))
    await _drain_to_trajectory_store(bus, trajectory_store, "trajectory_store")
    bus.unsubscribe("trajectory_store")

    return RunResult(run_id=run_id, gate_report=gate_report)


async def _drain_to_trajectory_store(
    bus: EventBus, trajectory_store: SqliteTrajectoryStore, consumer_id: str
) -> None:
    events = bus.drain(consumer_id)
    if not events:
        return
    next_seq = (await trajectory_store.latest_seq(events[0].run_id)) + 1
    for offset, event in enumerate(events):
        await trajectory_store.append(
            StoredEvent(
                seq=next_seq + offset,
                run_id=event.run_id,
                event_type=event.kind,
                payload_json=event.model_dump_json(),
                at=event.at,
            )
        )


__all__ = ["NODE_SOCKETS", "RunResult", "run"]
