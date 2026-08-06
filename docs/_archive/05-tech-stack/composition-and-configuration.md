---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Composition & Configuration**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

Detailed parameter key descriptions reside in [Configuration Reference](./configuration-reference.md). This document defines composition mechanics and boundaries between parametric settings and immutable code structures.

## **The Composition Root**

Single entry-point for kernel construction:

```python
def build_kernel(config: Config) -> Kernel: ...  # sagiha/composition.py
```

* Executes **once per process** before emitting events, instantiating adapters and binding ports into an immutable kernel.
* No service locators, dependency injection containers, or dynamic runtime rebinding.

### Adapter Selection

Named adapter mapping in composition:

```toml
[model]
provider = "anthropic"
mode     = "live"        # live | record | replay
```

```python
MODEL_ADAPTERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "google": GoogleProvider,
    "openai-compatible": OpenAICompatibleProvider,
}
```

Third-party adapters extend via [entry points](../02-architecture/extension-model.md). Setting `mode = "replay"` binds cassette adapters to run the entire kernel in CI without network calls.

### Port Binding & Execution Profiles

[Execution profiles](../02-architecture/execution-profiles.md) configure whether ports are bound:

```python
PROFILE_WORKSPACE = {
    "worktree": WorktreeWorkspaceFactory,
    "readonly": ReadOnlyWorkspaceFactory,
    "none": None,  # Explicitly unbound port (not a null object)
}
```

Unbound ports (`None`) fail loudly at composition or dispatch rather than swallowing calls silently. Profiles resolve per run. Roles map call sites to model tiers specified under `[model.tiers]`.

## **Layering & Merging**

Config merges across 4 layers (higher precedence overrides lower):

| Layer | Source | Scope & Use |
| :--- | :--- | :--- |
| 1. Defaults | Pydantic model defaults | Safe default configuration. |
| 2. Project | Workspace `config.toml` | Committed repository settings. |
| 3. User | `~/.config/sagiha/config.toml` | Local user preferences and env-var mappings. |
| 4. Invocation | CLI flags, `SAGIHA_*` env vars | Per-run overrides (e.g. `--model.mode replay`). |

* Dictionary merging is deep; list merging replaces existing lists unless modified by an `_append` suffix.
* Security constraint: Precedence may only **narrow** authority, never widen it (e.g. CLI flags cannot bypass project-level interactive autonomy).

## **Fail-Fast Validation**

Pydantic validates the merged configuration before kernel instantiation:
* `sandbox.runtime = "subprocess"` rejected when `autonomy.level` is `autonomous` or `scheduled`.
* `sandbox.network = "host"` rejected unless `allow_unsafe = true`.
* `gates.require_tests_unmodified = false` rejected.
* Retrieval weights (`retrieval.*_weight`) must sum to `1.0`.
* Referenced env vars must exist; hook modules and extensions must resolve per [Port Stability](../03-contracts-and-models/port-stability-and-versioning.md).
* `[model.roles]` values must reference valid `[model.tiers]`.
* Profiles with `gates = "full"` require a bound `Toolchain`; profiles with `workspace = "none"` cannot register write tools.

Resolved config (with secrets redacted) is recorded in run manifests and emitted with `run.started`.

## **Secret Handling**

Secrets are stored by environment variable **name** only (e.g. `api_key_env = "ANTHROPIC_API_KEY"`). Values are read at runtime by the control plane and never exposed to sandboxes, prompts, logs, or trajectories.

## **Parametric vs. Fixed Boundaries**

### Parametric
Providers/models per tier, role mappings, execution profiles, autonomy levels, governor budgets, sandbox configurations, retrieval parameters, context thresholds, telemetry endpoints, and extensions.

### Fixed in Code

| Invariant | Rationale |
| :--- | :--- |
| Mandatory `PolicyEngine` pre-dispatch check | Structural choke point for safety; prevents [CAR model](../02-architecture/car-model.md) bypasses. |
| `tests_unmodified` hard gate | Prevents agent self-grading tampering. |
| Binary hard gate admission | Preserves distinction between hard gates (admission) and soft scores (ranking). |
| TCB write boundary | Immutable policy, evaluator, benchmark, and deploy gate logic ([ADR-0007](../08-decisions/0007-trusted-computing-base.md)). |
| Deterministic event ordering & interceptors | Ensures deterministic trajectory replayability. |
| `Grant` token isolation | Grants never leave kernel dispatch. |
| Profile supervision | Profiles subtract capability, never supervision. |
| `gates = "none"` emits no `GateReport` | Prevents treating missing verdicts as `admitted=True`. |
| Aware-UTC timestamps | System-wide time contract. |

* **Rule**: Configuration parameterizes policy, never architectural invariants.

## **Profiles**

Preset configurations for common workloads (e.g. `ci`, `dev`). Invoked via `sagiha run --profile <name>` (see [STATUS.md](../STATUS.md)).
