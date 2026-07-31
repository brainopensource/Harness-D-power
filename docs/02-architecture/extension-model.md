---
status: rationale
retrieval: excluded
updated: 2026-07-29
---
# **Extension Model**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

SAGIHA is intended to be used and extended by people who did not write it — including other agents.
That requires a sanctioned path for adding an adapter, a tool, or a skill **without forking the
repository**.

That requirement sits in obvious tension with
[ADR-0004](../08-decisions/0004-no-di-container.md), which rejects DI containers and runtime plugin
discovery because dynamic wiring defeats the static analysis this codebase's LLM maintainer depends
on. If the only sanctioned wiring is "edit `build_kernel()`," then every extension is a pull request
and every extender becomes a maintainer of this repository.

The tension is real but the binary is false. [ADR-0013](../08-decisions/0013-extension-registration.md)
takes a third option — declarative registration resolved once at composition — which **amends ADR-0004
without reversing it**. Static navigability is preserved in full.

## **Registration: declared, resolved once, then frozen**

Extensions register through Python packaging entry points, in the **extender's** `pyproject.toml`:

```toml
[project.entry-points."sagiha.adapters"]
qdrant_indexer = "myorg_sagiha_qdrant:QdrantIndexer"

[project.entry-points."sagiha.tools"]
jira = "myorg_sagiha_jira:jira_tool"

[project.entry-points."sagiha.skills"]
django_orm = "myorg_sagiha_django:skill"
```

At startup the composition root resolves each declared entry point exactly once, validates it against
the port's `Protocol`, records it in the run manifest, and **freezes the registry**. Nothing is
discovered afterward; nothing is registered at runtime.

This is not the plugin discovery ADR-0004 rejected:

| ADR-0004 rejected | This mechanism |
| :--- | :--- |
| Scanning the filesystem for implementations | Reading a declaration the extender wrote explicitly |
| Types invisible to the checker | The extender's package is a real import; pyright resolves it |
| "Go to definition" fails | Works — the target is an ordinary module path |
| Wiring inferred, unauditable | `sagiha extensions list` prints the resolved set; it is in the run manifest |
| Registration at arbitrary runtime moments | One resolution pass at composition, then immutable |

Config can pin, override, or disable any of it, so the operator retains final say:

```toml
[extensions]
enabled  = ["qdrant_indexer", "jira"]     # empty list = core only
disabled = ["django_orm"]
```

## **The Four Surfaces**

Extension is **additive within the hexagon, never a hole through it**. No surface may define a new
port, reach past a port boundary, or widen authority.

| Surface | What it is | Entry-point group | Constraint |
| :--- | :--- | :--- | :--- |
| **Adapter** | An implementation of an existing port | `sagiha.adapters` | Must pass that port's conformance suite before it is usable. Cannot define new ports. |
| **Tool** | A new capability in the registry | `sagiha.tools` | Declares an `EffectClass` and a required grant. Policy-gated at the dispatch choke point like every other tool. |
| **Skill** | Instructions + optional tool bundle, progressively disclosed | `sagiha.skills` | Content is `EXTERNAL` provenance by default. Cannot bypass policy. |
| **Hook** | Observer or interceptor on the event bus | declared in `config.toml` | Observers cannot influence execution; interceptors may deny, never mutate. See [Event Bus & Hooks](./event-bus-and-hooks.md). |

### Adapters

The conformance suite is the admission gate, not a review. A new adapter is not "done" until it
appears in the port's parametrization in `tests/contracts/` and passes **unchanged** — that is the
operational meaning of swappable.

Third-party adapters run the same suite: `sagiha conformance --port indexer --adapter myorg:QdrantIndexer`.
An adapter that fails is refused at composition with the failing test named, not loaded and left to
break mid-run.

### Tools

A third-party tool is exactly as privileged as a built-in one, which is to say: not at all until
`PolicyEngine` says so. It declares its effect class and required grant at registration; both are
enforced at dispatch. `EffectClass` must be honest, because replay dispatches on it — a tool that
mutates state while declaring `PURE` corrupts replay, and its conformance test asserts the
declaration matches observed behavior under record/replay.

Tools count against the tool budget. A large tool namespace degrades model selection accuracy, so
adding twelve tools is a cost, not a feature.

### Skills

A **skill** is a versioned bundle of instructions — and optionally tools and reference files — that
teaches the agent a procedure it does not know: an internal deployment process, a house testing
convention, a domain API's idioms.

Skills are named throughout this tree and, until now, contracted nowhere. The contract:

```
myorg_sagiha_django/
├── skill.toml          # name, version, description, trigger, required tools
├── SKILL.md            # the instructions themselves
└── references/         # loaded on demand, never eagerly
```

```toml
name        = "django_orm"
version     = "1.2.0"
description = "House conventions for Django ORM queries and migrations."
trigger     = "editing models.py, writing migrations, or reviewing querysets"
tools       = ["run_migrations"]
```

**Progressive disclosure is the load-bearing property.** Only `name` + `description` + `trigger` — a
few dozen tokens — sit in the prompt by default. `SKILL.md` loads when the trigger matches;
`references/` loads only when the skill asks for it. Ten installed skills cost a few hundred tokens,
not ten full documents.

**Prompt placement is layer 5** of the [prompt architecture](./prompt-architecture.md): after the
stable system prefix and tool definitions, before the conversation tail. Skill *descriptors* are
cache-stable and belong in the prefix; expanded skill *bodies* are appended after the cache
breakpoint, because loading one mid-run must not invalidate the prefix.

**Trust**: skill content is `EXTERNAL` provenance by default and carries no authority to widen
permissions. A skill that says "you may skip the test gate" is text the agent read, not policy — the
gate is enforced in the kernel, which never consults a skill. Skills authored in the operator's own
repository may be marked `OPERATOR` in config; installed third-party skills may not.

### Hooks

Unchanged from [Event Bus & Hooks](./event-bus-and-hooks.md), and repeated here only as the boundary:
hooks may **narrow** authority, never widen it. `pre_tool` supplements `PolicyEngine`; it never
replaces it. A hook that could grant permission would reintroduce exactly the bypass the
[CAR model](./car-model.md) exists to prevent.

## **What Extensions Can Never Do**

| Forbidden | Why |
| :--- | :--- |
| Define a new port | Ports are the architecture. A third party adding one forks the contract surface, and every consumer of that port would live outside conformance. |
| Reach past a port boundary | Extension is additive within the hexagon, not a hole through it. |
| Grant themselves capability | Only `PolicyEngine` mints grants, and grants never leave `kernel/dispatch.py`. |
| Modify the trusted computing base | Policy engine, evaluator, benchmark definitions, and the deployment gate are outside every writable surface — see [ADR-0007](../08-decisions/0007-trusted-computing-base.md). |
| Register after composition | The registry is frozen. A run's extension set is fixed at start and recorded in the manifest, or replay is not reproducible. |

That last row is what makes an extension-bearing run auditable: the manifest records every extension
name, version, and resolved entry point, so a trajectory replays against the same code that produced
it.

## **Versioning**

Extensions depend on port contracts, which are versioned. See
[Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md) — an
extension declares the port major version it implements, and composition refuses a mismatch loudly at
startup rather than failing at first dispatch.
