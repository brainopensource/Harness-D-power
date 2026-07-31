"""Configuration models and fail-fast validation rules — see docs/05-tech-stack/configuration-reference.md."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sagiha.domain.trajectory import TokenUsage


class ThinkingConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    budget_tokens: int = 4096


class ModelTierConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    fallbacks: list[str] = Field(default_factory=list)
    max_tokens: int = 8192
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str | None = None
    thinking: ThinkingConfig = Field(default_factory=ThinkingConfig)


class ModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: Literal["live", "replay", "record"] = "live"
    active_tier: str = "tier0"
    fallback: str | None = "workhorse"
    tiers: dict[str, ModelTierConfig] = Field(
        default_factory=lambda: {
            # ─── Standard Role Tiers ───────────────────────────────────────────
            "frontier": ModelTierConfig(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                max_tokens=16384,
                api_key_env="ANTHROPIC_API_KEY",
                thinking=ThinkingConfig(enabled=True, budget_tokens=8192),
            ),
            "workhorse": ModelTierConfig(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                api_key_env="ANTHROPIC_API_KEY",
                thinking=ThinkingConfig(enabled=True, budget_tokens=4096),
            ),
            "fast": ModelTierConfig(
                provider="anthropic",
                model="claude-3-5-haiku-20241022",
                max_tokens=4096,
                api_key_env="ANTHROPIC_API_KEY",
                thinking=ThinkingConfig(enabled=False),
            ),
            "local": ModelTierConfig(
                provider="openai-compatible",
                model="qwen2.5-coder:7b",
                max_tokens=8192,
                base_url="http://localhost:11434/v1",
                api_key_env="",
            ),
            # ─── Config-Driven Fallback Tiers (Tier 0 / Tier 1 / Tier 2) ──────
            #
            # Tier 0 (Free / Local): Primary local server or OpenRouter free model,
            # falling back to free OpenRouter models in order.
            "tier0": ModelTierConfig(
                provider="openai-compatible",
                model="cohere/north-mini-code:free",
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
                max_tokens=8192,
                fallbacks=[
                    "inclusionai/ling-3.0-flash:free",
                    "poolside/laguna-s-2.1:free",
                    "poolside/laguna-xs-2.1:free",
                    "nvidia/nemotron-3-ultra-550b-a55b:free",
                ],
            ),
            # Tier 1 (Cheap / Medium Paid): High-speed, low-cost paid models.
            "tier1": ModelTierConfig(
                provider="openai-compatible",
                model="qwen/qwen3.7-flash",
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
                max_tokens=8192,
                fallbacks=[
                    "xiaomi/mimo-v2.5",
                    "deepseek/deepseek-v4-flash",
                    "tencent/hy3",
                ],
            ),
            # Tier 2 (Good / Premium Paid): High-capability frontier models.
            "tier2": ModelTierConfig(
                provider="openai-compatible",
                model="anthropic/claude-sonnet-5",
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
                max_tokens=8192,
                fallbacks=[
                    "deepseek/deepseek-v4-pro",
                    "z-ai/glm-5.2",
                    "minimax/minimax-m3",
                    "moonshotai/kimi-k3",
                ],
            ),
            # ─── Individual OpenRouter Catalog Items ─────────────────────────
            "openrouter_free": ModelTierConfig(
                provider="openai-compatible",
                model="google/gemma-4-31b-it:free",
                max_tokens=8192,
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
            ),
            "openrouter_code": ModelTierConfig(
                provider="openai-compatible",
                model="cohere/north-mini-code:free",
                max_tokens=8192,
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
            ),
            "openrouter_gpt": ModelTierConfig(
                provider="openai-compatible",
                model="openai/gpt-oss-20b:free",
                max_tokens=8192,
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
            ),
            "openrouter_ling": ModelTierConfig(
                provider="openai-compatible",
                model="inclusionai/ling-3.0-flash:free",
                max_tokens=8192,
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
            ),
        }
    )
    roles: dict[str, str] = Field(
        default_factory=lambda: {
            "planning": "frontier",
            "execution": "workhorse",
            "candidates": "workhorse",
            "compaction": "fast",
            "judge": "frontier",
            "meta": "frontier",
        }
    )


class ProfileConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace: Literal["worktree", "readonly", "none"] = "worktree"
    toolchain: Literal["full", "readonly", "none"] = "full"
    gates: Literal["full", "acceptance_only", "none"] = "full"
    model_role: str = "execution"
    tools: list[str] = Field(default_factory=lambda: ["*"])


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    root: str = "."
    worktree_dir: str = ".sagiha/worktrees"
    state_dir: str = ".sagiha"
    materialize: list[str] = Field(default_factory=lambda: [".env", ".venv", "node_modules"])


class AutonomyConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: Literal["interactive", "hybrid", "autonomous", "scheduled"] = "interactive"
    approval_timeout_s: int = 3600
    on_timeout: Literal["deny", "escalate"] = "deny"
    always_gate: list[str] = Field(
        default_factory=lambda: [
            "write_outside_worktree",
            "credential_access",
            "ci_config_change",
            "harness_policy_change",
        ]
    )


class PricingConfig(BaseModel):
    """Per-million-token rates used to turn `TokenUsage` into dollars.

    Defaults are `0.0` — the honest price of a local model. A non-zero default would
    invent a cost figure for every user who never configured one, which is the same
    class of defect as the zeroed telemetry it replaces (H2).
    """

    model_config = ConfigDict(frozen=True)

    usd_per_1m_input: float = 0.0
    usd_per_1m_output: float = 0.0
    #: Cached input is billed at a discount by most providers. Falls back to the full
    #: input rate when unset, which over-reports rather than under-reports.
    usd_per_1m_cache_read: float | None = None

    def cost_usd(self, usage: TokenUsage) -> float:
        cache_rate = (
            self.usd_per_1m_input if self.usd_per_1m_cache_read is None else self.usd_per_1m_cache_read
        )
        return (
            usage.input_tokens * self.usd_per_1m_input
            + usage.output_tokens * self.usd_per_1m_output
            + usage.cache_read_tokens * cache_rate
        ) / 1_000_000


class GovernorConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_concurrent_runs: int = 2
    max_concurrent_sandboxes: int = 4
    max_lsp_servers: int = 4
    max_spend_usd_per_run: float = 5.0
    max_spend_usd_per_hour: float = 20.0
    max_wall_clock_s: int = 7200
    max_steps_per_run: int = 200
    tokens_per_minute: int = 200_000


class SandboxConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime: Literal["container", "gvisor", "subprocess"] = "container"
    image: str = "sagiha/runtime:latest"
    network: Literal["none", "restricted", "host"] = "restricted"
    egress_allowlist: list[str] = Field(
        default_factory=lambda: [
            "pypi.org",
            "files.pythonhosted.org",
            "registry.npmjs.org",
            "github.com",
        ]
    )
    memory_limit_mb: int = 4096
    cpu_limit: float = 2.0
    env_passthrough: list[str] = Field(default_factory=lambda: ["LANG", "TZ"])
    allow_unsafe: bool = False


class RetrievalConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_strategy: Literal["ast_bounded", "fixed_window"] = "ast_bounded"
    max_chunk_tokens: int = 1024
    top_k: int = 20
    graph_expansion_hops: int = 2


class ContextConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_context_tokens: int = 200_000
    compact_at_headroom: float = 0.15
    cache_breakpoints: bool = True
    tool_output_max_chars: int = 30_000
    read_file_max_lines: int = 2000


class SearchConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    candidates: int = 3
    max_repair_rounds: int = 2
    escalate_after_failures: int = 2
    escalate_on_files: int = 3
    escalate_on_diff_lines: int = 150


class GatesConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_tests_pass: bool = True
    require_tests_unmodified: bool = True
    require_no_new_suppressions: bool = True
    #: Defaults to False as of PR-1a, and the change is a correction, not a relaxation.
    #: This gate previously "passed" because `GateEvaluator` returned a hardcoded `True`
    #: (H1) — it was never evaluated. It now reports an honest `None`, because there is
    #: no `Toolchain` adapter and no coverage baseline to compare against. Leaving the
    #: default at True would mean every run fails closed on a gate nothing can compute,
    #: which teaches operators to disable gates. Admission behaviour is unchanged; the
    #: label is now true. Set it to True once a Toolchain adapter lands and the gate can
    #: answer — at which point `None` correctly fails closed.
    require_coverage_not_decreased: bool = False
    max_diff_lines: int = 1000


class TelemetryConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    otlp_endpoint: str = "http://localhost:4317"
    service_name: str = "sagiha"
    trajectory_db: str = ".sagiha/trajectories.db"
    log_level: str = "INFO"
    redact_patterns: list[str] = Field(
        default_factory=lambda: [
            "(?i)api[_-]?key",
            "(?i)secret",
            "(?i)password",
            "(?i)token",
        ]
    )
    sample_rate: float = 1.0


class AOIConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    shadow_mode: bool = True
    exploration_fraction: float = 0.10


class MCPServerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    transport: Literal["stdio", "sse"] = "stdio"
    command: list[str]
    trusted_output: bool = False


class HookConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: str
    kind: Literal["observer", "interceptor"] = "observer"
    module: str
    timeout_ms: int = 5000


class Config(BaseModel):
    """Normalized, validated system configuration — see docs/05-tech-stack/configuration-reference.md."""

    model_config = ConfigDict(frozen=True)

    model: ModelConfig = Field(default_factory=ModelConfig)
    profiles: dict[str, ProfileConfig] = Field(
        default_factory=lambda: {
            "coding": ProfileConfig(
                workspace="worktree",
                toolchain="full",
                gates="full",
                model_role="execution",
                tools=["*"],
            ),
            "analysis": ProfileConfig(
                workspace="readonly",
                toolchain="readonly",
                gates="acceptance_only",
                model_role="execution",
                tools=[
                    "read_file",
                    "list_dir",
                    "glob",
                    "grep",
                    "recall",
                    "remember",
                ],
            ),
            "review": ProfileConfig(
                workspace="readonly",
                toolchain="readonly",
                gates="none",
                model_role="judge",
                tools=["read_file", "glob", "grep", "git_read", "recall"],
            ),
            "chat": ProfileConfig(
                workspace="none",
                toolchain="none",
                gates="none",
                model_role="fast",
                tools=["recall", "remember", "web_search"],
            ),
        }
    )
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    autonomy: AutonomyConfig = Field(default_factory=AutonomyConfig)
    governor: GovernorConfig = Field(default_factory=GovernorConfig)
    pricing: PricingConfig = Field(default_factory=PricingConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    gates: GatesConfig = Field(default_factory=GatesConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    aoi: AOIConfig = Field(default_factory=AOIConfig)
    mcp_servers: list[MCPServerConfig] = Field(default_factory=lambda: list[MCPServerConfig]())
    hooks: list[HookConfig] = Field(default_factory=lambda: list[HookConfig]())

    @model_validator(mode="after")
    def validate_security_invariants(self) -> Config:
        if self.sandbox.runtime == "subprocess" and self.autonomy.level in ("autonomous", "scheduled"):
            raise ValueError(
                f"sandbox.runtime='subprocess' is refused when autonomy.level is '{self.autonomy.level}'"
            )

        if self.sandbox.network == "host" and not self.sandbox.allow_unsafe:
            raise ValueError("sandbox.network='host' is refused without allow_unsafe=True")

        if not self.gates.require_tests_unmodified:
            raise ValueError("gates.require_tests_unmodified=False is refused outright")

        for role_name, tier_name in self.model.roles.items():
            if tier_name not in self.model.tiers:
                raise ValueError(f"Model role '{role_name}' references undefined tier '{tier_name}'")

        return self
