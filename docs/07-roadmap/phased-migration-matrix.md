# **Roadmap: Vertical Slices & Component Migration**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Slices First, Components Second**

The risk in this system lives in **integration**, not in any individual component — a perfect vector store and a perfect LSP adapter that have never run together tell you nothing about whether the harness works.

The plan is a sequence of **vertical slices**, each thin through every layer and each independently useful. The component matrix below is the appendix, not the plan.

## **Vertical Slice Plan**

| Slice | Capability Delivered End-to-End | Components | Gate (measurable) |
| :---- | :---- | :---- | :---- |
| **S0** | Agent resolves a failing test in one file — verified, logged, replayable | `ModelProvider` + cassette replay, domain models, dispatch choke point, `PolicyEngine` + grants, SQLite-WAL trajectory store, Tree-sitter chunking + FTS5, structured edit application, pytest runner, commit-per-step | ≥70% resolved on a pinned 30-task internal suite within cost and time budget; 100% of runs replay deterministically; conformance suite green; `lint-imports` clean |
| **S1** | Agent works in a materialized worktree inside a container, under enforced grants | Worktree allocate/materialize/release, container sandbox, egress allowlist, secret redaction, `ResourceGovernor`, warm LSP supervisor | No write outside the worktree without a grant; no credential reachable inside the sandbox; parallel runs show zero port, cache, or database interference |
| **S2** | Retrieval measurably improves task success | AST-bounded chunking, hybrid lexical + dense fusion, `CodeGraph`, episodic memory with temporal reads | recall@10 ≥ target on a labelled query set; ablation shows retrieval beats the no-retrieval control |
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
| **Long-Term Memory** | SQLite + sqlite-vec | LanceDB | Episodic temporal graph — *when decision recall demonstrably fails* |
| **Code Graph** | SQLite from Tree-sitter + git | Impact closure queries | Embedded property store (Kùzu) — *when traversal outgrows SQL* |
| **Indexing** | AST chunking + FTS5 + dense | Incremental file-watch update | Out-of-process service — *when measured indexing misses its latency budget* |
| **Vector Compression** | None (exhaustive scan) | None | Quantization — *when corpus or latency crosses a measured ceiling, ~10⁷ vectors* |
| **Diagnostics** | Subprocess pytest + linter | Warm LSP supervisor, pooled | More languages — *per language actually used* |
| **Sandbox** | Local subprocess (development only) + worktree; container required at autonomous/scheduled autonomy levels from S1 | **Container + materialization + egress allowlist** | gVisor — *when the threat model requires syscall isolation* |
| **Protocols** | Stdio MCP | HTTP-SSE MCP | A2A — *when a genuinely remote peer agent exists* |
| **Self-Improvement** | Manual iteration | PRM scoring in shadow mode | RHI — *once the A/A noise floor is established* |


## **What Makes Deferral Safe**

Every deferred component sits behind a port already shaped to accept it, verified by a conformance suite that the future adapter must pass unchanged. That is the entire return on drawing the hexagon correctly at Day Zero: **it lets you build the simple thing now without paying for it later.**
