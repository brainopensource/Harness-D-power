# **SAGIHA — Super AGI Harness Agent**

> [!NOTE]
> **Working Proposal Disclaimer**: This documentation tree is a working architectural proposal and reference blueprint for SAGIHA, not an imperative final specification. Practical iterations, prototyping, and empirical evaluation refine these modules as the system evolves.

Welcome to the documentation hub for **SAGIHA** — a decoupled, hexagonal Meta-Harness that turns frontier LLMs into an autonomous software engineering agent operating independently or with a human in the loop.

---

## **Naming & Scope**

`SAGIHA` expands to **Super AGI Harness Agent** throughout this suite. Earlier drafts used competing expansions; this one is canonical.

The system is scoped and measured as an **autonomous coding harness**. Capability claims in this suite are stated as benchmarks with thresholds, not as unfalsifiable end-states.

---

## **Source of Truth**

To avoid the documentation drift that affected earlier revisions, ownership is explicit:

* The **modular docs (`01` – `07`)** are the **normative source of truth**. When a detail is contested, these win.
* The **reference blueprints** in [`reference/`](./reference/) are the long-form derivation and rationale. They carry the research context, comparative analysis, and full port listings.

Each topic has exactly one owner. Do not restate a contract in two places.

---

## **Documentation Sitemap**

| Module Directory | Status | Primary Documents |
| :--- | :--- | :--- |
| 📁 [`01-executive/`](./01-executive/) | **Normative** | [vision-and-philosophy.md](./01-executive/vision-and-philosophy.md), [executive-summary.md](./01-executive/executive-summary.md) |
| 📁 [`02-architecture/`](./02-architecture/) | **Normative** | [car-model.md](./02-architecture/car-model.md), [microkernel-and-bus.md](./02-architecture/microkernel-and-bus.md), [neural-symbolic-memory.md](./02-architecture/neural-symbolic-memory.md), [context-and-cache-engineering.md](./02-architecture/context-and-cache-engineering.md), [security-and-threat-model.md](./02-architecture/security-and-threat-model.md), [performance-sidecars.md](./02-architecture/performance-sidecars.md) |
| 📁 [`03-contracts-and-models/`](./03-contracts-and-models/) | **Normative** | [hexagonal-ports.md](./03-contracts-and-models/hexagonal-ports.md), [domain-schemas.md](./03-contracts-and-models/domain-schemas.md), [task-and-acceptance.md](./03-contracts-and-models/task-and-acceptance.md), [lsp-interface.md](./03-contracts-and-models/lsp-interface.md), [protocols-mcp-a2a.md](./03-contracts-and-models/protocols-mcp-a2a.md) |
| 📁 [`04-workflows-and-loops/`](./04-workflows-and-loops/) | **Normative** | [dmartic-inner-loop.md](./04-workflows-and-loops/dmartic-inner-loop.md), [git-worktree-branching.md](./04-workflows-and-loops/git-worktree-branching.md), [rhi-outer-loop.md](./04-workflows-and-loops/rhi-outer-loop.md) |
| 📁 [`05-tech-stack/`](./05-tech-stack/) | **Normative** | [control-plane-python.md](./05-tech-stack/control-plane-python.md), [indexing-and-retrieval.md](./05-tech-stack/indexing-and-retrieval.md), [aoi-coprocessors.md](./05-tech-stack/aoi-coprocessors.md) |
| 📁 [`06-guides-and-patterns/`](./06-guides-and-patterns/) | **Normative** | [getting-started.md](./06-guides-and-patterns/getting-started.md), [writing-adapters.md](./06-guides-and-patterns/writing-adapters.md), [port-conformance-testing.md](./06-guides-and-patterns/port-conformance-testing.md), [sidecar-development.md](./06-guides-and-patterns/sidecar-development.md), [running-benchmarks.md](./06-guides-and-patterns/running-benchmarks.md) |
| 📁 [`07-roadmap/`](./07-roadmap/) | **Normative** | [phased-migration-matrix.md](./07-roadmap/phased-migration-matrix.md) |
| 📁 [`implementation/`](./implementation/) | **Normative** | [development-plan-and-prompts.md](./implementation/development-plan-and-prompts.md) |
| 📁 [`reference/`](./reference/) | **Rationale** | Long-form conceptual design and architecture specification blueprints |

---

## 📚 **Executive & Technical Reference Documents**
* 📘 [SAGIHA Conceptual Design.md](./reference/SAGIHA%20Conceptual%20Design.md) — conceptual architecture, functional blocks, and dual-process execution engine.
* 📗 [SAGIHA Architecture Specification Blueprint.md](./reference/SAGIHA%20Architecture%20Specification%20Blueprint.md) — technical brief, full port listings, protocol interfaces, and adversarial failure analysis.
* 📙 [benchmarking-existing-harnesses.md](./reference/benchmarking-existing-harnesses.md) — comparative teardown of Claude Code CLI, Aider, OpenHands, SWE-agent, and Grok Code Build.


---

## **Start Here**

1. [Vision & Philosophy](./01-executive/vision-and-philosophy.md) — what the harness owns and what it deliberately does not.
2. [Hexagonal Ports](./03-contracts-and-models/hexagonal-ports.md) — the contracts everything else depends on.
3. [Port Conformance Testing](./06-guides-and-patterns/port-conformance-testing.md) — the mechanism that makes adapter swapping real rather than aspirational.
4. [Phased Migration Matrix](./07-roadmap/phased-migration-matrix.md) — vertical slices, gates, and what is deliberately deferred.
