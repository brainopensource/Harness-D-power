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
| [0001](./0001-python-first-compiled-on-trigger.md) | Python-first; compiled sidecars only on a measured trigger | F1 | Accepted |
| [0002](./0002-no-number-before-the-floor.md) | No capability number is published before the A/A floor | F2 | Accepted |
| [0003](./0003-statistical-admission-protocol.md) | Exact McNemar, Holm–Bonferroni, N ≥ 50 | F3 | Accepted |
| [0004](./0004-benchmark-targets.md) | Lift is the committed target; absolutes are provisional | F4 | **Provisional** |
| [0005](./0005-eight-ports-adapter-first.md) | Eight ports; a port arrives with its first adapter | F5 | Accepted |
| [0006](./0006-tcb-boundary-and-meta-loop-authority.md) | The TCB boundary, and what the meta-loop may commit | F6 | Accepted |
| [0007](./0007-architect-editor-seam.md) | The Architect/Editor seam is built and ships off | F7 | Accepted |
| [0008](./0008-shell-ast-classifies.md) | Shell AST classifies; the sandbox contains | F8 | Accepted |
| [0009](./0009-gates-are-the-schedule.md) | Exit gates are the schedule; durations are tripwires | F9 | Accepted |
| [0010](./0010-context-prefix-layers.md) | Five prefix layers; the generated repo layer is the first M2 ablation | F10 | **Provisional** |
| [0011](./0011-no-lsp-adapter.md) | No LSP adapter; tree-sitter plus the project's own toolchain | F11 | Accepted |
| [0012](./0012-ip-protection-is-packaging.md) | Compiled packaging is packaging, not architecture | F12 | Accepted |
| [0013](./0013-workflow-dag-phased.md) | The workflow DAG lands in four phases | DAG | Accepted |

## The three that are still open questions

ADR-0001, ADR-0004 and ADR-0010 are decided but not settled. Each is in force and each names
what would overturn it:

| ADR | Decided on | Overturned by |
| :--- | :--- | :--- |
| **0001** | The absence of a measurement on either side | Two timers, one afternoon |
| **0004** | Unverified single-session leaderboard research | Independent re-verification |
| **0010** | Published evidence that generated context may be negative-value | The first M2 ablation |

**This is the intended state.** Deciding them "firmly" would not have made them more true —
it would have hidden which ones to go and measure first.

## Writing a new one

Match the existing shape: **Context** (what was contested and what the evidence said) ·
**Decision** · **Consequences** · **Reversal Conditions**. Keep it short — ADRs are exempt
from the word budget precisely because each one *replaces* long-form derivation elsewhere,
and that exemption is abused by writing an essay.

Where a decision can be a contract in code, write the contract and let the ADR point at it.

**How these decisions were reached:** [`../00/`](../00/) — the audit register, the corrected
brief, and the decision record. That trail is history and is not maintained.
