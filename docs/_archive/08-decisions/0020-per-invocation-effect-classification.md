---
status: historical
updated: 2026-07-31
---
# ADR-0020: Per-Invocation Effect Classification, With the Allowlist in the TCB

**Status**: Accepted-Implemented  
**Date**: 2026-07-31  

## Context

`EffectClass` was assigned per-tool rather than per-invocation. Because `run_command` was marked `DESTRUCTIVE`, `replay --verify` ([ADR-0012](./0012-record-replay-determinism.md)) served all commands (`git status`, `ls`, etc.) from recordings rather than re-executing read operations. 

Per-invocation classification resolves this, but requires placing the decision function where agents cannot tamper with re-execution boundaries.

## Decision

1. **Allowlist lives in TCB (`src/sagiha/kernel/policy/effects.py`)**:
   Enforced via `tcb-isolation` and `tcb-check` CI rules, making classification logic agent-unwritable without adding new infrastructure.
   ```python
   PURE_ARGV: Final[frozenset[str]] = frozenset({"ls", "cat", "head", "tail", "wc", "git"})
   PURE_GIT_OPS: Final[frozenset[str]] = frozenset({"status", "diff", "log", "show", "blame"})
   MUTATION_TOOLS: Final[frozenset[str]] = frozenset({"apply_edit", "write_file", "run_command"})


   def classify_command(argv: Sequence[str], declared: EffectClass) -> EffectClass:
       """Narrow a declared DESTRUCTIVE to PURE for allowlisted read-only argv."""
   ```
2. **Function NEVER widens**: Narrows `DESTRUCTIVE` to `PURE` for allowlisted read-only commands; unmatched commands remain unchanged. `bash -lc` is never narrowed.
3. **Wired in `agency`**: `agency/run_loop.py` and `GateEvaluator` construct `ToolCall.effect` via `classify_command`. `ToolRegistry` gains `effect_for_call(call_args) -> EffectClass` (`PORT_VERSION = 2`).
4. **Zero Replay Format Changes**: Recorded per-call `EffectClass` is read directly during replay to re-execute newly `PURE` commands.

## Consequences

- **Easy**: `replay --verify` becomes a genuine workspace check. Target metric: **≥60% of steps re-executed**.
- **Hard**: Allowlist additions require human-authored TCB diffs.
- **Foreclosed**: Model-based or automated effect classification.
- **Risk Accepted**: Sandboxed binary shadowing is bounded by `v2-S5` container perimeters.

## Reversal Conditions

- Allowlist churn becomes excessive (warranting adapter-declared rules).
- A `PURE`-classified command mutates workspace state.
- The 60% re-execution target is not achieved.

## Related

[ADR-0007](./0007-trusted-computing-base.md) · [ADR-0012](./0012-record-replay-determinism.md) · [Security & Threat Model](../02-architecture/security-and-threat-model.md) · [Tool Catalog](../03-contracts-and-models/tool-catalog.md)
