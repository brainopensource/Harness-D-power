---
status: rationale
updated: 2026-08-05
retrieval: excluded
---

# 📚 Phase-0 Review Reference Guide & Prototype Insights

> **Purpose:** This reference guide catalogs and synthesizes the historical reviews, audits, and architectural specifications stored in `docs/_archive/rationale/reviews/`. It is designed to brief incoming Tech Leads and team members on the findings, failure modes, and battle-tested insights gained during the early beta prototype phase.

---

## 1. Executive Summary & Inventory Overview

During the prototype phase, a comprehensive series of audits and review specs were conducted to evaluate the codebase, security boundaries, measurement pipelines, and long-horizon autonomy specs.

| Filename | Absolute Path | Primary Purpose & Scope |
| :--- | :--- | :--- |
| [`README.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/README.md) | `docs/_archive/rationale/reviews/README.md` | Audit taxonomy, remediation tracking, and finding ID conventions (`D<n>`, `G<n>`, `C<n>`, `X<n>`). |
| [`agi_evolution_path.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/agi_evolution_path.md) | `docs/_archive/rationale/reviews/agi_evolution_path.md` | **System 3 "Conductor" Spec**: Specifies multi-day mission planning, durable hibernation, A-MEM memory, and skill compilation without widening TCB authority. |
| [`concept_review.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/concept_review.md) | `docs/_archive/rationale/reviews/concept_review.md` | **Concept & Architecture Review**: Evaluates what the prototype got right (CAR choke-point, tri-state gates, refuse-at-load config) vs. what failed (sequencing measurement last). |
| [`critical_gaps_analysis.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/critical_gaps_analysis.md) | `docs/_archive/rationale/reviews/critical_gaps_analysis.md` | Deep dive into critical gaps G1–G10 (context rot, token budget leaks, unhandled taint propagation). |
| [`next_gen_architecture_specs.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/next_gen_architecture_specs.md) | `docs/_archive/rationale/reviews/next_gen_architecture_specs.md` | **v2 Spec Architecture**: Tiered self-improvement, dynamic context assembly, and AST-aware edit mechanics. |
| [`codebase_delta_refactor.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/codebase_delta_refactor.md) | `docs/_archive/rationale/reviews/codebase_delta_refactor.md` | Concrete refactoring plan for findings H1–H4, code smells, and structural debt in the prototype. |
| [`prompt_review.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/prompt_review.md) | `docs/_archive/rationale/reviews/prompt_review.md` | **Prompt & Context Engineering Review**: Audit of system prompt instruction budgets (~150 instruction ceiling), tool schema clarity, and instruction drift. |
| [`Harness_LLM_orchestrator_aether_project_review_v210.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/Harness_LLM_orchestrator_aether_project_review_v210.md) | `docs/_archive/rationale/reviews/Harness_LLM_orchestrator_aether_project_review_v210.md` | **Audit of Record (v2.1.0)**: 18 verified code defects (D1–D18) and 10 capability gaps across the prototype codebase. |
| [`review_project_rewrite_v300.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/review_project_rewrite_v300.md) | `docs/_archive/rationale/reviews/review_project_rewrite_v300.md` | **Track A Phase 0 RFP Charter**: Mandates 12 specific deliverables for the Phase 0 rewrite set. |
| [`review_project_rewrite_v300B.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/review_project_rewrite_v300B.md) | `docs/_archive/rationale/reviews/review_project_rewrite_v300B.md` | **Track B Phase 0 RFP Charter**: Parallel independent proposal charter targeting `docs/rationale/rewrite_b/`. |

---

## 2. In-Depth Summary & Key Insights per Document

### 1. [`agi_evolution_path.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/agi_evolution_path.md) — The System 3 "Conductor" Layer
* **Summary**: Specifies the long-horizon autonomy layer ("Conductor") that sits above single-task execution kernels. It handles multi-day missions, durable hibernation (`FrozenRunState`), memory consolidation (A-MEM), and skill compilation.
* **Key Insights & Takeaways**:
  1. **Pilot & Scheduler, Never an Executor**: The Conductor owns time, attention, and knowledge, but **holds zero tools, zero shell access, and zero capability grants**. Every action is submitted to an underlying kernel via `Orchestrator.execute()`.
  2. **System 3 Timescale**: System 1 (ReAct) handles seconds; System 2 (Best-of-N + repair) handles minutes; System 3 (Conductor) handles hours-to-weeks.
  3. **Hibernation as Absence**: Hibernation is not sleeping in RAM; it serializes state to SQLite WAL (`FrozenRunState`) and exits the process, surviving host reboots and rate limits seamlessly.
  4. **Active Memory Consolidation**: Raw trajectories are distilled into structured guidelines only if supported by $\ge 3$ distinct admitted, taint-free runs.

---

### 2. [`concept_review.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/concept_review.md) — Conceptual Audit & Lessons Learned
* **Summary**: A thorough retrospective on what the early beta prototype got right and where its design concepts failed.
* **Key Insights & Takeaways**:
  1. **What to Keep**: 
     - *Single Dispatch Choke-Point* (`kernel/dispatch.py`): Gated tool execution in one single location.
     - *Tri-State `GateReport`*: `True` / `False` / `None` (where `None` = unmeasured/failed closed, never a pass).
     - *Refuse-at-Load Configuration*: Pydantic validators reject insecure configurations at startup.
     - *Boring Storage*: SQLite + Tree-sitter without complex external daemons.
  2. **What Failed**: 
     - *Sequencing Measurement Last*: Deferring benchmark suites meant capability features shipped without empirical proof of value. **Rule for v3: Build evaluation suites in Milestone 1b**.
     - *Plausible Fallback Lies (C-1 Defect)*: Swallowing exceptions and returning empty lists (`[]`) masks failure as zero results. **Rule for v3: Use explicit `Measured[T]` types that fail closed**.

---

### 3. [`critical_gaps_analysis.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/critical_gaps_analysis.md) — Deep Dive into Prototype Gaps (G1–G10)
* **Summary**: Evaluates fundamental deficiencies in context window utilization, token leakage, taint tracking, and multi-agent coordination.
* **Key Insights & Takeaways**:
  1. **Context Rot Cliff**: Model performance degrades non-linearly past ~70% context usage. Auto-compaction must trigger early rather than late.
  2. **Taint Tracking Integrity**: Data originating from untrusted web sources or sub-agent outputs must carry `UNTRUSTED_TAINTED` tags to prevent prompt injection laundering.
  3. **Port Rent Enforcement**: Ports without active adapters must be demoted rather than left as un-tested abstractions.

---

### 4. [`next_gen_architecture_specs.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/next_gen_architecture_specs.md) — Next-Gen Harness Specification
* **Summary**: Outlines the transition from prototype architecture to a modular, production-ready specification.
* **Key Insights & Takeaways**:
  1. **5-Layer Prompt Cache Alignment**: System prompt, tools, repo map, task brief, dynamic history. Ensures >92% prompt cache hit rates on providers like Anthropic.
  2. **Anchored Search/Replace Edits**: Anchored string diffs with whitespace tolerance beat unanchored line-number edits.
  3. **Tree-sitter Syntax Gate**: Parsing modified files with Tree-sitter *before* disk write prevents syntax errors from entering test loops.

---

### 5. [`codebase_delta_refactor.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/codebase_delta_refactor.md) — Concrete Refactoring Plan (H1–H4)
* **Summary**: Translates audit findings into step-by-step refactoring tasks across the prototype package (`src/sagiha/`).
* **Key Insights & Takeaways**:
  1. **H1 (Measurement Honesty)**: Eliminating dummy pass rates and bogus noise floors.
  2. **H2 (Budget Governor Enforcement)**: Ensuring token and dollar spend are reserved before tool execution.
  3. **H3 (Replay Determinism)**: Ensuring cassette recordings match execution byte-for-byte.

---

### 6. [`prompt_review.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/prompt_review.md) — Context & System Prompt Engineering
* **Summary**: Audits system prompt structures, instruction ceilings, and tool schema formats.
* **Key Insights & Takeaways**:
  1. **~150-Instruction Adherence Ceiling**: Frontier LLMs lose instruction adherence rapidly when system prompts exceed ~150 distinct directives. Keep system rules concise and deterministic.
  2. **Tool Search on Demand**: Dynamic tool selection reduces prompt token bloat while keeping tool schemas clean.

---

### 7. [`Harness_LLM_orchestrator_aether_project_review_v210.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/Harness_LLM_orchestrator_aether_project_review_v210.md) — Baseline Audit of Record
* **Summary**: The comprehensive audit detailing 18 verified code defects (D1–D18) and 10 capability gaps (G1–G10) in the v2 prototype.
* **Key Insights & Takeaways**:
  1. Serves as the primary reference for why structural refactoring is required.
  2. Highlights key isolation failures (e.g. editable install `.pth` path leaks).

---

### 8. [`review_project_rewrite_v300.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/review_project_rewrite_v300.md) & [`review_project_rewrite_v300B.md`](file:///F:/Coding/Harness-D-power/docs/_archive/rationale/reviews/review_project_rewrite_v300B.md) — Phase-0 Rewrite Charters
* **Summary**: RFP charters commissioning Track A (`rewrite/`) and Track B (`rewrite_b/`) independent architectural designs.
* **Key Insights & Takeaways**:
  1. Defines the 15 technical domains required for the greenfield rewrite.
  2. Establishes the benchmarking targets and performance constraints.

---

## 3. Top 10 Architectural Lessons for the Tech Lead Meeting

1. **Build Evaluation Instruments First**: Fix test runner isolation and establish an A/A noise floor before measuring agent capabilities.
2. **Isolate the Trusted Computing Base (TCB)**: Never allow an agent or self-evolution loop to modify its own evaluators or test gates (Generator $\neq$ Evaluator).
3. **Single Tool Execution Choke-Point**: Enforce all capability grants exclusively through `kernel/dispatch.py`.
4. **Port Entry Rule**: Only introduce a port interface when its concrete adapter and conformance test are built simultaneously.
5. **Prompt Caching is Architecture**: Design fixed 5-layer prompt prefixes to guarantee >92% cache hit rates.
6. **No Plausible Fallback Lies**: Never swallow exceptions into empty lists or zeros. Return explicit `None` or typed `Measured[T]` results that fail closed.
7. **Tree-sitter Syntax Validation**: Pre-validate code diffs with Tree-sitter before committing changes to disk.
8. **Durable Hibernation**: Support process-exit hibernation via `FrozenRunState` so long-horizon tasks survive host reboots.
9. **Depth-1 Sub-agent Delegation**: Cap sub-agent nesting at depth 1 with scoped tool registries to prevent recursive cost explosions.
10. **Code Wins**: Maintain clean, executable `Protocol` contracts in `src/aether/ports/` as the single source of truth.
