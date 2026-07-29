---
status: normative
updated: 2026-07-29
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
| [0015](./0015-benchmark-target-repository.md) | S0 benchmark target: rubric decided, repository **not yet named** | **Proposed** |
| [0016](./0016-container-runtime-podman.md) | Rootless Podman; egress allowlisted at an explicit proxy | Accepted |
| [0017](./0017-execution-profiles.md) | Execution profiles compose ports; coding is one profile, not the only path | Accepted |

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

**Reversal Conditions is the section that matters most.** Most of these decisions trade capability for simplicity on the basis of current scale or current tooling. Writing down what would change our mind is what separates an engineering decision from an ideological one — and it is what lets a future maintainer (human or agent) re-open a question legitimately instead of either obeying or ignoring the record.

## **Relationship to Agent Memory**

Decisions the *agent* makes while working in a target repository are written to `docs/decisions/` **in that repository**, using this same format. Repository-resident decisions are versioned by git, reviewable in a pull request, and portable across harnesses — see [Neural-Symbolic Memory](../02-architecture/neural-symbolic-memory.md).

This directory records decisions about SAGIHA itself.
