---
status: normative
updated: 2026-07-31
---

# ADR-0020: Per-Invocation Effect Classification, With the Allowlist in the TCB

**Status**: Accepted
**Date**: 2026-07-31

## Context

`EffectClass` is assigned **per tool**, not per call. `run_command` is registered `DESTRUCTIVE`,
because it can be. The consequence under [ADR-0012](./0012-record-replay-determinism.md) is that
`replay --verify` serves every `run_command` from the recording rather than re-executing it.

But most `run_command` invocations in a real trajectory are `git status`, `git diff`, `ls`, `wc` —
reads. Serving those from a recording means replay verifies almost nothing about the workspace: it
confirms the harness produced the same request, not that the workspace is in the same state. The
verification is weakest exactly where it would be cheapest to make strong.

Classifying per invocation fixes this, but introduces a new question: **who decides?** A narrowing
function is a security-relevant decision — narrowing `DESTRUCTIVE` to `PURE` says "it is safe to
re-execute this". If an agent can edit that function, it can widen its own re-execution surface,
and the RHI mutable-surface rules would have to grow a new exception.

## Decision

**1. The allowlist lives in `src/sagiha/kernel/policy/effects.py`.** This placement is the whole
mechanism. The `tcb-isolation` import contract already forbids `kernel.policy` from importing
`agency`, `aoi`, or `adapters`, and CI's `tcb-check` already hard-fails an agent-authored diff
touching `kernel/policy/**`. Putting the allowlist there makes it **agent-unwritable for free** —
no new gate, no new CI job, no new concept.

```python
PURE_ARGV: Final[frozenset[str]] = frozenset({"ls", "cat", "head", "tail", "wc", "git"})
PURE_GIT_OPS: Final[frozenset[str]] = frozenset({"status", "diff", "log", "show", "blame"})
MUTATION_TOOLS: Final[frozenset[str]] = frozenset({"apply_edit", "write_file", "run_command"})


def classify_command(argv: Sequence[str], declared: EffectClass) -> EffectClass:
    """Narrow a declared DESTRUCTIVE to PURE for allowlisted read-only argv."""
```

**2. The function NEVER widens.** It narrows or it returns `declared` unchanged. Anything unmatched
keeps its declared class. `bash -lc` is never narrowed, because the argv of a shell invocation says
nothing about what the shell will do — the same reasoning as
[T2](../02-architecture/security-and-threat-model.md): if the agent has a shell, argv inspection is
theatre.

**3. Wiring is in `agency`, not the registry.** `DefaultToolRegistry.dispatch` is the wrong place —
adapters are not TCB, so classifying there would put the decision back in mutable code. Instead
`agency/run_loop.py` and `GateEvaluator` construct `ToolCall.effect` via
`classify_command(args["command"], registry_effect)` when `tool_name == "run_command"`.
`ToolRegistry` gains `effect_for_call(call_args) -> EffectClass` as the extension seam
(`PORT_VERSION = 2`), defaulting to `get_effect_class` + `classify_command`.

**4. Replay needs zero changes.** `ToolCall.effect` is already recorded per call in the trajectory.
Replay reads the recorded per-call class and simply starts re-executing the newly-`PURE` majority.
No cassette format change, no migration.

## Consequences

**Easy.** `replay --verify` becomes a real workspace check rather than a request-digest check.
**Exit metric: ≥60% of steps re-executed** under `replay --verify` on the pinned suite, up from
approximately zero for command steps.

**Hard.** The allowlist is a maintained artifact. Every addition is a TCB diff requiring human
authorship — deliberately, because that is the cost of the guarantee.

**Foreclosed.** Automatic or model-proposed classification. A model that can argue a command is
pure can argue it about `rm`.

**Risk accepted.** An allowlisted binary shadowed by something malicious on `PATH` inside the
sandbox would be re-executed as pure. This is bounded by the `v2-S5` container perimeter and is not
a new exposure: the command already ran once, live, when it was recorded.

## Reversal Conditions

* **The allowlist churns.** More than a handful of additions per phase means argv is the wrong
  granularity, and classification should move to a declared per-tool `effect_for_call` implemented
  by each adapter with the TCB holding only the *rules*.
* **A narrowing proves wrong.** Any single case where a `PURE`-classified command mutated the
  workspace invalidates the argv approach outright, not just that entry. Remove the mechanism and
  keep per-tool classification.
* **The 60% metric is not met.** If re-execution stays low after this lands, the bottleneck was
  never effect classification and this complexity is not paying for itself.

## Related

[ADR-0007](./0007-trusted-computing-base.md) (TCB) ·
[ADR-0012](./0012-record-replay-determinism.md) (record/replay determinism) ·
[Security & Threat Model](../02-architecture/security-and-threat-model.md) (T2, T5) ·
[Tool Catalog](../03-contracts-and-models/tool-catalog.md)
