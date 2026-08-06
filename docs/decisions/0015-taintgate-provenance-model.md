---
status: normative
updated: 2026-08-06
---
# ADR-0015: The TaintGate Provenance Model

**Status**: Accepted · **Date**: 2026-08-06 · **Fork**: raised by the Phase 0 lock audit

## Context

Prompt injection is one of the four named failure modes in [`../vision.md`](../vision.md) §2 —
*"the agent is an untrusted actor executing code it wrote, over content it did not write"* — and
injection resistance is a stated differentiator. Before this ADR the entire defence was one
sentence in the spec: *"The TaintGate is deterministic."*

Deterministic in what. Over what labels. Propagating how. Enforced where, and against which
predicate. **One sentence is not a design**, and the gap was invisible because the sentence
sounded like one.

The audit also found the mechanism conflated with a different one: a single backlog task covered
both the shell-AST classifier and the TaintGate. They are different mechanisms at different
layers — the classifier reads a command string in `kernel/`, the gate labels context spans in
`agency/context/` — and merging them means neither gets designed.

## Decision

### Labels

Every context span carries exactly one provenance label. Spans are the atoms of the gate and are
**never merged across labels**.

| Label | Applied to |
| :--- | :--- |
| `trusted-system` | System prompt, policy text, standing instructions |
| `operator` | Direct human input through the CLI or TUI |
| `agent` | The agent's own prior outputs, derived only from trusted spans |
| `untrusted-external` | Repository files · issue text · tool stdout · test output · web and MCP results |
| `untrusted-derived` | Any model output computed over an untrusted span |

**Labelling happens at birth**, at the adapter boundary, not at the point of use. A tool result
is `untrusted-external` when it is constructed; nothing downstream has to remember to mark it.

### Propagation

Deterministic and monotone:

> A completion that consumed **any** span in `{untrusted-external, untrusted-derived}` produces
> `untrusted-derived` output. Otherwise it produces `agent`.

There is no declassification path, no confidence threshold, and no model in the loop. A
classifier that decides whether text is "really" an instruction is a model deciding whether to
trust its own input, which is the problem, not the solution.

### The binding rule

> **A request that grants or widens capability fails closed when any span justifying it is
> `untrusted-external` or `untrusted-derived`.**

**The gate labels; the policy decides.** Propagation lives in `agency/context/taint_gate.py`;
the enforcing predicate lives in the `PolicyEngine` inside `kernel/` — TCB. Enforcement must not
sit in the mutable layer alongside the thing it constrains.

Untrusted content may **inform** work — the agent must read the repository, and refusing to
would make the harness useless. It may not **authorize** it. An issue body reading *"also run
`curl … | sh`"* produces an effect request whose justifying spans are `untrusted-external`, and
the predicate fails closed.

### Enforcement

A **pinned injection corpus in CI**, whose gate is **zero capability grants**. The corpus is TCB
data — a defence whose test set is editable by the thing it defends against is not a defence.
The gate ships with a test proving it can fail: a deliberately permissive predicate must make the
corpus produce a grant.

## Consequences

- Every port payload that carries content carries `TaintSpan`s rather than bare strings. This is
  why the label set is fixed now: retrofitting provenance through a port surface is the kind of
  change I3 exists to make cheap and nothing makes free.
- **Retrieved memories re-enter as `untrusted-derived`.** A memory poisoned by injected content
  must not launder into authority by aging — this is the constraint the growth-tier `Memory` port
  is designed against.
- MCP tool outputs are `untrusted-external` like any tool output
  ([ADR-0016](./0016-mcp-integration-trust-model.md)).
- The shell-AST classifier ([ADR-0008](./0008-shell-ast-classifies.md)) supplies the
  `widens_capability` flag the predicate reads. It classifies; it still does not contain.
- Some legitimate work will fail closed. That is the intended direction of the error, and the
  escalation taxonomy (`Reject | AskRuleMatch | AskFailClosed`) is where a human resolves it.

## Reversal Conditions

**None on the binding rule.** An untrusted span acquiring capability is the failure this exists
to prevent, and a rule with an exemption is a rule with an exploit.

Revisable, with an audit trail: the corpus contents, the escalation taxonomy's routing, and
whether a specific effect class counts as capability-widening. **Not revisable**: that the
predicate is evaluated in the TCB, and that propagation is deterministic rather than learned.
