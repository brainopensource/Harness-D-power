---
status: normative
updated: 2026-07-29
---

# **Glossary**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Terms carry these meanings throughout the suite. Where a term is commonly used loosely elsewhere, the entry says what SAGIHA specifically means by it.

## **Architecture**

**CAR** — Control-Agency-Runtime. The three-layer model. Control authorizes, Agency deliberates, Runtime executes. Enforced by capability grants, import-linter contracts, and a single dispatch choke point — not by convention.

**Port** — a `typing.Protocol` written in *domain* language defining a capability boundary. `Memory.recall()` is a port; `store_vector()` would be a driver.

**Adapter** — a concrete implementation of a port. Interchangeable, verified by conformance suites.

**Conformance suite** — behavioral tests in `tests/contracts/` parametrized over every adapter of a port. The mechanism that makes swappability real. An adapter absent from it is unsupported.

**Composition root** — the single `build_kernel(config)` function wiring everything. No DI container.

**Dispatch choke point** — the one path from intent to effect, where authorization, budget, audit, and redaction attach.

**Grant** — an unforgeable capability token minted only by `PolicyEngine`, required by every side-effecting Runtime method. Makes policy non-bypassable by construction.

**TCB (Trusted Computing Base)** — policy engine, evaluator, gate definitions, benchmark definitions, deployment gate, secret handling, sandbox boundary. Never writable by the agent.

**Sidecar** — an out-of-process compiled service. A deployment topology, not an architectural layer. Currently all deferred or dropped.

## **Execution**

**DMARTIC** — the inner loop: Design, Measure, Analyze, Review, Test, Improve, Control, Self-Reflect.

**System 1 / System 2** — fast direct ReAct for localized work; deliberate best-of-N with sequential repair for complex work. Routing is a deterministic escalation ladder.

**Best-of-N** — propose *n* candidate solutions, gate them, rank survivors, pick one. Explicitly *not* MCTS: no persistent tree, no visit counts, no backpropagation.

**Sequential repair** — feeding a failing candidate its own gate failures for another attempt. Higher yield per dollar than widening N.

**Escalation ladder** — the deterministic System 1 → System 2 rule (repeated failure, multi-file scope, diff size, risk class). Also the label generator for a future learned router.

**Worktree** — an isolated git working directory per candidate or sub-task. Isolates **tracked file state only** — not ports, dependency trees, caches, databases, or environment.

**Materialization** — copying or linking ignored-but-required artifacts (`.env`, `.venv`, `node_modules`) into a fresh worktree. Required, not optional: a worktree contains only tracked files, so builds fail without it.

**EffectClass** — `PURE` / `IDEMPOTENT` / `DESTRUCTIVE`. Governs replay safety; only `PURE` calls re-execute during replay.

**Cassette** — a recorded model interaction enabling replay with zero API calls. The `ModelProvider` replay adapter.

## **Memory & Retrieval**

**STM / LTM** — short-term (per-session ring buffer over SQLite-WAL) and long-term (durable `Memory` port).

**Code graph** — deterministic structure (imports, calls, ownership, co-change) derived exactly from Tree-sitter and git. Never LLM-extracted.

**Episodic memory** — learned, contestable facts (decisions, rationale, preferences) with bi-temporal validity. The only place LLM extraction and temporal invalidation earn their cost.

**Bi-temporal** — tracking both *valid time* (when a fact held) and *transaction time* (when the system learned it). Note git is already bi-temporal for code.

**AST-bounded chunk** — an embeddable unit that is a Tree-sitter function/method/class span, prefixed with file path and symbol path. Never a fixed-size window.

**Skeletonization** — stripping function bodies while keeping interfaces, signatures, and docstrings.

**Staged re-hydration** — restoring full file content after an edit fails under compacted context. Compilation failure is the signal that compaction went too far.

**Stable prefix** — the byte-identical leading portion of the prompt that stays cached across turns. Any per-turn repartitioning destroys it.

## **Evaluation**

**Hard gate** — a binary, non-negotiable admission criterion (tests pass, tests unmodified, no new suppressions, coverage held, diff bounded). Gates *admit*; they are never traded off.

**Soft score** — a continuous ranking signal (PRM value) applied *only* to candidates that already cleared every gate. Never admits.

**`tests_unmodified`** — the gate preventing a candidate from editing its own grader. With filesystem access to its worktree, an agent can otherwise rewrite the tests it is scored against.

**Pristine injection** — supplying the test suite read-only from the base commit, so evaluation never uses the candidate's copy.

**PRM** — Process Reward Model. Scores intermediate steps rather than only final outcomes.

**A/A noise floor** — the score-delta distribution from running the *unmodified* harness twice. Any change not exceeding it is not an improvement. Must be re-measured whenever the model version changes.

**Commit-replay** — harvesting real commits, reverting them, posing them as tasks. Uncontaminated, in-distribution, self-maintaining.

**Recall@k** — retrieval quality against a labelled query set, reported separately from task success so retrieval regressions stay attributable.

## **Improvement**

**RHI** — Recursive Harness Self-Improvement. The outer loop, restricted to the mutable surface, gated on statistics, deployed only with human sign-off.

**Mutable surface** — what the outer loop may edit: prompts, retrieval and compaction parameters, tool descriptions, routing heuristics, non-Control adapters. The complement of the TCB.

**AOI** — Auxiliary Optimization Intelligence. Small local models (reward, failure, cost predictors). Advisory only, shadow mode by default.

**Shadow mode** — a model predicts and logs but does not act, until calibration justifies promotion.

**Exploration fraction** — the share of runs that complete regardless of predicted failure, preventing the predictor from censoring its own training data.

## **Protocols & Channels**

**MCP** — Model Context Protocol. Vertical integration: agent to tools. SAGIHA both consumes MCP servers and runs as one.

**A2A** — Agent-to-Agent. Horizontal peer delegation. Deferred until a genuinely remote peer exists.

**Observer / Interceptor** — event bus subscriber kinds. Observers cannot influence execution; interceptors may deny but never mutate.

**Pilot** — any client driving the headless entry point: CLI/TUI, bot, IDE, CI, A2A peer.

**`sagiha-bot`** — the separate, disposable messaging-platform pilot service. Deliberately out of this repository.

## **Roadmap**

**Vertical slice (S0–S4)** — a thin end-to-end capability through every layer, each with a measurable gate. Contrast with component-wise phasing, which optimizes the wrong axis since the risk lives in integration.

**Trigger condition** — the measurement that must fire before an advanced component is adopted. Replaces calendar-based scheduling.
