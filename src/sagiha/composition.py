"""Composition root — see docs/05-tech-stack/composition-and-configuration.md.

Single function, single place: `build_kernel(config: Config) -> Kernel`.
Constructs adapters, binds ports, and returns an immutable kernel.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from sagiha.adapters.memory.short_term import InMemoryMemory
from sagiha.adapters.model.cassette import CassetteModelProvider
from sagiha.adapters.tools.builtins import BUILTIN_SCHEMAS, TOOL_DESCRIPTIONS, register_builtin_tools
from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.domain.config import Config
from sagiha.domain.content import ToolSchema
from sagiha.domain.control import RunContext
from sagiha.domain.work import TaskSpec
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
from sagiha.ports.search import CandidateSearch
from sagiha.ports.tool_registry import ToolRegistry
from sagiha.ports.trajectory import TrajectoryStore
from sagiha.ports.workspace import Workspace, WorktreeManager

if TYPE_CHECKING:
    from sagiha.adapters.search.protocols import CandidateOutcome
    from sagiha.adapters.workspace.worktree import GitWorktreeManager


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
    #: Non-optional (RC-8): `RunLoop.evaluator` is required, and `build_kernel` always
    #: constructs exactly one `GateEvaluator`. Leaving this `| None` re-created the hole RC-8
    #: closes — every consumer had to either narrow it or fall back to building its own TCB
    #: object, which is the thing `agency` must never do.
    evaluator: Evaluator
    bus: EventBus = field(default_factory=EventBus)
    indexer: Indexer | None = None
    code_graph: CodeGraph | None = None
    lsp_adapter: LSPAdapter | None = None
    worktree_manager: WorktreeManager | None = None
    candidate_search: CandidateSearch | None = None
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
    include_search: bool = True,
) -> Kernel:
    """Builds and wires the Sprint 3a kernel from configuration.

    Adapter selection, capability instantiation, and port binding happen exactly once here.
    Misconfiguration fails at composition (D3 / D14).

    `include_search=False` skips wiring a `CandidateSearch` — used by
    `KernelCandidateExecutor.execute` (v2-S4), which calls `build_kernel` once per Best-of-N
    candidate to get that candidate its own worktree-scoped kernel. Without this flag every
    candidate would recursively build a full `BestOfNSearch` (and its own `GitWorktreeManager`,
    pointed at the same `worktree_dir`) that it can never use — construction cost and a stray
    worktree-manager instance per candidate, for zero behavioral benefit.
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

    from sagiha.adapters.workspace.worktree import GitWorktreeManager

    worktree_manager = GitWorktreeManager(
        config.workspace.root,
        config.workspace.worktree_dir,
        materialize_paths=config.workspace.materialize,
        bus=bus,
    )

    candidate_search = build_candidate_search(config, cassette_path=path, bus=bus) if include_search else None

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
        worktree_manager=worktree_manager,
        candidate_search=candidate_search,
    )


def _parse_numstat(numstat_output: str) -> tuple[int, int]:
    """`(files_changed, total_lines)` from `git diff --numstat` output — mirrors
    `GateEvaluator._diff_within_bounds`'s parsing, duplicated rather than imported because that
    method is TCB-owned (`sagiha.outer_loop.evaluator`) and composition-root code must not
    depend on it (nor may the TCB depend on composition — the `tcb-isolation` contract runs
    both directions in spirit even where it is not mechanically enforced)."""
    files = 0
    total = 0
    for line in numstat_output.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        files += 1
        for count in fields[:2]:
            if count.isdigit():
                total += int(count)
    return files, total


@dataclass
class KernelCandidateExecutor:
    """`CandidateExecutor` implementation — the composition root's own class, since running a
    Best-of-N candidate means building a fresh `Kernel` and `RunLoop` bound to its worktree, and
    only composition-root code may reach both `build_kernel` and the concrete adapters at once.
    """

    parent_config: Config
    cassette_path: str
    worktree_manager: GitWorktreeManager

    async def execute(
        self,
        task: TaskSpec,
        context: RunContext,
        *,
        branch_id: str,
        base_commit: str,
        temperature: float | None = None,
        repair_round: int = 0,
    ) -> CandidateOutcome:
        from sagiha.adapters.search.protocols import CandidateOutcome
        from sagiha.agency.run_loop import RunLoop

        manager = self.worktree_manager
        if repair_round == 0:
            await manager.allocate(base_commit, branch_id, run_id=context.run_id)
            await manager.materialize(branch_id)

        worktree_path = manager.path_for(branch_id)
        roles = self.parent_config.model.roles
        candidate_tier = roles.get("candidates") or roles.get("execution")

        candidate_workspace_cfg = self.parent_config.workspace.model_copy(update={"root": worktree_path})
        candidate_config = self.parent_config.model_copy(update={"workspace": candidate_workspace_cfg})

        kernel = build_kernel(
            candidate_config, cassette_path=self.cassette_path, tier=candidate_tier, include_search=False
        )
        run_id = str(uuid.uuid4())

        loop = RunLoop(
            model_provider=kernel.model_provider,
            policy_engine=kernel.policy_engine,
            resource_governor=kernel.resource_governor,
            tool_registry=kernel.tool_registry,
            trajectory_store=kernel.trajectory_store,
            bus=kernel.bus,
            tool_schemas=list(kernel.tool_schemas),
            evaluator=kernel.evaluator,
            workspace=kernel.workspace,
            pricing=kernel.config.pricing,
            context=kernel.config.context,
            branch_id=branch_id,
            temperature=temperature,
        )

        candidate_task = task.model_copy(update={"parent_task_id": task.task_id})
        ctx = RunContext(
            run_id=run_id,
            autonomy_level=candidate_config.autonomy.level,
            workspace_root=worktree_path,
            budget_remaining_usd=candidate_config.governor.max_spend_usd_per_run,
            base_commit=base_commit,
        )

        start = time.monotonic()
        result = await loop.run(candidate_task, ctx)
        elapsed = time.monotonic() - start

        diff_result = await kernel.workspace.run(["git", "diff", base_commit])
        numstat_result = await kernel.workspace.run(["git", "diff", "--numstat", base_commit])
        files_changed, diff_lines = _parse_numstat(numstat_result.stdout)

        return CandidateOutcome(
            branch_id=branch_id,
            run_id=run_id,
            worktree_ref=branch_id,
            gate_report=result.gate_report,
            cost=result.cost,
            steps=len(result.steps),
            wall_clock_s=elapsed,
            diff_digest=hashlib.sha256(diff_result.stdout.encode()).hexdigest(),
            files_changed=files_changed,
            diff_lines=diff_lines,
            temperature=temperature or 0.0,
            repair_round=repair_round,
        )


def build_candidate_search(
    config: Config,
    *,
    cassette_path: str | None = None,
    bus: EventBus | None = None,
) -> CandidateSearch | None:
    """Wires the Best-of-N adapter, gated on `config.search.enabled`.

    Returns `None` when search is disabled — callers must not construct an always-on stub just
    to have something to call; absence of search is absence of a `CandidateSearch`, not a
    single-candidate degenerate case of one.
    """
    if not config.search.enabled:
        return None

    from sagiha.adapters.search.best_of_n import BestOfNSearch
    from sagiha.adapters.search.scoring import build_scorer
    from sagiha.adapters.workspace.worktree import GitWorktreeManager

    path = cassette_path or ".sagiha/cassettes/default.json"
    worktree_manager = GitWorktreeManager(
        config.workspace.root,
        config.workspace.worktree_dir,
        materialize_paths=config.workspace.materialize,
        bus=bus,
    )
    executor = KernelCandidateExecutor(
        parent_config=config,
        cassette_path=path,
        worktree_manager=worktree_manager,
    )
    scorer = build_scorer(config.search.scoring)

    # Bounded by inference capacity, not just sandbox capacity: launching more parallel
    # candidates than the model tier can actually serve concurrently gets one candidate,
    # repeated, plus context thrashing — not more candidates. See `sagiha.cpu.toml` /
    # `sagiha.gpu.toml` for the two committed profiles this is meant to be driven from.
    candidates_tier_name = config.model.roles.get("candidates") or config.model.roles.get("execution")
    candidates_tier = config.model.tiers.get(candidates_tier_name) if candidates_tier_name else None
    tier_capacity = candidates_tier.max_concurrent_requests if candidates_tier is not None else 1
    max_concurrent = min(config.governor.max_concurrent_sandboxes, tier_capacity)

    return BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=scorer,
        config=config.search,
        bus=bus,
        max_concurrent=max_concurrent,
    )
