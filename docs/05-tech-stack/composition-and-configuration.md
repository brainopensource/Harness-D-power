---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Composition & Configuration**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

[Configuration Reference](./configuration-reference.md) documents *what each key means*. This file
documents *what configuration is* in this architecture: the mechanism that selects which adapter
implements each port, and — equally important — the boundary of what configuration is allowed to
decide.

"Config-driven" is a claim that gets projects into trouble. Taken far enough it produces a system
where behavior lives in TOML, no path is type-checked, and every question is answered "it depends on
the config." The discipline is to name what is parametric and what is fixed, and to defend the line.

## **The Composition Root**

One function, one place:

```python
def build_kernel(config: Config) -> Kernel: ...  # sagiha/composition.py
```

It is the only place adapters are constructed and the only place ports are bound. Every other module
receives its dependencies as constructor arguments and imports nothing from `sagiha.adapters`.

Composition happens **exactly once per process, before the first event is emitted**, and produces an
immutable kernel. There is no rebinding, no service locator, no runtime registration. The
`import-linter` contract makes the direction of dependency a build failure rather than a convention.

### Config selects adapters by name

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

A literal dict, resolved at composition, extended by
[entry points](../02-architecture/extension-model.md) for third parties. Not a registry, not
reflection, not `importlib` on a config string. pyright sees every branch; "go to definition" reaches
every adapter.

`mode` is the same mechanism, and it is the highest-leverage line in the file: `replay` binds a
cassette adapter implementing the same `ModelProvider` Protocol, and the entire kernel then runs in CI
with zero API calls. That works only because the port is narrow enough that a recording satisfies it.

### Profiles select which ports are bound at all

[Execution profiles](../02-architecture/execution-profiles.md) extend the same mechanism from *which
adapter* to *whether a port is bound*:

```python
PROFILE_WORKSPACE = {
    "worktree": WorktreeWorkspaceFactory,
    "readonly": ReadOnlyWorkspaceFactory,
    "none": None,  # the port is genuinely unbound, not a null object
}
```

`None` rather than a no-op stub, deliberately. A null `Workspace` that silently swallows writes is a
class of bug that surfaces as "the agent said it edited the file"; an unbound port makes the attempt a
loud composition-time or dispatch-time failure. The same applies to `Toolchain` and `Evaluator`.

Profiles resolve **per run**, not per process: one kernel serves `coding` and `chat` tasks
concurrently, because the profile determines which bound set a given run draws from rather than how the
kernel was built.

### Model roles resolve the same way

`[model.tiers.*]` binds a provider per tier; `[model.roles]` maps call sites to tiers. The composition
root produces one `ModelProvider` per role, and callers request a role. `mode = "replay"` substitutes a
cassette adapter for **every** role at once, which is what keeps the whole kernel runnable in CI with
zero API calls.

## **Layering**

Four layers, later wins, all validated as one:

| Layer | Source | Use |
| :--- | :--- | :--- |
| 1. Defaults | Pydantic model defaults in code | The safe configuration; a valid run needs no config file |
| 2. Project | `config.toml` at the workspace root | Team-level settings, committed |
| 3. User | `~/.config/sagiha/config.toml` | Personal preferences, endpoints, keys-by-env-name |
| 4. Invocation | CLI flags, `SAGIHA_*` env vars | One run: `--autonomy interactive`, `--model.mode replay` |

Merging is **deep for tables, replace for lists**. Appending to `always_gate` by accident is a
security regression; replacing it is at least visible. Lists that genuinely accumulate — `materialize`,
`egress_allowlist` — take an explicit `_append` suffix.

Precedence never crosses the security boundary: a lower layer may **narrow** authority, never widen
it. `--autonomy autonomous` on the CLI cannot override a project config that pins `interactive`, and
nothing at any layer can empty `always_gate`. Config is subject to the same rule as hooks — narrow,
never widen.

## **Validation Is Fail-Fast**

The whole config is one Pydantic model, validated before composition. Misconfiguration fails at
startup, loudly, with the offending key and file — never at the first tool dispatch forty minutes into
an autonomous run.

Validation covers what a type cannot:

* `sandbox.runtime = "subprocess"` is **refused** when `autonomy.level` is `autonomous` or
  `scheduled`. Permitted for local development only.
* `sandbox.network = "host"` is refused without an explicit `allow_unsafe` acknowledgement.
* `gates.require_tests_unmodified = false` is refused outright — see below.
* `retrieval.*_weight` values must sum to 1.0.
* Every referenced env var name must exist; every hook module must import.
* Every declared extension must resolve and match its port's major version
  ([Port Stability](../03-contracts-and-models/port-stability-and-versioning.md)).
* Every `[model.roles]` value must name a tier defined under `[model.tiers]`.
* Every tool listed in a profile must exist in the registry; `"*"` means all registered tools.
* A profile with `gates = "full"` must bind a `Toolchain` — gates it cannot evaluate are gates that
  silently pass.
* A profile with `workspace = "none"` must not list a write-capable tool. Refused at load, since the
  alternative is a dispatch-time denial forty minutes in.

The resolved config is recorded in the run manifest and emitted with `run.started`, with secrets
redacted. A trajectory that cannot say what configuration produced it is not auditable, and replay
against a different config is not replay.

## **Secrets Are Never Configuration**

Config holds the **name** of an environment variable, never a value:

```toml
api_key_env = "ANTHROPIC_API_KEY"
```

The value is read at runtime by the control plane and never enters the sandbox, the prompt, the
trajectory, or a log line. This is a hard gate at S1: *no credential reachable inside the sandbox*.
A config file with a key in it is a config file that gets committed.

## **What Is Parametric — and What Is Not**

This is the part that keeps "config-driven" from meaning "everything is a knob."

### Parametric

Anything with a legitimate per-project or per-run answer: which provider and model **per tier**, and
which tier serves each **role**; which execution profiles exist and what each mounts; autonomy level
and approval timeout; governor limits (spend, concurrency, wall clock, steps); sandbox image,
resources, and egress allowlist; retrieval `top_k`, chunk strategy, graph hops; context window and
compaction headroom; candidate count and escalation thresholds; gate *thresholds*; telemetry endpoint
and sampling; which extensions are enabled.

### Fixed in code, deliberately

| Not configurable | Why |
| :--- | :--- |
| That `PolicyEngine` is consulted before every dispatch | The choke point is structural. A config key that could skip it is the bypass the [CAR model](../02-architecture/car-model.md) exists to prevent. |
| `tests_unmodified` as a hard gate | The one gate that stops a candidate editing its own grader. A disable switch is the first thing an optimizer finds. |
| Hard gates being hard | Thresholds are configurable; the gate/score distinction is not. "Proxies may rank; only gates may admit" stops being true the moment it is a boolean. |
| The TCB write boundary | Policy engine, evaluator, benchmark definitions, deploy gate — see [ADR-0007](../08-decisions/0007-trusted-computing-base.md). |
| Event ordering and observer/interceptor semantics | Architectural invariants. Configurable ordering makes replay non-deterministic. |
| Grants never leaving the dispatch choke point | Structural, not a policy setting. |
| That every profile dispatches through `PolicyEngine` | A profile subtracts *capability*, never *supervision*. A `gates`/`tools` setting that could skip authorization would be a privilege-escalation surface with a friendly name. |
| That `gates = "none"` yields **no** `GateReport` rather than an empty one | An empty report reads as `admitted=True`. Absence of a verdict and a passing verdict must never share a representation. |
| Aware-UTC timestamps | Contract rule 3. |

The pattern: **configuration parameterizes policy, never structure.** If a key would let an operator
turn a structural invariant off, the answer is no — and the reason belongs in this table rather than in
a rejected issue.

## **Profiles**

Named bundles for the recurring combinations, so the common cases are one flag rather than six:

```toml
[profiles.ci]
model.mode      = "replay"
autonomy.level  = "autonomous"
sandbox.runtime = "container"
telemetry.sample_rate = 1.0

[profiles.dev]
model.mode      = "live"
autonomy.level  = "interactive"
sandbox.runtime = "subprocess"    # permitted: autonomy is interactive
```

> **Planned — Sprint 3**: `sagiha run --profile …` lands with the CLI. Profile *data* is already in the config schema; composition does not yet resolve profiles at run time ([STATUS.md](../STATUS.md)).

`sagiha run --profile ci`. Profiles apply at layer 2/3 and remain subject to every validation rule
above — a profile is a shorthand, not an exemption.
