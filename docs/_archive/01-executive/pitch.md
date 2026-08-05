---
status: rationale
updated: 2026-07-30
retrieval: excluded
---
# ⚡ SAGIHA — The Pitch

> A meta-loop harness: infrastructure that turns frontier LLMs into autonomous, verifiable, and benchmarkable software engineers built with swappable components.

---

## 1. What a Meta-Loop Harness Is

The LLM operates strictly as a reasoning engine without direct file or shell access. Every action is emitted as an intent evaluated by the harness dispatch choke point.

### Nested Execution Loops
| Loop | Operates On | Primary Objective |
| :--- | :--- | :--- |
| **Inner Loop** (DMARTIC) | Single task | Verifies code changes |
| **Process Loop** (Workflow DAG) | Entire goal | Sequences and scopes tasks |
| **Outer Loop** (RHI) | Past trajectories | Optimizes harness configuration |

### Core System Properties
- **Containment**: Capabilities require scoped grants validated at `kernel/dispatch.py`.
- **Replayability**: Model calls record to cassettes for deterministic offline replay with zero network cost.
- **Empirical Measurement**: Benchmarking against a measured **A/A noise floor** to validate changes against stochastic drift.
- **Grader Integrity**: Read-only pristine test suite injection prevents candidate test tampering.

---

## 2. Environment & Infrastructure

- **Perception**: Tree-sitter AST structural queries (`callers_of`, `impacted_by`) + LSP diagnostics (no ungrounded embeddings).
- **Motor Control**: Bounded, paginated tool outputs to prevent context overflow.
- **Workspace**: Ephemeral git worktrees per attempt; failing attempts are discarded.
- **Memory Split**: Deterministic code structure via AST; bi-temporal learned facts in an episodic knowledge graph.
- **Storage**: Single SQLite file baseline.

---

## 3. Execution Workflow & Dual-Process Loop

Prompts decompose into PRD specs and story boards with disjoint file sets executed via the inner loop:

```
[ Prompt ] ─► [ PRD Spec ] ─► [ Story Board ] ─► [ Pick Story ]
                                                       │
                                                       ▼
[ Land worktree ] ◄── [ Verify Gate ] ◄── [ DMARTIC Inner Loop ]
                              │                         ▲
                              └── fail: return to board ─┘
                                  (with diagnostics attached)
```

- **DMARTIC Inner Loop**: Design, Measure, Analyze, Review, Test, Improve, Control, Self-Reflect.
- **Dual-Process Switch**: Fast ReAct for local edits; parallel best-of-N worktrees with sequential repair for architectural tasks.
- **Separation Invariant**: Binary gates admit; soft scores rank. A missing verdict never passes.

---

## 4. Workflow DAG (`WorkflowStep[In, Out]`)

Each pipeline stage is an isolated `WorkflowStep[In, Out]` configured via `config.toml`. Stages emit events and persist step state, making workflows resumable, replayable, and testable.

*Invariants*: Planning stages are adopted only if benchmark results prove they outperform un-planned execution.

---

## 5. Outer Loop Optimization (RHI)

Reflexive Harness Improvement (RHI) tunes prompts, tool descriptions, and model routing offline over past runs.

*Safety Constraints*:
1. Mutates declared surfaces only; kernel/TCB is immutable.
2. Changes must exceed the measured A/A noise floor.

---

## 6. Hexagonal Decoupling & Architecture

- **Typed Interfaces**: `async` Pydantic models over domain ports.
- **Adapter Swappability**: Infrastructure components (indexers, models, search) swap behind ports without core changes. Enforced via `import-linter` in CI.
- **Granular Optimization**:
  - **Micro**: Replace single adapter behind a port.
  - **Macro**: Reconfigure DAG pipeline in `config.toml`.

---

## 7. Multi-Agent Scaling

Scales horizontally by routing stories across Architect, Developer, and QA harnesses via MCP/A2A into isolated worktrees.

### Scaling Sequence Rule
```
one closed loop  ──►  measurement  ──►  process layer  ──►  swarm
```
Multi-agent expansion is strictly gated on single-agent benchmark reproducibility.

---

## 8. Current Implementation Status

- **Sprint 3a Exit Test (Closed 2026-07-30)**: Replay of bugfix candidate through dispatch choke point validated in CI via committed cassettes.
- **Current Gaps & Roadmap**:
  - Provider adapters pending live model execution.
  - E0 evaluation substrate (Block 2) under active development.
  - Workflow DAG defined in [ADR-0018](../08-decisions/0018-native-workflow-dag.md) gated on Block 2 verification.

Source of truth: [`docs/STATUS.md`](../STATUS.md) | [Sprint 3a Status](../implementation/development_plan_v2.md).

---

## Further Reading

* [`README.md`](../../../README.md) — System architecture, agency levels, quickstart.
* [`docs/STATUS.md`](../STATUS.md) — Implementation status and roadmap.
* [`docs/08-decisions/`](../08-decisions/) — Architecture Decision Records (ADRs).
* [`docs/reviews/`](../rationale/reviews/) — Architectural review audit trail.
