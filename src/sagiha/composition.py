"""Composition root — see docs/05-tech-stack/composition-and-configuration.md.

Single function, single place: `build_kernel(config: Config) -> Kernel`.
Constructs adapters, binds ports, and returns an immutable kernel.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sagiha.adapters.memory.short_term import InMemoryMemory
from sagiha.adapters.model.cassette import CassetteModelProvider
from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.domain.config import Config
from sagiha.kernel.bus import EventBus
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine
from sagiha.ports.code_graph import CodeGraph
from sagiha.ports.evaluator import Evaluator
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.indexer import Indexer
from sagiha.ports.lsp import LSPAdapter
from sagiha.ports.memory import Memory
from sagiha.ports.model import ModelProvider
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry
from sagiha.ports.trajectory import TrajectoryStore
from sagiha.ports.workspace import WorktreeManager


@dataclass(frozen=True)
class Kernel:
    """Immutable runtime kernel instance holding bound ports and configuration."""

    config: Config
    model_provider: ModelProvider | None = None
    memory: Memory | None = None
    indexer: Indexer | None = None
    code_graph: CodeGraph | None = None
    lsp_adapter: LSPAdapter | None = None
    worktree_manager: WorktreeManager | None = None
    tool_registry: ToolRegistry | None = None
    policy_engine: PolicyEngine | None = None
    resource_governor: ResourceGovernor | None = None
    trajectory_store: TrajectoryStore | None = None
    evaluator: Evaluator | None = None
    bus: EventBus = field(default_factory=EventBus)


def build_kernel(config: Config) -> Kernel:
    """Builds and wires the Day-Zero kernel from configuration.

    Adapter selection, capability instantiation, and port binding happen exactly once here.
    """
    trajectory_store = SQLiteTrajectoryStore(config.telemetry.trajectory_db)
    policy_engine = DefaultPolicyEngine(always_gate=config.autonomy.always_gate)
    resource_governor = DefaultResourceGovernor(
        max_spend_usd_per_run=config.governor.max_spend_usd_per_run,
        max_concurrent_sandboxes=config.governor.max_concurrent_sandboxes,
    )
    tool_registry = DefaultToolRegistry()
    memory = InMemoryMemory()

    model_provider: ModelProvider
    if config.model.mode == "replay":
        model_provider = CassetteModelProvider(
            cassette_path=".sagiha/cassettes/default.json", mode="replay"
        )
    else:
        # Default placeholder cassette adapter for local/test execution
        model_provider = CassetteModelProvider(
            cassette_path=".sagiha/cassettes/default.json", mode="replay"
        )

    bus = EventBus()
    # Subscribe TrajectoryStore event observer to bus
    bus.subscribe_observer(trajectory_store.append_event)

    return Kernel(
        config=config,
        model_provider=model_provider,
        memory=memory,
        tool_registry=tool_registry,
        policy_engine=policy_engine,
        resource_governor=resource_governor,
        trajectory_store=trajectory_store,
        bus=bus,
    )
