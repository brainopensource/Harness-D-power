---
status: normative
updated: 2026-07-30
---

# **Architecture Decision Records**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Binding decisions, each with the reasoning that produced it and the conditions that would reverse it. A decision without a recorded rationale gets re-litigated every few months; one without a reversal condition becomes dogma.

## **Status Values**

`Proposed` · `Accepted` · `Superseded by ADR-XXXX` · `Deprecated`

## **Log**

| ADR | Decision | Status |
| :--- | :--- | :--- |
| [0001](./0001-project-name.md) | Project is SAGIHA — Super AGI Harness Agent | Accepted |
| [0002](./0002-domain-language-ports.md) | Ports speak domain language, never storage language | Accepted |
| [0003](./0003-conformance-over-isinstance.md) | Conformance suites in `tests/contracts/`, not `@runtime_checkable` | Accepted |
| [0004](./0004-no-di-container.md) | Explicit composition root; no DI container or plugin discovery | Accepted |
| [0005](./0005-best-of-n-not-mcts.md) | System 2 is best-of-N + sequential repair, not MCTS | Accepted |
| [0006](./0006-sandbox-is-the-perimeter.md) | Container sandbox is the security boundary; no command blocklisting | Accepted |
| [0007](./0007-trusted-computing-base.md) | TCB is never writable by the agent; deploy needs human sign-off | Accepted |
| [0008](./0008-native-sdks-no-litellm.md) | Native provider SDKs behind `ModelProvider`; no universal layer | Accepted |
| [0009](./0009-python-313-and-toolchain.md) | Python ≥3.13, uv, ruff, pyright blocking + mypy advisory | Accepted |
| [0010](./0010-defer-exotic-components.md) | Sidecars, quantization, Redis, graph daemons, A2A deferred behind triggers | Accepted |
| [0011](./0011-split-code-and-episodic-graphs.md) | Deterministic code graph separate from episodic memory | Accepted |
| [0012](./0012-record-replay-determinism.md) | Determinism claim is record/replay, not reproducible generation | Accepted |
| [0013](./0013-extension-registration.md) | Extensions register via entry points, resolved once then frozen (amends 0004) | Accepted |
| [0014](./0014-defer-dense-retrieval.md) | Dense retrieval and the embedding provider deferred behind a recall@10 trigger | Accepted |
| [0015](./0015-benchmark-target-repository.md) | S0 benchmark target: `brainopensource/Harness-D-power` | Accepted |
| [0016](./0016-container-runtime-podman.md) | Rootless Podman; egress allowlisted at an explicit proxy | Accepted |
| [0017](./0017-execution-profiles.md) | Execution profiles compose ports; coding is one profile, not the only path | Accepted |
| [0018](./0018-native-workflow-dag.md) | Macro workflow is a native `WorkflowStep` protocol in `agency/`; no LangGraph/LangChain/Temporal | Accepted |
| [0019](./0019-port-consolidation.md) | Port consolidation 24 → 19 Protocols; deletions carry written re-promotion conditions | Accepted |
| [0020](./0020-per-invocation-effect-classification.md) | Per-invocation effect classification; the PURE argv allowlist lives in the TCB | Accepted |
| [0021](./0021-seed-only-layer-6-retrieval.md) | Layer-6 retrieval is seed-only; all later retrieval is agentic and tail-resident | Accepted |
| [0022](./0022-rhi-economic-refounding.md) | RHI re-founded on economics: Tiers A/B scheduled, Tier C dormant behind a funding trigger | Accepted |
| [0023](./0023-port-rent-rule.md) | Ports pay rent — zero non-test adapters for two phases ⇒ automatic demotion and deletion review | Accepted |

## **Template**

```markdown
# ADR-XXXX: <Title>

**Status**: Proposed | Accepted | Superseded by ADR-YYYY
**Date**: YYYY-MM-DD

## Context
What forced a decision. The constraints, not the conclusion.

## Decision
What was decided, stated so a reader can act on it.

## Consequences
What this makes easy, what it makes hard, what it forecloses.

## Reversal Conditions
The specific evidence that would justify revisiting this.
```

### The two `Status` fields are not a duplication

Every ADR carries a status in **two** places, and an audit flagged this as drift. It is not — they
are different axes, and collapsing them would lose information:

| Where | Values | Means |
| :--- | :--- | :--- |
| Front matter `status:` | `normative` / `rationale` / `historical` | The **docs taxonomy** — is this file binding, and does it count against the word budget? Read by `scripts/docs_budget.py` and the `v2-S6` retrieval indexer. See [docs/README.md](../README.md) |
| Body `**Status**:` | `Proposed` / `Accepted` / `Superseded by ADR-YYYY` | The **decision lifecycle** — has this call been made, and does it still stand? |

An ADR is `status: normative` from the moment it is written, including while its decision is still
`Proposed` — the file binds as the record of an open question. A `Superseded` ADR stays `normative`
too: superseded decisions are still the authoritative account of what was decided and why, and
demoting them would hide the reversal from exactly the reader who needs it.

**ADRs are exempt from the normative word budget.** They are short, high-value, and each one
*replaces* long-form derivation elsewhere.

**Reversal Conditions is the section that matters most.** Most of these decisions trade capability for simplicity on the basis of current scale or current tooling. Writing down what would change our mind is what separates an engineering decision from an ideological one — and it is what lets a future maintainer (human or agent) re-open a question legitimately instead of either obeying or ignoring the record.

## **Relationship to Agent Memory**

Decisions the *agent* makes while working in a target repository are written to `docs/decisions/` **in that repository**, using this same format. Repository-resident decisions are versioned by git, reviewable in a pull request, and portable across harnesses — see [Neural-Symbolic Memory](../02-architecture/neural-symbolic-memory.md).

This directory records decisions about SAGIHA itself.
