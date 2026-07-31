---
status: rationale
updated: 2026-07-30
retrieval: excluded
---
# **Configuration Reference**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

> [!IMPORTANT]
> The TOML below is the **target schema** (validated by `src/sagiha/domain/config.py`).
> Composition does **not** yet honor every section — see the table and [STATUS.md](../STATUS.md).
> Setting a planned field today is inert (or only validated), not a live control.

Single local-first `config.toml`, validated by Pydantic at startup. **Misconfiguration fails at load, never at first dispatch** — an agent that discovers a bad sandbox setting forty minutes into a run has already done unbounded damage.

Precedence: CLI flags → environment (`SAGIHA_*`) → `config.toml` → defaults.

## **Implementation Status (composition vs schema)**

| Section | Schema / validation | Consumed by `build_kernel` today | Becomes real |
| :--- | :--- | :--- | :--- |
| `model.mode` | Yes | Partial — both branches bind replay cassette (Sprint 3 fixes) | Sprint 3 |
| `model.tiers` / `model.roles` | Yes (role→tier consistency) | No | Sprint 3+ |
| `profiles.*` | Yes (defaults) | No | Sprint 3 |
| `workspace.*` | Yes | No | Sprint 3 (root); Block 5 (worktrees) |
| `autonomy.always_gate` | Yes | Yes | — |
| `autonomy.level` / timeouts | Yes | Validation only (subprocess refuse) | Sprint 3 / Block 3 |
| `governor.max_spend_usd_per_run` | Yes | Wired into governor ctor | Spend recording Sprint 3 |
| `governor.max_concurrent_sandboxes` | Yes | Stored; admission not enforced | Block 3 |
| Other `governor.*` | Yes | No | Later |
| `sandbox.*` | Yes (host/subprocess refuses; container required for autonomous/scheduled) | Yes — rootless Podman `ContainerSandbox` + egress proxy (v2-S5) | — |
| `retrieval.*` / `context.*` / `search.*` | Yes | No | Blocks 4 / later |
| `gates.*` | Yes (`require_tests_unmodified` refuse) | No evaluator | Sprint 3 (acceptance); later for code gates |
| `telemetry.trajectory_db` | Yes | Yes | — |
| Other `telemetry.*` | Yes | No | Block 5 (OTel) |
| `aoi.*` | Yes | No | Deferred |
| `mcp_servers` / `hooks` | Yes | No | Block 5 |

Sprint 3 must shrink this table: each closed checklist item names which config sections became live.

## **Complete Reference**

```toml
# ─── Model access ────────────────────────────────────────────────────────────
# Tiers are defined by ROLE, not vendor, so routing policy survives model releases.
# Call sites request a role; the composition root binds one provider per role.
[model]
mode     = "live"                # live | replay (cassette) | record — applies to every tier
fallback = "workhorse"           # tier used when a breaker opens; omit to disable

[model.tiers.frontier]           # deepest reasoning: planning, judging, meta-improvement
provider    = "anthropic"
model       = "..."              # provider model id
max_tokens  = 16384
# Secrets are NEVER stored here. Env var name only; the value is read at runtime
# and excluded from the sandbox.
api_key_env = "ANTHROPIC_API_KEY"

[model.tiers.frontier.thinking]
enabled       = true
budget_tokens = 8192

[model.tiers.workhorse]          # default execution — the large majority of steps
provider    = "anthropic"
model       = "..."
max_tokens  = 8192
api_key_env = "ANTHROPIC_API_KEY"

[model.tiers.workhorse.thinking]
enabled       = true
budget_tokens = 4096

[model.tiers.fast]               # compaction, summarization, classification, commit messages
provider    = "anthropic"
model       = "..."
max_tokens  = 4096
api_key_env = "ANTHROPIC_API_KEY"

[model.tiers.local]              # offline / air-gapped; zero marginal cost
provider    = "openai-compatible"
model       = "..."
base_url    = "http://localhost:11434/v1"
max_tokens  = 8192

# Role → call-site defaults. Override per profile with `model_role`.
[model.roles]
planning    = "frontier"
execution   = "workhorse"
candidates  = "workhorse"        # N× cost: this line dominates System 2 spend
compaction  = "fast"
judge       = "frontier"         # must differ from the generating model
meta        = "frontier"

# ─── Execution profiles ──────────────────────────────────────────────────────
# A profile declares what a run MOUNTS and what ADMITS its result. Coding is one
# profile, not the privileged path. Third parties add profiles via entry points.
#   workspace: worktree | readonly | none
#   toolchain: full | readonly | none
#   gates:     full | acceptance_only | none
[profiles.coding]
workspace  = "worktree"
toolchain  = "full"
gates      = "full"
model_role = "execution"
tools      = ["*"]

[profiles.analysis]              # code explanation, architecture Q&A, impact assessment
workspace  = "readonly"
toolchain  = "readonly"
gates      = "acceptance_only"
model_role = "execution"
tools      = ["read_file", "list_dir", "glob", "grep", "recall", "remember"]

[profiles.review]                # PR review bot — soft score only, never a hard gate
workspace  = "readonly"
toolchain  = "readonly"
gates      = "none"
model_role = "judge"
tools      = ["read_file", "glob", "grep", "git_read", "recall"]

[profiles.chat]                  # conversational; no repository access at all
workspace  = "none"
toolchain  = "none"
gates      = "none"
model_role = "fast"
tools      = ["recall", "remember", "web_search"]

# ─── Workspace ───────────────────────────────────────────────────────────────
[workspace]
root         = "/path/to/target/repo"
worktree_dir = ".sagiha/worktrees"
# All three stores live under .sagiha/ at the REPOSITORY ROOT, never inside a
# worktree — a per-candidate trajectory is deleted on release and the run becomes
# unreplayable. One writer per database; see control-plane-python.md.
state_dir    = ".sagiha"
# Ignored-but-required artifacts linked into every fresh worktree.
# Without these, the first build in a new worktree fails. See git-worktree-branching.md
materialize  = [".env", ".venv", "node_modules"]

# ─── Autonomy & approval ─────────────────────────────────────────────────────
[autonomy]
level             = "interactive"   # interactive | hybrid | autonomous | scheduled
approval_timeout_s = 3600
on_timeout        = "deny"          # deny | escalate. Never "allow".

# Always require a human grant regardless of level.
always_gate = [
  "write_outside_worktree",
  "credential_access",
  "ci_config_change",
  "harness_policy_change",
]

# ─── Resource governor (global admission control) ────────────────────────────
[governor]
max_concurrent_runs      = 2
max_concurrent_sandboxes = 4
max_lsp_servers          = 4
max_spend_usd_per_run    = 5.0
max_spend_usd_per_hour   = 20.0
max_wall_clock_s         = 7200
max_steps_per_run        = 200
tokens_per_minute        = 200_000

# ─── Sandbox (the security perimeter) ────────────────────────────────────────
[sandbox]
runtime          = "container"      # container | gvisor | subprocess
image            = "sagiha/runtime:latest"
network          = "restricted"     # none | restricted | host  ("host" refused unless allow_unsafe)
egress_allowlist = ["pypi.org", "files.pythonhosted.org", "registry.npmjs.org", "github.com"]
memory_limit_mb  = 4096
cpu_limit        = 2.0
# Env vars passed in. Everything else is scrubbed.
env_passthrough  = ["LANG", "TZ"]

# ─── Retrieval ───────────────────────────────────────────────────────────────
[retrieval]
chunk_strategy    = "ast_bounded"   # ast_bounded | fixed_window (fixed_window is a baseline for ablation only)
max_chunk_tokens  = 1024
top_k             = 20
graph_expansion_hops = 2
# v1 is lexical (BM25/FTS5) + graph expansion. `dense_weight`, `embedding_model`, and
# `embedding_dims` return with the dense tier — deferred behind a measured recall@10
# trigger, see ADR-0014.

# ─── Context assembly ────────────────────────────────────────────────────────
[context]
max_context_tokens    = 200_000
compact_at_headroom   = 0.15        # compact when <15% of the window remains
cache_breakpoints     = true
tool_output_max_chars = 30_000
read_file_max_lines   = 2000

# ─── Candidate search (System 2) ─────────────────────────────────────────────
[search]
# Off by default: empirical exit gate not met (s4-harvest-findings.md).
enabled            = false
candidates         = 3
max_repair_rounds  = 2
escalate_after_failures = 3         # stop further repair after this many failed attempts
escalate_on_files  = 3
escalate_on_diff_lines = 150
prune_on_first_gate_fail = false    # true = skip repair after first fail

# ─── Gates ───────────────────────────────────────────────────────────────────
[gates]
require_tests_pass          = true
require_tests_unmodified    = true   # never disable: this is the anti-grader-editing gate
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

# ─── AOI (advisory models) ───────────────────────────────────────────────────
[aoi]
enabled              = false        # off until calibrated
shadow_mode          = true         # never flip to false without a reliability diagram
exploration_fraction = 0.10         # always runs to completion regardless of predicted risk

# ─── MCP servers ─────────────────────────────────────────────────────────────
[[mcp_servers]]
name      = "postgres"
transport = "stdio"
command   = ["mcp-server-postgres"]
trusted_output = false              # third-party output is untrusted by default

# ─── Hooks ───────────────────────────────────────────────────────────────────
[[hooks]]
event      = "post_edit"
kind       = "observer"             # observer | interceptor
module     = "myorg.hooks.autoformat:run"
timeout_ms = 5000
```

## **Settings That Are Deliberately Hard to Weaken**

Some values are not merely defaults — loosening them changes the system's safety properties, so the loader treats them specially.

| Setting | Constraint |
| :--- | :--- |
| `gates.require_tests_unmodified` | Warns loudly at load if false; refused entirely in benchmark and RHI runs — a candidate that can edit its grader makes every downstream number meaningless |
| `autonomy.on_timeout` | Accepts `deny` or `escalate` only. There is no `allow`; an unattended approval must never become consent |
| `sandbox.network = "host"` | Requires `allow_unsafe = true` **and** `autonomy.level = "interactive"` |
| `sandbox.runtime = "subprocess"` | Permitted for local development only; refused when autonomy is `autonomous` or `scheduled` |
| `aoi.shadow_mode` | Cannot be false unless a calibration report exists for the loaded model version |

## **Secrets**

`config.toml` holds **environment variable names, never values.** Secrets are resolved at runtime, scoped per grant, excluded from the sandbox environment, and redacted from tool output before it reaches context, logs, or the trajectory.

A config file containing a literal key is rejected at load with an explicit error rather than a warning — this file is committed to repositories, pasted into issues, and read by the agent itself.

## **Profiles**

> **Planned — Sprint 3**: CLI profile selection. See [STATUS.md](../STATUS.md).

```bash
sagiha run --profile ci        # config.ci.toml overlays config.toml
```

Standard profiles: `dev` (interactive, subprocess sandbox, replay-friendly), `ci` (autonomous, container, strict gates, hard budget), `bench` (records A/A metadata, forbids gate relaxation).

## **Validation Output**

> **Planned — Sprint 3+**: resolved-config dump. Config *validation at load* already exists in the `Config` model; the CLI command below is not shipping yet.

```bash
sagiha config validate --profile ci
```

Prints the fully resolved configuration with provenance for every value (default / file / env / flag) and secrets masked. The resolved config hash is recorded in every trajectory, so a run's exact settings are recoverable months later — without which "it worked last week" is unfalsifiable.
