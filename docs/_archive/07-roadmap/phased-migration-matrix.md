---
status: rationale
updated: 2026-07-30
retrieval: excluded
---
# Roadmap: Vertical Slices & Component Migration

> [!NOTE]
> Working architectural proposal, refined iteratively.

> [!IMPORTANT]
> **Build contract**: [Sprint 3a / 3b](../implementation/development_plan_v2.md) (Block 1).
> Truth source: [STATUS.md](../STATUS.md). **Sprint 3a closed (2026-07-30)**; Sprint 3b (hardening) is active.

---

## Slices First, Components Second

Architecture risk lives in system integration. Development proceeds via end-to-end **vertical slices**; individual component migration is secondary.

### Execution Order (Foundation Review 2026-07-29)
1. **Block 1 / Sprint 3**: Close runnable, replayable coding loop.
2. **Block 2 / E0-lite**: Harvester + A/A noise floor measurement.
3. **Blocks 3–5**: Authority → Retrieval → Sandbox / MCP / OTel.

### E0 Strategic Role
- **Noise Floor Baseline**: Prevents self-improvement from ratcheting on random noise.
- **Task Harvester**: Automatically extracts benchmark tasks from historical commits ([ADR-0015](../08-decisions/0015-benchmark-target-repository.md)).
- **Standalone Grader**: Evaluates any agent against pristine git targets.

---

## Vertical Slice Plan

| Slice | Capability Delivered End-to-End | Core Components | Measurable Gate |
| :--- | :--- | :--- | :--- |
| **E0** | Standalone agent evaluator with A/A noise floor | Harvester, task runner, A/A comparison, paired statistics | A/A noise floor reported at stated confidence level; harvester yields ≥30 valid tasks; 100% clean base commit reverts |
| **S0** | Resolves 1-file test failures (replayable) | `ModelProvider` + cassettes, dispatch choke point, `PolicyEngine`, SQLite-WAL, Tree-sitter + FTS5, pytest runner | ≥70% resolution on 30-task suite within budget; 100% deterministic replay; clean `lint-imports` and contracts |
| **S1** | Sandboxed execution in materialized container | Worktree manager, Podman sandbox, egress allowlist, secret redaction, warm LSP supervisor | Zero out-of-worktree writes without grant; zero sandbox credential leaks; zero port/cache/DB interference across runs |
| **S2** | Retrieval-enhanced task resolution | AST chunking, BM25/FTS5, `CodeGraph` expansion, bi-temporal episodic memory ([ADR-0014](../08-decisions/0014-defer-dense-retrieval.md)) | recall@10 ≥ target on query set; retrieval beats no-retrieval baseline |
| **S3** | Best-of-N + sequential repair on multi-file tasks | `CandidateSearch`, hard gates, pristine test suite, escalation ladder | Best-of-N exceeds single-shot by > A/A noise floor; 0% grader modification attempts |
| **S4** | Statistically validated outer-loop mutations | Commit harvester, PRM scorer, shadow AOI, Meta-Improver, human sign-off | Published noise floor; accepted mutations beat floor under paired correction; 100% TCB diff rejection in CI |

---

## Component Migration Matrix

Components migrate based on empirical **trigger conditions** rather than calendar dates.

| Component | Day 0 | Day 1 | Advanced State & Trigger |
| :--- | :--- | :--- | :--- |
| **Model Access** | Provider client + cassettes | Cache-aware assembly, budget accounting | Multi-provider routing — *when cost/availability data demands* |
| **Kernel Orchestrator** | Async ReAct loop | State machine + checkpoints | Candidate search / A2A — *when single-agent plateaus or remote peer exists* |
| **Control Layer** | Static policy + grants | Risk gates, durable approvals | Learned escalation — *once approval history accumulates* |
| **Short-Term Memory** | SQLite-WAL ring buffer | Compaction at checkpoints | Compressed ring — *when sessions exceed window bounds* |
| **Long-Term Memory** | SQLite FTS5 + record links | Backlinks, bi-temporal reads | Episodic temporal graph — *when decision recall fails* |
| **Code Graph** | Tree-sitter + git in SQLite | Impact closure queries | Embedded graph DB (Kùzu) — *when SQL graph traversal bottlenecked* |
| **Indexing** | AST chunking + FTS5 + graph | Incremental file-watch updates | Dense tier — *when recall@10 misses from vocabulary mismatch*; Out-of-process service — *when latency budget missed* |
| **Vector Compression** | Exhaustive scan | None | Quantization — *when corpus exceeds ~10⁷ vectors* |
| **Diagnostics** | Subprocess pytest + linter | Warm LSP supervisor | Multi-language LSP pools — *per language used* |
| **Sandbox** | Subprocess + worktree (dev) | Container + materialization + egress allowlist | gVisor — *when syscall isolation required* |
| **Protocols** | Stdio MCP | HTTP-SSE MCP | A2A — *when remote peer agent exists* |
| **Self-Improvement** | Manual iteration | Shadow PRM scoring | RHI — *once A/A noise floor established* |

---

## Deferral Safety

Hexagonal ports and parametrized conformance suites validate component swappability upfront, allowing simple initial implementations without architectural debt.
