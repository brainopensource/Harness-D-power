---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Execution Profiles**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Overview**

An **execution profile** defines what a run mounts and what evaluates its result. Profiles allow non-coding tasks (Q&A, analysis, code review, chat) to run without worktree materialization or container overhead.

## **Profile Definitions**

| Profile | Workspace | Toolchain | Gates | Typical Use |
| :--- | :--- | :--- | :--- | :--- |
| **`coding`** *(default)* | Writable worktree | Full | Full `GateReport` | Code generation & modification |
| **`analysis`** | Read-only, no worktree | Read-only | Acceptance criteria only | Q&A, impact analysis, doc search |
| **`review`** | Read-only + target diff | Read-only | `Reviewer` soft score (no hard gate) | Pull request code review |
| **`chat`** | None | None | None | Conversational, tool-light interactions |

```toml
[profiles.coding]
workspace = "worktree"
toolchain = "full"
gates     = "full"
tools     = ["*"]

[profiles.chat]
workspace = "none"
toolchain = "none"
gates     = "none"
tools     = ["recall", "remember", "web_search"]
```

## **Port Composition Without Kernel Branching**

Profiles resolve at composition time to specific bound ports. The orchestrator loop remains byte-identical across profiles without kernel-level `if profile == ...` branching:

```
TaskSpec.profile ─→ composition root ─→ bound ports for run
                                        ├─ Workspace?   (coding: worktree | analysis: readonly | chat: —)
                                        ├─ Toolchain?   (coding: full     | analysis: readonly | chat: —)
                                        ├─ Evaluator?   (coding: yes      | analysis: yes      | chat: —)
                                        └─ Tool subset
```

Mandatory ports bound under **all** profiles: `ModelProvider`, `PolicyEngine`, `ResourceGovernor`, `ToolRegistry`, `TrajectoryStore`, `EventBus`. See [Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md).

## **Gate Evaluation Rules**

* **`gates = "none"`**: No `GateReport` is generated, `gate.evaluated` is omitted, and `RunCompleted` sets `gate_report: None`. Absence of a verdict must never evaluate as a passed gate.
* **`gates = "acceptance_only"`**: Generates `GateReport` with criteria evaluated, omitting code-specific assertions (`tests_unmodified`, `coverage_not_decreased`).

## **Security Invariants**

Profiles can only subtract capability; they can never bypass policy or widen authority:

1. **Single Dispatch Choke Point**: All tool calls pass `PolicyEngine.authorize()`.
2. **Immutability of `always_gate`**: Profiles cannot clear strict gate rules.
3. **TCB Protection**: Preserves boundaries from [ADR-0007](../08-decisions/0007-trusted-computing-base.md).
4. **Untrusted Data Isolation**: Chat-based web searches remain wrapped in provenance checks.

## **Extension Surface**

Profiles register via `sagiha.profiles` Python entry points per [ADR-0013](../08-decisions/0013-extension-registration.md):

```toml
[project.entry-points."sagiha.profiles"]
scrum_master = "myorg_sagiha_scrum:profile"
```

## **Related References**

* [Composition & Configuration](../05-tech-stack/composition-and-configuration.md)
* [ADR-0017: Execution Profiles](../08-decisions/0017-execution-profiles.md)
* [Task & Acceptance](../03-contracts-and-models/task-and-acceptance.md)
* [Event Catalog](../04-workflows-and-loops/event-catalog.md)
