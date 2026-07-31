"""Composition root — see docs/05-tech-stack/composition-and-configuration.md.

Single function, single place: `build_kernel(config: Config) -> Kernel`.
Constructs adapters, binds ports, and returns an immutable kernel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sagiha.adapters.memory.short_term import InMemoryMemory
from sagiha.adapters.model.cassette import CassetteModelProvider
from sagiha.adapters.tools.builtins import BUILTIN_SCHEMAS, TOOL_DESCRIPTIONS, register_builtin_tools
from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.domain.config import Config
from sagiha.domain.content import ToolSchema
from sagiha.kernel.bus import EventBus
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine
from sagiha.outer_loop.evaluator import GateEvaluator
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
from sagiha.ports.workspace import Workspace, WorktreeManager


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
    workspace: Workspace
    bus: EventBus = field(default_factory=EventBus)
    indexer: Indexer | None = None
    code_graph: CodeGraph | None = None
    lsp_adapter: LSPAdapter | None = None
    worktree_manager: WorktreeManager | None = None
    evaluator: Evaluator | None = None
    tool_schemas: tuple[ToolSchema, ...] = ()


def load_env_file(path: str | Path = ".env") -> dict[str, str]:
    """Parse key-value environment variables from a .env file if present."""
    env_vars: dict[str, str] = {}
    p = Path(path)
    if not p.is_file():
        return env_vars
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'\"")
        if key:
            env_vars[key] = val
    return env_vars


def build_kernel(
    config: Config,
    *,
    cassette_path: str | None = None,
    tier: str | None = None,
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
        max_wall_clock_s=config.governor.max_wall_clock_s,
        max_steps_per_run=config.governor.max_steps_per_run,
    )
    default_registry = DefaultToolRegistry()
    tool_registry: ToolRegistry = default_registry
    memory = InMemoryMemory()
    workspace = LocalWorkspace(config.workspace.root)
    schemas = register_builtin_tools(default_registry, workspace)
    for tool_name, schema in schemas.items():
        policy_engine.register_tool_schema(tool_name, schema)

    # Derived from BUILTIN_SCHEMAS in a fixed sorted() order — the manually-duplicated
    # per-tool ToolSchema literals this replaced could (and once did) drift from the
    # schemas actually registered on the tool registry.
    tool_schemas = tuple(
        ToolSchema(name=name, description=TOOL_DESCRIPTIONS[name], parameters=BUILTIN_SCHEMAS[name])
        for name in sorted(BUILTIN_SCHEMAS)
    )

    path = cassette_path or ".sagiha/cassettes/default.json"
    mode = config.model.mode
    bus = EventBus()

    def _adapter_for_tier(tier_cfg: object, *, api_key: str | None) -> list[tuple[str, ModelProvider]]:
        """In-tier model chain: primary + same-endpoint fallbacks only."""
        from sagiha.adapters.model.openai import OpenAIModelAdapter
        from sagiha.domain.config import ModelTierConfig

        assert isinstance(tier_cfg, ModelTierConfig)
        base_url = tier_cfg.base_url or "http://localhost:11434/v1"
        models = [tier_cfg.model, *tier_cfg.fallbacks]
        out: list[tuple[str, ModelProvider]] = []
        for m in models:
            out.append(
                (
                    f"{tier_cfg.provider}:{m}",
                    OpenAIModelAdapter(model_name=m, base_url=base_url, api_key=api_key),
                )
            )
        return out

    def _create_live_model_provider() -> ModelProvider:
        import os

        from sagiha.adapters.model.fallback import FallbackModelAdapter
        from sagiha.domain.config import ModelTierConfig

        # Role-level binding: execution role → primary tier; ModelConfig.fallback → secondary tier.
        role_tier_name = tier or config.model.roles.get("execution") or config.model.active_tier
        primary_cfg = (
            config.model.tiers.get(role_tier_name)
            or config.model.tiers.get("tier0")
            or config.model.tiers.get("local")
        )
        if primary_cfg is None:
            raise RuntimeError(f"No model tier resolved for role tier '{role_tier_name}'")

        def _api_key_for(tier_cfg: ModelTierConfig) -> str | None:
            api_key_env = tier_cfg.api_key_env
            api_key = os.environ.get(api_key_env) if api_key_env else None
            if not api_key and api_key_env:
                env_vars = load_env_file(Path(config.workspace.root) / ".env")
                if not env_vars:
                    env_vars = load_env_file(".env")
                api_key = env_vars.get(api_key_env)
            return api_key

        labeled = _adapter_for_tier(primary_cfg, api_key=_api_key_for(primary_cfg))

        fallback_tier_name = config.model.fallback
        if fallback_tier_name and fallback_tier_name != role_tier_name:
            fb_cfg = config.model.tiers.get(fallback_tier_name)
            if fb_cfg is not None:
                # Role-level hop: only the fallback tier's primary model, not its whole in-tier chain.
                from sagiha.adapters.model.openai import OpenAIModelAdapter

                base_url = fb_cfg.base_url or "http://localhost:11434/v1"
                labeled.append(
                    (
                        f"{fb_cfg.provider}:{fb_cfg.model}",
                        OpenAIModelAdapter(
                            model_name=fb_cfg.model,
                            base_url=base_url,
                            api_key=_api_key_for(fb_cfg),
                        ),
                    )
                )

        if len(labeled) == 1:
            return labeled[0][1]
        return FallbackModelAdapter(
            [p for _, p in labeled],
            labels=[name for name, _ in labeled],
        )

    if mode == "replay":
        if not Path(path).exists():
            raise FileNotFoundError(f"model.mode=replay requires cassette at {path}")
        model_provider: ModelProvider = CassetteModelProvider(cassette_path=path, mode="replay")
    elif mode == "record":
        live_adapter = _create_live_model_provider()
        model_provider = CassetteModelProvider(cassette_path=path, mode="record", inner_provider=live_adapter)
    elif mode == "live":
        model_provider = _create_live_model_provider()
    else:
        raise RuntimeError(f"Unknown model.mode: {mode}")

    bus.subscribe_observer(trajectory_store.append_event)
    evaluator = GateEvaluator(
        policy_engine,
        resource_governor,
        tool_registry,
        bus,
        max_diff_lines=config.gates.max_diff_lines,
        require_coverage_not_decreased=config.gates.require_coverage_not_decreased,
    )

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
        evaluator=evaluator,
    )
