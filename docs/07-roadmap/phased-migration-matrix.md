---
status: normative
updated: 2026-07-30
---

# **Roadmap: Vertical Slices & Component Migration**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

> [!IMPORTANT]
> **Current build contract:** [Sprint 3](../sprints/sprint-3.md) (Block 1 — close the loop).
> Implementation truth: [STATUS.md](../STATUS.md). Sprint 2 is closed with known defects;
> do not extend periphery (MCP/OTel) before the Sprint 3 exit test is green.

## **Slices First, Components Second**

The risk in this system lives in **integration**, not in any individual component — a perfect vector store and a perfect LSP adapter that have never run together tell you nothing about whether the harness works.

The plan is a sequence of **vertical slices**, each thin through every layer and each independently useful. The component matrix below is the appendix, not the plan.

## **Sequencing Decision (Foundation Review 2026-07-29)**

E0 (standalone evaluation harness) remains the **strategic moat** — without a noise floor,
every later claim is unfalsifiable. Strict E0-before-any-agent would build a grader with nothing
to grade. The accepted near-term order is therefore:

1. **Block 1 / Sprint 3** — close one runnable, replayable coding loop.
2. **Block 2 / E0-lite** — harvest tasks, A/A noise floor, measure that loop.
3. **Blocks 3–5** — authority → retrieval → sandbox / MCP / OTel.

E0's full standalone product (grade *any* agent) still expands from E0-lite; it is not cancelled.

## **E0: The Evaluation Harness (strategic first product)**

Before treating the agent as “done,” one slice that is not only about the agent: **a standalone
evaluation harness** — commit-replay harvester, task runner, A/A noise floor, paired statistics
with multiple-comparison correction, and reporting. It grades *any* coding agent against a
repository's real commit history, not only SAGIHA.

Three reasons it stays first-class rather than last:

1. **It is the prerequisite for self-improvement, not a companion to it.** The stated goal is a harness that improves itself under structured tests and benchmarks. That is impossible before a measured noise floor exists — without one, every self-modification is accepted or rejected on noise, and the loop ratchets permanently on randomness. Most harness work in this space is an undiagnosed random walk for exactly this reason.
2. **It produces the S0 suite as a byproduct.** The chicken-and-egg problem — S0 needs a benchmark, the benchmark needs harvesting, harvesting needs a harness — dissolves when the harvester *is* an early deliverable ([ADR-0015](../08-decisions/0015-benchmark-target-repository.md)).
3. **It is independently useful.** No sandbox, no LSP pool, no candidate search, no embeddings. "Grade any coding agent on your own repository's history, against a measured noise floor" is a tool people would use before SAGIHA can resolve a single task — which is the project's realistic path to external feedback.

Every slice below is graded by E0 (or E0-lite) once Block 2 exists. That is what converts each subsequent architectural claim from an argument into a number.

## **Vertical Slice Plan**

| Slice | Capability Delivered End-to-End | Components | Gate (measurable) |
| :---- | :---- | :---- | :---- |
| **E0** | Grades any agent on a real repository, with a measured noise floor | Commit-replay harvester, task runner, A/A comparison, paired statistics with multiple-comparison correction, reporting | A/A run over the pinned suite reports a noise floor with a stated confidence interval; harvester produces ≥30 valid tasks; zero tasks whose base commit fails to revert cleanly |
| **S0** | Agent resolves a failing test in one file — verified, logged, replayable | `ModelProvider` + cassette replay, domain models, dispatch choke point, `PolicyEngine` + grants, SQLite-WAL trajectory store, Tree-sitter chunking + FTS5, structured edit application, pytest runner, commit-per-step | ≥70% resolved on a pinned 30-task internal suite within cost and time budget; 100% of runs replay deterministically; conformance suite green; `lint-imports` clean |
| **S1** | Agent works in a materialized worktree inside a container, under enforced grants | Worktree allocate/materialize/release, container sandbox, egress allowlist, secret redaction, `ResourceGovernor`, warm LSP supervisor | No write outside the worktree without a grant; no credential reachable inside the sandbox; parallel runs show zero port, cache, or database interference |
| **S2** | Retrieval measurably improves task success | AST-bounded chunking, BM25/FTS5, `CodeGraph` expansion, episodic memory with temporal reads and links. **Dense tier deferred** — [ADR-0014](../08-decisions/0014-defer-dense-retrieval.md) | recall@10 ≥ target on a labelled query set; ablation shows retrieval beats the no-retrieval control |
| **S3** | Best-of-N with sequential repair on multi-file tasks | `CandidateSearch`, hard gates, pristine injected test suite, graph-partitioned decomposition, escalation ladder | Best-of-N beats single-shot by more than the measured A/A noise floor; zero instances of a candidate modifying its grader |
| **S4** | Outer loop proposes mutations that survive statistical scrutiny | Commit-replay harvester, PRM scorer, calibrated AOI in shadow mode, Meta-Improver with TCB restrictions, human sign-off | Noise floor established and published; every accepted mutation beats it under paired evaluation with multiple-comparison correction; CI rejects 100% of TCB diffs |

**On gates.** "100% test passing" and "zero crash rate" are not measurable gates for a stochastic system without a defined workload. Every gate above names a fixed suite, a threshold, and a budget.

## **Component Migration Appendix**

Every advanced entry carries a **trigger condition** rather than a phase number. A component migrates when a measurement demands it.

| Component | Day 0 | Day 1 | Later — and its trigger |
| :---- | :---- | :---- | :---- |
| **Model Access** | Provider client + cassettes | Cache-aware assembly, budget accounting | Multi-provider routing — *when cost or availability data justifies it* |
| **Kernel Orchestrator** | Async ReAct loop | State machine + checkpoints | Candidate search; A2A — *when single-agent plateaus; when a real remote peer exists* |
| **Control Layer** | Static policy + grants | Risk gates, durable approvals | Learned escalation — *once approval history exists* |
| **Short-Term Memory** | Ring buffer over SQLite-WAL | Compaction at checkpoints | Compressed ring — *when sessions routinely exceed the window* |
| **Long-Term Memory** | SQLite FTS5 + record links | Backlinks, bi-temporal reads | Episodic temporal graph — *when decision recall demonstrably fails* |
| **Code Graph** | SQLite from Tree-sitter + git | Impact closure queries | Embedded property store (Kùzu) — *when traversal outgrows SQL* |
| **Indexing** | AST chunking + FTS5 + graph expansion | Incremental file-watch update | Dense tier — *when recall@10 misses target and the misses are vocabulary mismatch, not chunking*; out-of-process service — *when indexing misses its latency budget* |
| **Vector Compression** | None (exhaustive scan) | None | Quantization — *when corpus or latency crosses a measured ceiling, ~10⁷ vectors* |
| **Diagnostics** | Subprocess pytest + linter | Warm LSP supervisor, pooled | More languages — *per language actually used* |
| **Sandbox** | Local subprocess (development only) + worktree; container required at autonomous/scheduled autonomy levels from S1 | **Container + materialization + egress allowlist** | gVisor — *when the threat model requires syscall isolation* |
| **Protocols** | Stdio MCP | HTTP-SSE MCP | A2A — *when a genuinely remote peer agent exists* |
| **Self-Improvement** | Manual iteration | PRM scoring in shadow mode | RHI — *once the A/A noise floor is established* |


## **What Makes Deferral Safe**

Every deferred component sits behind a port already shaped to accept it, verified by a conformance suite that the future adapter must pass unchanged. That is the entire return on drawing the hexagon correctly at Day Zero: **it lets you build the simple thing now without paying for it later.**
