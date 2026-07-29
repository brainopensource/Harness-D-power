---
status: normative
updated: 2026-07-29
---

# **Execution Profiles**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

Everything else in this tree assumes the task is a coding task: a run allocates a worktree,
materializes it, runs a toolchain, and produces a `GateReport`. That is the right default and it is
not the only shape of work an LLM harness is asked to do.

Using SAGIHA to explain an architecture, answer a question about a codebase, review a pull request, or
carry a conversation currently pays for worktree materialization, container startup, and language-server
indexing before it can emit a single token — for work that touches no files. The overhead is not a
rounding error: on a two-turn question it is the overwhelming majority of wall-clock.

An **execution profile** is the mechanism that makes coding *one* configuration of the harness rather
than the only one.

## **What a Profile Is**

A profile declares **what a run mounts** and **what admits its result**. It is data, resolved at
composition, not a branch in the kernel.

| Profile | Workspace | Toolchain | Gates | Typical use |
| :--- | :--- | :--- | :--- | :--- |
| **`coding`** *(default)* | worktree, writable | full | full `GateReport` | The pipeline every other doc describes. Unchanged. |
| **`analysis`** | read-only, no worktree | read-only (typecheck, lint) | acceptance criteria only | Code explanation, architecture Q&A, impact assessment |
| **`review`** | read-only + a diff under review | typecheck, lint | `Reviewer` soft score, **no hard gate** | PR review bot |
| **`chat`** | none | none | none | Conversational, tool-light, no repository access |

```toml
[profiles.coding]
workspace   = "worktree"     # worktree | readonly | none
toolchain   = "full"         # full | readonly | none
gates       = "full"         # full | acceptance_only | none
model_role  = "workhorse"
tools       = ["*"]

[profiles.chat]
workspace   = "none"
toolchain   = "none"
gates       = "none"
model_role  = "fast"
tools       = ["recall", "remember", "web_search"]
```

## **Profiles Compose Ports — They Do Not Branch Logic**

This is the load-bearing property, and it is what separates this design from a `task_type` enum.

A profile resolves to a **set of bound ports** plus an admission policy. The orchestrator's loop is
byte-identical across profiles: it assembles context, calls the model, dispatches tools, and emits
events. Under `chat` there is simply no `Workspace` bound and no `Evaluator` bound, so there is
nothing to materialize and nothing to gate.

```
TaskSpec.profile ─→ composition root ─→ bound ports for this run
                                        ├─ Workspace?   (coding: worktree | analysis: readonly | chat: —)
                                        ├─ Toolchain?   (coding: full     | analysis: readonly | chat: —)
                                        ├─ Evaluator?   (coding: yes      | analysis: yes      | chat: —)
                                        └─ tool subset
```

The kernel contains **no `if profile == "chat"`**. If a proposed profile requires one, the profile
model is wrong for that case — the same test [Entry Points](./entry-points-and-piloting.md) applies to
channels.

Ports a profile may leave unbound are marked **optional** in the
[port index](../03-contracts-and-models/hexagonal-ports.md). Every other port — `ModelProvider`,
`PolicyEngine`, `ResourceGovernor`, `ToolRegistry`, `TrajectoryStore`, `EventBus` — is bound in every
profile without exception. Those are the harness; the rest is what the harness is being pointed at.

## **Degenerate Gates Are Defined, Not Accidental**

`GateReport.acceptance_met` is `all(c.passed for c in criteria if c.required)`, which is **vacuously
true on an empty tuple**. A profile with no gates must therefore *not* produce a `GateReport` at all.

> **Rule**: when `gates = "none"`, no `GateReport` is constructed and **`gate.evaluated` is never
> emitted**. A run under such a profile terminates with `run.completed` carrying `gate_report: None`.

The alternative — emitting an empty report whose `admitted` property evaluates to `True` — would be
the most dangerous artifact this change could introduce: a downstream consumer, a benchmark reporter,
or the outer loop would read "admitted" and count a chat turn as a passed coding task. Absence of a
verdict and a verdict of "pass" must never be representable by the same value.

`gates = "acceptance_only"` produces a `GateReport` whose `criteria` are evaluated and whose
code-specific booleans (`tests_unmodified`, `coverage_not_decreased`, `diff_within_bounds`,
`no_new_suppressions`) are **omitted rather than defaulted to `True`** — for the same reason.

## **Security Is Profile-Independent**

A profile narrows what is mounted. It can never widen authority.

| Invariant | Holds under every profile |
| :--- | :--- |
| Single dispatch choke point | ✅ Every tool call, in every profile, passes `PolicyEngine.authorize()` |
| `always_gate` list | ✅ Config cannot empty it, and no profile can bypass it |
| TCB write boundary | ✅ [ADR-0007](../08-decisions/0007-trusted-computing-base.md) is unaffected |
| Provenance and untrusted-data wrapping | ✅ `chat` reaching the web is the *highest*-risk injection path, not an exempt one |
| Grants never leave dispatch | ✅ Structural |

`chat` is safe because it **has no shell**, not because a check was skipped. That distinction matters:
a profile that omitted the policy check while keeping the tools would be a privilege-escalation
surface with a friendly name. Profiles subtract capability, never supervision.

One consequence worth stating: a profile with `workspace = "none"` is *safer* than `coding`, so
autonomy levels that would be refused for `coding` may be acceptable here. That is a policy decision
recorded in config, not an inference the kernel makes on its own.

## **Profiles Are an Extension Surface**

Third parties ship a profile through `sagiha.profiles` entry points, under the same
resolve-once-then-freeze lifecycle as every other extension
([ADR-0013](../08-decisions/0013-extension-registration.md)):

```toml
[project.entry-points."sagiha.profiles"]
scrum_master = "myorg_sagiha_scrum:profile"
```

A profile may only compose ports that already exist and select from tools already registered. It
cannot define a new port, grant itself capability, or alter gate semantics — the constraints that
apply to every extension surface apply here unchanged. This is the whole reason profiles are config
rather than an enum: **"SAGIHA is used as an English tutor" should not require a kernel change**, and
under a closed `Literal[...]` it would.

## **What Profiles Do Not Solve**

* **They are not a permission system.** `PolicyEngine` is. A profile that binds a read-only workspace
  still authorizes every read.
* **They do not make an unverified result verified.** A task under `gates = "none"` terminates on the
  model's own completion signal — see [Task & Acceptance](../03-contracts-and-models/task-and-acceptance.md).
  That is a real epistemic downgrade and it is why `coding` remains the default.
* **They do not partition memory.** A `chat` run and a `coding` run against the same repository share
  the same `Memory` and the same trajectory store, which is the point — the harness accumulates
  context across the ways it is used.

## **Related**

[Composition & Configuration](../05-tech-stack/composition-and-configuration.md) for resolution and
layering · [ADR-0017](../08-decisions/0017-execution-profiles.md) for the decision and its alternatives
· [Event Catalog](../04-workflows-and-loops/event-catalog.md) for which events are profile-dependent.
