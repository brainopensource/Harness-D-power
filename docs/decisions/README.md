---
status: normative
updated: 2026-08-05
---
# Architecture Decision Records

Binding decisions, each with an explicit **reversal condition**.

**A decision without a reversal condition is a preference with better formatting.** The
competing Phase 0 proposal set carried fourteen ADRs and zero reversal conditions; that is
the single most fixable process gap Phase 0 produced, and it is closed here.

**Status values:** `Accepted` · `Accepted (provisional)` · `Superseded by ADR-XXXX` ·
`Deprecated`

*Provisional* means the decision is in force **and** names a measurement that will confirm or
overturn it. It is not a weaker decision — it is an honest one.

## Log

| ADR | Decision | Fork | Status |
| :--- | :--- | :--- | :--- |
| [0001](./0001-python-first-compiled-on-trigger.md) | Python-first; compiled sidecars only on a measured trigger | F1 | **Provisional** |
| [0002](./0002-no-number-before-the-floor.md) | No capability number is published before the A/A floor | F2 | Accepted |
| [0003](./0003-statistical-admission-protocol.md) | Exact McNemar, Holm–Bonferroni, **derived N** | F3 | Accepted · **rev. 2** |
| [0004](./0004-benchmark-targets.md) | Lift is the committed target; absolutes are provisional | F4 | **Provisional** |
| [0005](./0005-eight-ports-adapter-first.md) | Eight ports; a port arrives with its first adapter | F5 | Accepted · **rev. 2** |
| [0006](./0006-tcb-boundary-and-meta-loop-authority.md) | The TCB boundary, and what the meta-loop may commit | F6 | Accepted |
| [0007](./0007-architect-editor-seam.md) | The Architect/Editor seam is built and ships off | F7 | Accepted |
| [0008](./0008-shell-ast-classifies.md) | Shell AST classifies; the sandbox contains | F8 | Accepted |
| [0009](./0009-gates-are-the-schedule.md) | Exit gates are the schedule; durations are tripwires | F9 | Accepted |
| [0010](./0010-context-prefix-layers.md) | Five prefix layers, enumerated; the generated repo layer is ablated early at M2 | F10 | **Provisional** |
| [0011](./0011-no-lsp-adapter.md) | No LSP adapter; tree-sitter plus the project's own toolchain | F11 | Accepted |
| [0012](./0012-ip-protection-is-packaging.md) | Compiled packaging is packaging, not architecture | F12 | Accepted |
| [0013](./0013-workflow-dag-phased.md) | The workflow DAG lands in four phases | DAG | Accepted · **rev. 2** |
| [0014](./0014-workflow-topology-is-data.md) | Workflow topology is hash-pinned data, not code | lock audit | Accepted |
| [0015](./0015-taintgate-provenance-model.md) | Provenance labels; untrusted spans never grant capability | lock audit | Accepted |
| [0016](./0016-mcp-integration-trust-model.md) | MCP is one `ToolRegistry` adapter; its output is untrusted | lock audit | Accepted |
| [0017](./0017-subagent-capability-attenuation.md) | A sub-agent is a subgraph; capabilities only narrow | lock audit | Accepted |
| [0018](./0018-agency-below-workflow.md) | `agency/` sits below `workflow/`, not beside it | abstraction audit | **Proposed** |
| [0019](./0019-three-horizons-harness-framework-metaloop.md) | Three horizons: harness → framework → meta-loop, in that order | what this project is | Accepted |
| [0020](./0020-verdict-capability-and-judge-integrity.md) | `Verdict` is a closed capability; I7/I9 restated for non-test judges | F-0019 | Accepted |
| [0021](./0021-extension-contract-and-trust.md) | Capability is declared; data cannot widen capability; install ≠ trust | F-0019 | Accepted |

**0019–0021 resolve what the project is.** Every document before them described a SWE-bench
harness while the goal was a self-improving framework — a gap that was not rhetorical: `Task`
was a SWE-bench record, the judge was a test runner, and `check_evaluator_termination` made
non-benchmark topologies structurally unexpressible. 0019 chooses, 0020 generalises the judge
**without relaxing I7 or I9**, and 0021 defines how others extend the system without acquiring
the ability to grade it. Designs: [`architecture/`](../architecture/).

**0016 and 0017 are decided now and built later** — at growth tier and M3+ respectively. Deciding
costs a page; building prematurely costs velocity, and [ADR-0005](./0005-eight-ports-adapter-first.md)
forbids the ports anyway. This is [ADR-0007](./0007-architect-editor-seam.md)'s pattern — settle the
shape, ship nothing — applied at roadmap scale.

## Amendments (2026-08-06, the Phase 0 lock)

Four ADRs were revised rather than superseded, because in each case the decision held and its
implementation was under-specified. The trail is [`../PHASE-0-LOCK.md`](../PHASE-0-LOCK.md).

| ADR | What changed | Why |
| :--- | :--- | :--- |
| **0003 → rev. 2** | N is **derived** for ≥ 0.80 power, not fixed at 50; pass@1 aggregation rule; family declared mechanically; cost criterion is **per resolved task** | At N = 50 the protocol detected its own committed target 12–32% of the time — 4–10% after Holm. It was an engine for rejecting true wins, and its cost criterion contradicted [0007](./0007-architect-editor-seam.md) |
| **0005 → rev. 2** | A mock adapter satisfies the entry rule **only with the first real adapter named** | The rule and the first sprint disagreed: nine protocols, one funded adapter |
| **0010** | The five layers are **enumerated**; the gated metric is harness-side **prefix stability** | A gated invariant over a structure defined nowhere is not enforceable, and a provider-reported hit rate is unmeasurable on the reference endpoint |
| **0013 → rev. 2** | The **bounded repair edge** — `evaluate →(fail, k)→ repair → apply` | The pipeline terminated on first evaluation, so the lever [`../vision.md`](../vision.md) calls the largest in the system had no node, no gate and no task |

## The three that are still open questions

ADR-0001, ADR-0004 and ADR-0010 are decided but not settled. Each is in force and each names
what would overturn it:

| ADR | Decided on | Overturned by |
| :--- | :--- | :--- |
| **0001** | The absence of a measurement on either side | Two timers, one afternoon |
| **0004** | Unverified single-session leaderboard research | Independent re-verification |
| **0010** | Published evidence that generated context may be negative-value | The **second** M2 ablation — the repair ablation now goes first |

**This is the intended state.** Deciding them "firmly" would not have made them more true —
it would have hidden which ones to go and measure first.

## Writing a new one

Match the existing shape: **Context** (what was contested and what the evidence said) ·
**Decision** · **Consequences** · **Reversal Conditions**. Keep it short — ADRs are exempt
from the word budget precisely because each one *replaces* long-form derivation elsewhere,
and that exemption is abused by writing an essay.

Where a decision can be a contract in code, write the contract and let the ADR point at it.

**How these decisions were reached:** [`../concepts/`](../concepts/README.md) — the audit
register, the corrected brief, and the decision record. That trail is history and is not
maintained.
