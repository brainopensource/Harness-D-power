"""Composition root — see docs/05-tech-stack/composition-and-configuration.md.

Single function, single place: `build_kernel(config: Config) -> Kernel`.
Constructs adapters, binds ports, and returns an immutable kernel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sagiha.adapters.memory.short_term import InMemoryMemory
from sagiha.adapters.model.cassette import CassetteModelProvider
from sagiha.adapters.tools.builtins import register_builtin_tools
from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.domain.config import Config
from sagiha.domain.content import ToolSchema
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
    model_provider: ModelProvider
    policy_engine: PolicyEngine
    resource_governor: ResourceGovernor
    tool_registry: ToolRegistry
    trajectory_store: TrajectoryStore
    memory: Memory
    workspace: LocalWorkspace
    bus: EventBus = field(default_factory=EventBus)
    indexer: Indexer | None = None
    code_graph: CodeGraph | None = None
    lsp_adapter: LSPAdapter | None = None
    worktree_manager: WorktreeManager | None = None
    evaluator: Evaluator | None = None
    tool_schemas: tuple[ToolSchema, ...] = ()


def build_kernel(
    config: Config,
    *,
    cassette_path: str | None = None,
) -> Kernel:
    """Builds and wires the Sprint 3a kernel from configuration.

    Adapter selection, capability instantiation, and port binding happen exactly once here.
    Misconfiguration fails at composition (D3 / D14).
    """
    trajectory_store = SQLiteTrajectoryStore(config.telemetry.trajectory_db)
    policy_engine = DefaultPolicyEngine(always_gate=config.autonomy.always_gate)
    resource_governor = DefaultResourceGovernor(
        max_spend_usd_per_run=config.governor.max_spend_usd_per_run,
        max_concurrent_sandboxes=config.governor.max_concurrent_sandboxes,
    )
    tool_registry = DefaultToolRegistry()
    memory = InMemoryMemory()
    workspace = LocalWorkspace(config.workspace.root)
    schemas = register_builtin_tools(tool_registry, workspace)
    for tool_name, schema in schemas.items():
        policy_engine.register_tool_schema(tool_name, schema)

    tool_schemas = (
        ToolSchema(
            name="read_file",
            description="Read a text file from the workspace",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        ),
        ToolSchema(
            name="list_dir",
            description="List directory entries",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        ),
        ToolSchema(
            name="grep",
            description="Search file contents by regex",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern"],
            },
        ),
        ToolSchema(
            name="apply_edit",
            description="Apply a search/replace edit to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        ),
        ToolSchema(
            name="run_command",
            description="Run a command in the workspace",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["command"],
            },
        ),
    )

    path = cassette_path or ".sagiha/cassettes/default.json"
    mode = config.model.mode

    if mode == "replay":
        if not Path(path).exists():
            raise FileNotFoundError(
                f"model.mode=replay requires cassette at {path}"
            )
        model_provider: ModelProvider = CassetteModelProvider(
            cassette_path=path, mode="replay"
        )
    elif mode == "record":
        # Record requires an inner live provider — Sprint 3a uses a passthrough stub
        # only when explicitly testing; otherwise fail closed without an inner.
        raise RuntimeError(
            "model.mode=record requires an inner live provider; "
            "use replay with a committed cassette or bind a live adapter"
        )
    elif mode == "live":
        # OpenAI-compatible live adapter lands with optional extras; fail closed for now
        # unless a cassette path is explicitly provided for offline demo.
        if cassette_path and Path(path).exists():
            model_provider = CassetteModelProvider(cassette_path=path, mode="replay")
        else:
            raise RuntimeError(
                "model.mode=live requires a provider adapter (OpenAI-compatible) — "
                "not bound in this build; use mode=replay with a cassette"
            )
    else:
        raise RuntimeError(f"Unknown model.mode: {mode}")

    bus = EventBus()
    bus.subscribe_observer(trajectory_store.append_event)

    return Kernel(
        config=config,
        model_provider=model_provider,
        memory=memory,
        tool_registry=tool_registry,
        policy_engine=policy_engine,
        resource_governor=resource_governor,
        trajectory_store=trajectory_store,
        workspace=workspace,
        bus=bus,
        tool_schemas=tool_schemas,
    )
