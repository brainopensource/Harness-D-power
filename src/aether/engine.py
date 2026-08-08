"""Headless engine API (TASK-022) — the one entrypoint every client (TUI,
CLI, CI, a future GUI) consumes with no privileged access (spec.md §8).

Wires composition (real adapters + `Dispatcher`), the topology validator, the
event bus, and the executor, and exposes one `async def run(...) ->
RunResult`. Not itself a port — this is the M1a walking skeleton's assembly
root; `src/aether/composition.py` is the wiring root it calls into.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from aether.adapters.model_provider.openai_compatible import OpenAICompatibleProvider
from aether.adapters.sandbox.podman import ContainerSandbox
from aether.adapters.tools.builtin import BuiltinToolRegistry
from aether.adapters.trajectory_store.sqlite import SqliteTrajectoryStore
from aether.adapters.workspace.git_cli import GitCliWorkspace, GitCliWorktreeManager
from aether.composition import build_dispatcher
from aether.domain.budget import BudgetDims
from aether.domain.events import RunCompleted, RunStarted
from aether.domain.gate import GateReport
from aether.domain.ids import Frozen, RunId
from aether.domain.task import Task
from aether.domain.tools import ToolSpec
from aether.kernel.bus import EventBus
from aether.kernel.governor import ResourceGovernor
from aether.measurement.evaluator import RealEvaluator
from aether.ports.evaluator import EvalSpec
from aether.ports.trajectory_store import StoredEvent
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.edit_format import DEFAULT_EDIT_FORMAT
from aether.workflow.executor import WorkflowExecutor
from aether.workflow.nodes.apply import ApplyStep
from aether.workflow.nodes.architect import ArchitectStep, ReflectorStep
from aether.workflow.nodes.evaluate import EvaluatedCandidate, EvaluateStep
from aether.workflow.nodes.generate import GenerateStep
from aether.workflow.nodes.repair import RepairStep
from aether.workflow.nodes.retrieve import RetrieveStep, TaskInput
from aether.workflow.step import StepFactory, WorkflowStep
from aether.workflow.validator import load_topology, validate_topology

# The M1a walking skeleton's node registry (I6 — registered at composition).
# Matches `workflows/linear_v1.yaml`'s four `kind`s.
NODE_SOCKETS: dict[str, tuple[str, str]] = {
    "retrieve": ("TaskInput", "RetrievedContext"),
    "architect": ("RetrievedContext", "RetrievedContext"),
    "generate": ("RetrievedContext", "GeneratedPatch"),
    "apply": ("GeneratedPatch", "AppliedPatch"),
    "evaluate": ("AppliedPatch", "EvaluatedCandidate"),
    "reflector": ("EvaluatedCandidate", "EvaluatedCandidate"),
    # The repair edge closes the loop: evaluate's output is repair's input, and
    # repair's output re-enters apply (TASK-023, workflows/linear_repair_v1.yaml).
    "repair": ("EvaluatedCandidate", "GeneratedPatch"),
}


def build_step_registry(
    facade: DispatchFacade,
    *,
    model_name: str,
    tool_catalog: tuple[ToolSpec, ...] = (),
    default_entry_files: tuple[str, ...] = ("README.md",),
) -> dict[str, StepFactory]:
    """kind -> factory. **The swap point of the whole system.**

    A topology names kinds; this maps each kind to the implementation that
    serves it and hands that implementation the node's own `params`. Pointing
    `generate` at a different model, `apply` at a different edit format, or any
    kind at an entirely different library is an entry here plus a line of YAML
    — no caller changes, which is what ADR-0014's "topologies are data" buys.

    Frozen at composition (I6): the registry is built once and never mutated at
    runtime.
    """

    def retrieve(params: Mapping[str, Any]) -> WorkflowStep[Any, Any]:
        entry_files = tuple(params.get("entry_files") or default_entry_files)
        return RetrieveStep(facade, entry_files=entry_files, max_bytes=int(params.get("max_bytes", 20_000)))

    def generate(params: Mapping[str, Any]) -> WorkflowStep[Any, Any]:
        return GenerateStep(
            facade,
            model_name=str(params.get("model", model_name)),
            tool_catalog=tool_catalog if params.get("tools", False) else (),
            max_tokens=int(params.get("max_tokens", 4096)),
            edit_format=str(params.get("edit_format", DEFAULT_EDIT_FORMAT)),
        )

    def apply_step(params: Mapping[str, Any]) -> WorkflowStep[Any, Any]:
        return ApplyStep(facade, edit_format=str(params.get("edit_format", DEFAULT_EDIT_FORMAT)))

    def evaluate(params: Mapping[str, Any]) -> WorkflowStep[Any, Any]:
        return EvaluateStep(facade, timeout_ms=int(params.get("timeout_ms", 60_000)))

    def repair(params: Mapping[str, Any]) -> WorkflowStep[Any, Any]:
        return RepairStep(
            facade,
            model_name=str(params.get("model", model_name)),
            max_tokens=int(params.get("max_tokens", 4096)),
            edit_format=str(params.get("edit_format", DEFAULT_EDIT_FORMAT)),
            entry_files=tuple(params.get("entry_files") or default_entry_files),
        )

    def architect(params: Mapping[str, Any]) -> WorkflowStep[Any, Any]:
        return ArchitectStep(
            facade,
            model_name=str(params.get("model", model_name)),
            max_tokens=int(params.get("max_tokens", 1024)),
        )

    def reflector(params: Mapping[str, Any]) -> WorkflowStep[Any, Any]:
        return ReflectorStep(
            facade,
            model_name=str(params.get("model", model_name)),
            max_tokens=int(params.get("max_tokens", 1024)),
        )

    return {
        "retrieve": retrieve,
        "architect": architect,
        "generate": generate,
        "apply": apply_step,
        "evaluate": evaluate,
        "reflector": reflector,
        "repair": repair,
    }


class RunResult(Frozen):
    run_id: RunId
    gate_report: GateReport
    # What the run actually spent, read from the governor's ledger rather than
    # estimated afterwards. Cost per resolved task is a mandatory report column
    # (ADR-0003 rev. 2 §4), and a number reconstructed after the fact is the
    # after-the-fact accounting `spec.md` §5 exists to make unrepresentable.
    usage: BudgetDims = BudgetDims()


async def run(
    task: Task,
    *,
    repo_path: str,
    worktrees_root: str,
    topology_path: str,
    resolve_command: Callable[[EvalSpec], str],
    model_base_url: str = "http://localhost:11434/v1",
    model_name: str = "qwen2.5-coder-32b",
    model_api_key: str | None = None,
    api_key: str | None = None,
    trajectory_db_path: str = ":memory:",
    entry_file: str = "README.md",
    sandbox_runtime: str | None = None,
    usd_micros_ceiling: int | None = None,
    entry_files: tuple[str, ...] | None = None,
) -> RunResult:
    """`sandbox_runtime` ("podman" | "docker") puts the evaluator inside the B3
    container (TASK-016). Left None the judge runs uncontained — fine for the
    smoke suite, never valid for a published number (measurement.md §2 B3).

    `usd_micros_ceiling` seeds a hard spend ceiling for this run; effects past
    it are refused at the choke point. `entry_files` overrides what the
    retrieve node reads when the topology does not name files itself.
    """
    run_id = RunId(f"run-{uuid4().hex[:12]}")

    workspace = GitCliWorkspace(worktrees_root)
    worktree_manager = GitCliWorktreeManager(repo_path, worktrees_root)
    tool_registry = BuiltinToolRegistry(workspace, worktrees_root)
    resolved_api_key = model_api_key or api_key
    model_provider = OpenAICompatibleProvider(model_base_url, model_name, api_key=resolved_api_key)
    sandbox = ContainerSandbox(sandbox_runtime) if sandbox_runtime is not None else None
    evaluator = RealEvaluator(worktrees_root, resolve_command, sandbox=sandbox)
    # The bus is constructed first: the governor and the dispatcher both emit
    # to it, and a component that takes it later cannot emit at all.
    bus = EventBus()
    bus.subscribe("trajectory_store", drop_policy="never")
    governor = ResourceGovernor(bus)
    if usd_micros_ceiling is not None:
        # A real ceiling, not a comment: the dispatcher refuses any effect the
        # governor will not fund, so the run stops itself rather than relying
        # on a caller to notice (spec.md §5, and A4 made `usd_micros` real).
        governor.seed_run_budget(run_id, BudgetDims(usd_micros=usd_micros_ceiling))
    dispatcher = build_dispatcher(
        workspace, tool_registry, model_provider, evaluator, governor, model_base_url, bus
    )
    trajectory_store = SqliteTrajectoryStore(trajectory_db_path)

    topology_text = await asyncio.to_thread(Path(topology_path).read_text, encoding="utf-8")
    topology = load_topology(topology_text)
    validate_topology(topology, NODE_SOCKETS)

    worktree = await worktree_manager.create(run_id, task.base_commit)
    facade = DispatchFacade(dispatcher, run_id)
    tool_catalog = await tool_registry.catalog()

    registry = build_step_registry(
        facade,
        model_name=model_name,
        tool_catalog=tool_catalog,
        default_entry_files=entry_files or (entry_file,),
    )
    executor = WorkflowExecutor(topology, registry, bus, governor)

    await bus.emit(RunStarted(run_id=run_id, at=datetime.now(UTC), task_id=task.task_id))
    initial = TaskInput(task=task, worktree=worktree)

    try:
        outcome = await executor.execute(run_id, initial)
        gate_report = outcome.report if isinstance(outcome, EvaluatedCandidate) else outcome
    finally:
        await _drain_to_trajectory_store(bus, trajectory_store, "trajectory_store")

    usage = await governor.spent(run_id)
    await bus.emit(RunCompleted(run_id=run_id, at=datetime.now(UTC), final_status=gate_report.status.value))
    await _drain_to_trajectory_store(bus, trajectory_store, "trajectory_store")
    bus.unsubscribe("trajectory_store")

    return RunResult(run_id=run_id, gate_report=gate_report, usage=usage)


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
