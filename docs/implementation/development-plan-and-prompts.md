---
status: normative
updated: 2026-07-29
---

# **SAGIHA Implementation Plan & Modular Prompt Guidelines**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a structured implementation guideline for SAGIHA. Prompts are parameterized and modularized to remain valid even as specific adapter implementations or stack choices evolve.

> [!IMPORTANT]
> Phases here map onto the vertical slices in [`07-roadmap/phased-migration-matrix.md`](../07-roadmap/phased-migration-matrix.md), which is normative for scope and gates. Where this document and the roadmap disagree, the roadmap wins.

**Before Sprint 1, read these — they resolve every stack question the prompts assume:**
[Dependencies & Versions](../05-tech-stack/dependencies-and-versions.md) ·
[Tool Catalog](../03-contracts-and-models/tool-catalog.md) ·
[Prompt Architecture](../02-architecture/prompt-architecture.md) ·
[Error Taxonomy](../03-contracts-and-models/error-taxonomy.md) ·
[Configuration Reference](../05-tech-stack/configuration-reference.md) ·
[CI & Quality Gates](../06-guides-and-patterns/ci-and-quality-gates.md) ·
[ADR Log](../08-decisions/README.md)

---

## 🗓️ **Phased Execution Roadmap**

| Phase | Slice | Focus Area | Primary Deliverables | Gate (measurable) |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | S0 | Scaffolding & Ports | Package tree, Pydantic v2 schemas, `typing.Protocol` ports, composition root, conformance suite | `mypy --strict` clean; conformance suite green; `lint-imports` passes |
| **Phase 2** | S0 | Day-Zero Microkernel | SQLite-WAL trajectory store, stdio MCP driver, ReAct microkernel, **cassette replay** | ≥70% resolved on a pinned 30-task suite within budget; 100% of runs replay deterministically |
| **Phase 3** | S1 | Isolation, Sandbox & LSP | Worktree manager + materialization, **container sandbox + egress allowlist**, warm LSP supervisor, pristine test injection | No write outside the worktree without a grant; no credential reachable inside; parallel runs show zero interference |
| **Phase 4** | S2 | Memory & AST Chunking | Tree-sitter skeletonizer, lexical (FTS5) + code-graph retrieval — dense tier deferred per [ADR-0014](../08-decisions/0014-defer-dense-retrieval.md), code graph, telemetry logging | recall@10 ≥ target on a labelled query set; retrieval beats the no-retrieval control |
| **Phase 5** | S3–S4 | System 2 & Self-Improvement | Best-of-N search, hard gates, commit-replay harvester, AOI in shadow mode, Meta-Improver with TCB restrictions | Best-of-N beats single-shot by more than the A/A noise floor; CI rejects 100% of TCB diffs |

**Note on gates.** "0% crash rate" and "100% passing" are not measurable for a stochastic system without a defined workload; every gate above names a suite, a threshold, and a budget.

---

## 🛠️ **Reusable Modular Implementation Prompts**

### **Sprint 1: Core Scaffolding, Typed Ports & Conformance Tests**
```markdown
Scaffold the Python >=3.13 project under `src/sagiha/`, managed with uv (commit uv.lock).
Configure ruff, pyright strict (blocking), mypy strict (advisory), pytest + pytest-asyncio,
and import-linter with the contracts from 06-guides-and-patterns/ci-and-quality-gates.md.

Define Pydantic v2 domain schemas in
`domain/` and `typing.Protocol` interfaces in `ports/` — including `ModelProvider`, `Memory`,
`Indexer`, `CodeGraph`, `LSPAdapter`, `Workspace`, `WorktreeManager`, `ToolRegistry`,
`PolicyEngine`, `ResourceGovernor`, `TrajectoryStore`, `Evaluator`.

Contract rules, enforced in CI:
  - No `Dict[str, Any]` crosses a port; every payload is a Pydantic model.
  - Ports speak domain language, never storage language (`recall()`, not `search_similar(vector)`).
  - All timestamps are timezone-aware UTC via a single `utc_now()` helper.
  - Do NOT use `@runtime_checkable` as a correctness mechanism; it checks method presence only.
  - Trajectory identity is a DAG: `StepId(run_id, branch_id, seq, parent)`, not an int.

Create a single composition root `build_kernel(config) -> Kernel` — no DI container, no plugin
discovery, so static analysis and "go to definition" keep working. Write the port conformance
suite under `tests/contracts/`, parametrized over every adapter. Add `import-linter` contracts
forbidding `agency/` from importing `runtime/` or `adapters/`.
```

### **Sprint 2: Day-Zero Baseline Kernel, Replay & MCP Driver**
```markdown
Implement the Day-Zero kernel in `src/sagiha/kernel/`: an append-only SQLite-WAL
TrajectoryStore, an in-memory ShortTermMemory over it, a stdio MCP client driver for
filesystem and shell tools, and a deterministic async ReAct state machine.

Route every effect through a single dispatch choke point: authorize via `PolicyEngine`,
mint a capability `Grant`, acquire a lease from `ResourceGovernor`, dispatch, record the
outcome. Agency code must hold no reference to Runtime objects.

Implement the record/replay cassette adapter behind `ModelProvider` so the whole kernel runs
in CI with zero API calls. Classify every tool with an `EffectClass`; replay re-executes only
PURE calls and serves the rest from recorded observations. Emit OTel spans using the GenAI
semantic conventions. Both the TrajectoryStore and the OTel exporter subscribe to the EventBus independently. Neither is derived from the other.

Scores are emitted as separate `StepScored` events, never written back into a stored step.
```

### **Sprint 3: Isolation, Sandbox & LSP Diagnostic Gate**
```markdown
Implement `GitWorktreeManager` in `src/sagiha/runtime/`: allocate, **materialize**, release.
Materialization links or copies ignored-but-required artifacts (`.env`, `.venv`,
`node_modules`) — a fresh worktree contains only tracked files, so builds fail without it.
`allocate` returns a `Workspace`, never a path.

Run all agent commands inside a container sandbox with an egress allowlist enforced at the
network namespace and no host credentials mounted. Do not implement command-string
blocklisting as a security control — it fails to `bash -c`, base64, and `$IFS`.

Add an `LSPAdapter` backed by a warm server supervisor: servers persist across tasks, use
in-memory document overlays for unsaved edits, and share a bounded pool across worktrees
(one server per worktree exhausts RAM under parallel search).

Evaluate against a pristine, read-only injected copy of the test suite. `tests_unmodified`
is a hard gate: a candidate must never be able to edit its own grader.
```

### **Sprint 4: Hybrid Retrieval, Code Graph & Cache-Aware Context**
```markdown
Implement AST-bounded chunking in `src/sagiha/adapters/indexing/`: the unit is a Tree-sitter
function/method/class span, prefixed with file path, module docstring, and symbol path.
Chunking dominates retrieval quality — do not substitute fixed-size windows.

Build retrieval as BM25 via SQLite-FTS5 (exact symbol match is the strongest signal for code),
expanded along code-graph edges. The dense tier is **deferred** per ADR-0014 — add it only when
lexical+graph measurably misses recall@10 for vocabulary-mismatch reasons; when it arrives it is
fused with, never ranked above, the lexical tier.

Build the deterministic `CodeGraph` (imports, calls, definitions, ownership, co-change)
directly from Tree-sitter and git into SQLite. Never route deterministic structure through
LLM extraction.

Implement cache-aware context assembly: a stable prefix closed by a cache breakpoint, a
semi-stable retrieved region, and an append-only tail. Do NOT repartition the window by
percentage each turn — it changes the prefix and forfeits the cache on every call. Compaction
happens at deliberate checkpoints. Store reasoning as opaque provider-native blocks
round-tripped verbatim, never as a normalized string.

Log task features, costs, cache hit rates, and outcomes as structured events for later AOI training.
```

### **Sprint 5: Best-of-N Search, Gates & Bounded Self-Improvement**
```markdown
Implement `CandidateSearch` in `src/sagiha/agency/`: best-of-N proposal across parallel
worktrees with sequential repair of the best failing candidate. Do not implement MCTS — there
is no persistent tree, visit counts, or backpropagation, and each expansion costs a full agent
run. Tree search is gated on a calibrated value model.

Separate hard gates from soft scores. Gates (binary, non-negotiable): tests pass,
tests unmodified, no new suppressions, coverage not decreased, diff within bounds. Score
(ranking only, among candidates that already passed every gate): PRM value from diagnostic
deltas and test metrics. Never let a gameable proxy admit a candidate.

Competing candidates are selected among and discarded — never merged with each other.
Decomposed parallel work is partitioned into disjoint file sets via `CodeGraph.impacted_by()`;
overlapping sub-tasks are serialized.

Build the commit-replay benchmark harvester (mine commits, revert, pose as tasks) and run an
A/A test to establish the noise floor before believing any comparison. Ship AOI models in
shadow mode with an exploration fraction that always runs to completion, so acting on
predictions does not censor the training data.

Restrict `MetaImprover` by path allowlist away from the trusted computing base — policy engine,
evaluator, gate and benchmark definitions, deployment gate. Deployment requires human sign-off.
```

---

## 🧭 **Build Order**

`model port + replay → policy + dispatch → edit application → retrieval → isolation → search → outer loop`

The temptation is to start with the interesting parts: quantization, tree search, sidecars, temporal graphs. Those are the parts that will not matter if the boring ones are wrong — and the correct seams are what make deferring them free.
