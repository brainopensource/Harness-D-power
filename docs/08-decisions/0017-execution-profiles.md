---
status: normative
updated: 2026-07-29
---
# ADR-0017: Execution Profiles Over Task-Type Branching

**Status**: Accepted  
**Date**: 2026-07-29  

## Context

Treating every task as a coding task forces full worktree allocation, container startup, and language-server indexing—even for simple chat, analysis, or code review tasks. Adding a `task_type` enum with kernel branch points was considered but rejected.

## Decision

`TaskSpec` carries **`profile: str = "coding"`**, resolved at composition against a registry of profiles defined in configuration.

Profiles declare bound optional ports (`Workspace`, `Toolchain`, `Evaluator`), available tools, model roles, and admission criteria. Four profiles ship standard: `coding`, `analysis`, `review`, and `chat` (extendable via `sagiha.profiles` entry points).

### Core Rules
1. **Profiles compose ports; the kernel never branches on them.** No `if profile == ...` in orchestrator.
2. **`gates = "none"` produces no `GateReport` and emits no `gate.evaluated`.**
3. **Profiles subtract capability, never supervision.** All profiles pass through the same `PolicyEngine` choke point and TCB boundary.

Using `str` rather than an `enum` keeps the extension surface open.

## Consequences

- **Easy**: Non-coding tasks (chat, review) bypass filesystem overhead and return in a single model call.
- **Hard**: Consumers of `GateReport` must handle `None`.
- **Downgrade**: Tasks with `gates = "none"` terminate on model completion signal without independent verification (profile recorded in `run.started` to prevent mistaking ungated runs for gated ones).
- **Forecloses**: Nothing.

## Alternatives Considered

- **`task_type` enum with kernel branch points**: Rejected because new task shapes would require kernel modifications and enum changes, violating [ADR-0013](./0013-extension-registration.md).
- **Separate entry points per task shape** (`execute_chat`, `execute_task`): Rejected as it breaks the unified headless boundary and splits event streams.
- **Do nothing (run all tasks through coding pipeline)**: Rejected due to unnecessary resource waste.

## Reversal Conditions

- Profile count expands excessively (>12) or begins encoding per-customer behavior.
- Any profile requires a kernel control-flow branch.
- Evidence shows ungated profiles are used inappropriately for tasks requiring gating.
