---
status: normative
updated: 2026-07-30
---
# **Architecture Decision Records**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural decisions refined iteratively.

Binding decisions with rationale and explicit reversal conditions.

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
| [0024](./0024-e0-is-a-tool-not-a-port.md) | `e0/` is a tool, not a port — `adapters/benchmark/` and `ports/benchmark.py` deleted; the `layers` contract forbids the adapter this port needed | Accepted |
| [0025](./0025-candidate-search-seams.md) | `CandidateExecutor`/`CandidateScorer` are adapter-internal Protocols, not ports — same reasoning as ADR-0024, applied to Best-of-N's scoring ladder | Accepted |

## **Template**

```markdown
# ADR-XXXX: <Title>

**Status**: Proposed | Accepted | Superseded by ADR-YYYY
**Date**: YYYY-MM-DD

## Context
What forced a decision (constraints, not conclusions).

## Decision
Actionable decision.

## Consequences
Impact and trade-offs.

## Reversal Conditions
Specific evidence required to revisit.
```

### Dual Status Fields

| Where | Values | Meaning |
| :--- | :--- | :--- |
| Frontmatter `status:` | `normative` / `rationale` / `historical` | Documentation taxonomy for budget tracking & retrieval indexer. See [docs/README.md](../README.md). |
| Body `**Status**:` | `Proposed` / `Accepted` / `Superseded by ADR-YYYY` | Decision lifecycle status. |

- **Budget Exemption**: ADRs are exempt from the normative word budget as high-density decision records.
- **Reversal Conditions**: Explicit criteria defining when to revisit decisions.

## **Relationship to Agent Memory**

Agent decisions within target repositories are written to `docs/decisions/` using this format (versioned in git, portable across harnesses). See [Neural-Symbolic Memory](../02-architecture/neural-symbolic-memory.md). This directory records decisions for SAGIHA itself.
