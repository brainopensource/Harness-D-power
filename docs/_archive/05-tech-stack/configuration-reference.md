---
status: rationale
updated: 2026-07-30
retrieval: excluded
---
# **Configuration Reference**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

> [!IMPORTANT]
> TOML target schema validated by `src/sagiha/domain/config.py`. Composition implementation status per section detailed below (see [STATUS.md](../STATUS.md)).

Precedence: CLI flags $\rightarrow$ Environment (`SAGIHA_*`) $\rightarrow$ `config.toml` $\rightarrow$ Pydantic defaults. Validation occurs at load time prior to dispatch.

## **Implementation Status**

| Section | Schema Validation | Consumed by `build_kernel` | Target Milestone |
| :--- | :--- | :--- | :--- |
| `model.mode` | Yes | Partial (binds replay cassette) | Sprint 3 |
| `model.tiers` / `model.roles` | Yes | No | Sprint 3+ |
| `profiles.*` | Yes | No | Sprint 3 |
| `workspace.*` | Yes | No | Sprint 3 (root), Block 5 (worktrees) |
| `autonomy.always_gate` | Yes | Yes | Live |
| `autonomy.level` / timeouts | Yes | Validation only (subprocess refusal) | Sprint 3 / Block 3 |
| `governor.max_spend_usd_per_run` | Yes | Wired to governor constructor | Sprint 3 |
| `governor.max_concurrent_sandboxes` | Yes | Stored | Block 3 |
| Other `governor.*` | Yes | No | Future |
| `sandbox.*` | Yes (refuses host/subprocess under autonomous) | Yes (ContainerSandbox + proxy v2-S5) | Live |
| `retrieval.*` / `context.*` / `search.*` | Yes | No | Block 4+ |
| `gates.*` | Yes (`require_tests_unmodified` check) | Partial | Sprint 3+ |
| `telemetry.trajectory_db` | Yes | Yes | Live |
| `telemetry.*` (OTel) | Yes | No | Block 5 |
| `aoi.*`, `mcp_servers`, `hooks` | Yes | No | Block 5 / Deferred |

## **Complete TOML Reference**

```toml
# ─── Model Access ────────────────────────────────────────────────────────────
[model]
mode     = "live"                # live | replay | record
fallback = "workhorse"

[model.tiers.frontier]
provider    = "anthropic"
model       = "claude-3-5-sonnet-20241022"
max_tokens  = 16384
api_key_env = "ANTHROPIC_API_KEY"

[model.tiers.frontier.thinking]
enabled       = true
budget_tokens = 8192

[model.tiers.workhorse]
provider    = "anthropic"
model       = "claude-3-5-sonnet-20241022"
max_tokens  = 8192
api_key_env = "ANTHROPIC_API_KEY"

[model.tiers.workhorse.thinking]
enabled       = true
budget_tokens = 4096

[model.tiers.fast]
provider    = "anthropic"
model       = "claude-3-5-haiku-20241022"
max_tokens  = 4096
api_key_env = "ANTHROPIC_API_KEY"

[model.tiers.local]
provider    = "openai-compatible"
model       = "llama3"
base_url    = "http://localhost:11434/v1"
max_tokens  = 8192

[model.roles]
planning    = "frontier"
execution   = "workhorse"
candidates  = "workhorse"
compaction  = "fast"
judge       = "frontier"
meta        = "frontier"

# ─── Execution Profiles ──────────────────────────────────────────────────────
[profiles.coding]
workspace  = "worktree"
toolchain  = "full"
gates      = "full"
model_role = "execution"
tools      = ["*"]

[profiles.analysis]
workspace  = "readonly"
toolchain  = "readonly"
gates      = "acceptance_only"
model_role = "execution"
tools      = ["read_file", "list_dir", "glob", "grep", "recall", "remember"]

[profiles.review]
workspace  = "readonly"
toolchain  = "readonly"
gates      = "none"
model_role = "judge"
tools      = ["read_file", "glob", "grep", "git_read", "recall"]

[profiles.chat]
workspace  = "none"
toolchain  = "none"
gates      = "none"
model_role = "fast"
tools      = ["recall", "remember", "web_search"]

# ─── Workspace ───────────────────────────────────────────────────────────────
[workspace]
root         = "/path/to/target/repo"
worktree_dir = ".sagiha/worktrees"
state_dir    = ".sagiha"            # SQLite stores live here (see control-plane-python.md)
materialize  = [".env", ".venv", "node_modules"] # Link into worktrees (see git-worktree-branching.md)

# ─── Autonomy & Approval ─────────────────────────────────────────────────────
[autonomy]
level             = "interactive"   # interactive | hybrid | autonomous | scheduled
approval_timeout_s = 3600
on_timeout        = "deny"          # deny | escalate

always_gate = [
  "write_outside_worktree",
  "credential_access",
  "ci_config_change",
  "harness_policy_change",
]

# ─── Resource Governor ───────────────────────────────────────────────────────
[governor]
max_concurrent_runs      = 2
max_concurrent_sandboxes = 4
max_lsp_servers          = 4
max_spend_usd_per_run    = 5.0
max_spend_usd_per_hour   = 20.0
max_wall_clock_s         = 7200
max_steps_per_run        = 200
tokens_per_minute        = 200_000

# ─── Sandbox ─────────────────────────────────────────────────────────────────
[sandbox]
runtime          = "container"      # container | gvisor | subprocess
image            = "sagiha/runtime:latest"
network          = "restricted"     # none | restricted | host
egress_allowlist = ["pypi.org", "files.pythonhosted.org", "registry.npmjs.org", "github.com"]
memory_limit_mb  = 4096
cpu_limit        = 2.0
env_passthrough  = ["LANG", "TZ"]

# ─── Retrieval ───────────────────────────────────────────────────────────────
[retrieval]
chunk_strategy    = "ast_bounded"   # ast_bounded | fixed_window
max_chunk_tokens  = 1024
top_k             = 20
graph_expansion_hops = 2

# ─── Context Assembly ────────────────────────────────────────────────────────
[context]
max_context_tokens    = 200_000
compact_at_headroom   = 0.15
cache_breakpoints     = true
tool_output_max_chars = 30_000
read_file_max_lines   = 2000

# ─── Candidate Search (System 2) ─────────────────────────────────────────────
[search]
enabled            = false
candidates         = 3
max_repair_rounds  = 2
escalate_after_failures = 3
escalate_on_files  = 3
escalate_on_diff_lines = 150
prune_on_first_gate_fail = false

# ─── Gates ───────────────────────────────────────────────────────────────────
[gates]
require_tests_pass          = true
require_tests_unmodified    = true   # Anti-grader-editing gate
require_no_new_suppressions = true
require_coverage_not_decreased = true
max_diff_lines              = 1000

# ─── Observability ───────────────────────────────────────────────────────────
[telemetry]
otlp_endpoint      = "http://localhost:4317"
service_name       = "sagiha"
trajectory_db      = ".sagiha/trajectories.db"
log_level          = "INFO"
redact_patterns    = ["(?i)api[_-]?key", "(?i)secret", "(?i)password", "(?i)token"]
sample_rate        = 1.0

# ─── AOI (Advisory Models) ───────────────────────────────────────────────────
[aoi]
enabled              = false
shadow_mode          = true
exploration_fraction = 0.10

# ─── MCP Servers & Hooks ─────────────────────────────────────────────────────
[[mcp_servers]]
name      = "postgres"
transport = "stdio"
command   = ["mcp-server-postgres"]
trusted_output = false

[[hooks]]
event      = "post_edit"
kind       = "observer"
module     = "myorg.hooks.autoformat:run"
timeout_ms = 5000
```

## **Security Constraints & Failures**

| Setting | Enforced Constraint |
| :--- | :--- |
| `gates.require_tests_unmodified` | Refused if `false` in benchmark or RHI execution. |
| `autonomy.on_timeout` | Restricted to `deny` or `escalate` (`allow` prohibited). |
| `sandbox.network = "host"` | Refused unless `allow_unsafe = true` and `autonomy.level = "interactive"`. |
| `sandbox.runtime = "subprocess"` | Refused under `autonomous` or `scheduled` autonomy levels. |
| `aoi.shadow_mode` | Mandatory `true` without calibrated reliability diagrams. |

## **Secrets**

`config.toml` accepts environment variable names only (`api_key_env`). Hardcoded key values trigger immediate load-time rejection.

## **CLI Commands**

* Profile override: `sagiha run --profile ci` (see [STATUS.md](../STATUS.md)).
* Inspection/Validation: `sagiha config validate --profile ci` dumps resolved configuration with masked secrets and source provenance.
