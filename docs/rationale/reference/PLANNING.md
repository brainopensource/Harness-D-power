---
status: normative
phase: 0 — planning
updated: 2026-08-03
---

# AETHER — Phase 0 Planning Charter

> **Working name.** `AETHER` is a placeholder until ADR-0001 pins it. Every other name in this
> document is a real, defined term.

## 0. How to use this document

This is the **only** document that exists before the others. It exists to answer three questions in
order, and it is finished when all three are answered:

1. **What are we building, precisely enough to falsify?** (§2, §3)
2. **What must be true structurally so that scale never forces a rewrite?** (§4, §5, §7)
3. **Which documents get written, in what order, before any `src/` code is merged?** (§9, §10)

**Rule: no code merges to `src/` until the §10 exit gate is green.** One phase of documentation
discipline buys every later phase an uncontested specification. This is the cheapest leverage
available in the entire project and the only phase where being slow is correct.

**Rule: this document is superseded, not maintained.** Once a section's owning document exists
(§9), that document wins and the section here becomes a pointer. Do not maintain two copies.

---

## 1. Benchmark reality check — READ BEFORE COMMITTING TO A NUMBER

The stated goal was "score higher than 80 on SWE-bench, like the top performers." **As of August
2026, that target is stale and would understate the system.** The landscape moved:

| Benchmark | State as of Aug 2026 | Implication for this project |
| :--- | :--- | :--- |
| **SWE-bench Verified** | **Saturating.** Top reported score ~96% (Claude Opus 5), with ~95–96% clustering across the frontier tier within ~1 point. | 80% is **below** the frontier baseline, not above it. Targeting 80 here would ship a system worse than an unscaffolded frontier model call. **Not a viable headline metric.** |
| **SWE-bench Pro** | **Unsaturated and now the industry's preferred hard benchmark.** Leader ~69.2% (Opus 4.8). OpenAI stopped reporting Verified in early 2026 and points to Pro. | **This is the real target.** An 80% here would be genuine SOTA. |
| **SWE-bench Lite** | Small, cheap, heavily contaminated by age. | Useful only as a fast CI smoke signal, never as a headline claim. |

Two further facts, both load-bearing for a client commitment:

- **Scaffold-attributable lift is documented at roughly 10–20 points** on a fixed model. That is the
  ceiling of what harness engineering itself can buy. **Absolute score is dominated by which model
  you are permitted to call.** If the client constrains model tier for cost reasons, that constraint —
  not architecture — sets the score.
- **Verification is weak.** Of ~100 models on the public leaderboards, approximately **one** carries an
  independent verification badge; the rest are vendor self-reported. Any number we publish must be
  independently reproducible or it is worth nothing in diligence.

### The corrected target (§3 formalizes this)

> **Primary:** SWE-bench **Pro**, beating the best published open scaffold result on the same model tier.
> **Secondary (the actually defensible claim):** **scaffold-attributable lift** — our harness vs. a
> naive single-shot baseline **on the identical model**, reported with confidence intervals against a
> measured A/A noise floor, plus **cost and wall-clock per resolved task**.

Lift-on-fixed-model is the claim that survives a model swap, a leaderboard reshuffle, and a hostile
diligence review. Absolute score does not. **Sell the lift, report the absolute.**

*Sources: see §13.*

---

## 2. Project concept

### Thesis

Frontier models already hold the intelligence. **The harness is the environment that makes that
intelligence reliable, cheap, auditable, and durable across long horizons.** AETHER is a
config-driven, self-improving execution environment that turns a frontier model into an autonomous
software engineer that can work for days, on codebases too large to fit in any context window,
without a human babysitting it and without lying about what it accomplished.

### What it is

- A **microkernel + typed ports** control plane. Pure domain logic, zero I/O; every effect crosses a
  wire-serializable port.
- A **capability-secured** execution environment. Every tool call is authorized at a single choke
  point and verified at the point of effect.
- A **measured** system. Every capability claim is a benchmark number with a confidence interval
  against a noise floor, or it is not made.
- A **composable workflow engine** — agent logic as a serializable, parametric DAG (ComfyUI's model
  applied to agent cognition), reconfigurable without touching kernel code.
- A **self-improving** system, bounded: the outer loop may optimize prompts, routing, and skills; it
  may never touch the Trusted Computing Base (policy, evaluator, gates, benchmarks).

### What it is not

- Not a model. Not a fine-tuning project. Not a chatbot.
- Not a framework with plugins-all-the-way-down. Extension points are enumerated and frozen at
  composition.
- Not a system that reports a number it cannot reproduce.

### The agency ladder (scope boundary)

| Level | Name | In scope? |
| :--- | :--- | :--- |
| L0 | Raw model call | Baseline for lift measurement |
| L1 | **Harness engineering** — tools, sandbox, retrieval, gates | **Phase 1** |
| L2 | **Loop engineering** — plan → generate → verify → repair; System 1/2 escalation | **Phase 1–2** |
| L3 | **Meta-loop (RHI)** — harness optimizes itself against a noise floor | **Phase 3** |
| L4 | **Multi-agent swarm** — harnesses delegating to harnesses | **Phase 4, gated on L1–L3 measured** |

---

## 3. Target definition — measurable and falsifiable

No capability is "done" without a number. These are the project's acceptance criteria.

| # | Target | Metric | Threshold | Measured by |
| :--- | :--- | :--- | :--- | :--- |
| T1 | **Scaffold lift** | Resolve-rate delta vs. single-shot baseline, same model, paired | **≥ +10 pts, CI excludes the A/A noise floor** | `bench --compare` |
| T2 | **Absolute capability** | SWE-bench Pro resolve rate | Beat best published open scaffold at same model tier | Official harness, independently reproducible |
| T3 | **Contamination control** | Resolve rate on private held-out suite vs. public suite | Gap **< 10 pts** (a larger gap means we are measuring memorization) | Private commit-replay suite |
| T4 | **Cost efficiency** | USD per resolved task | Beat naive baseline by ≥ 30% | Token accounting, real prices |
| T5 | **Long-horizon autonomy** | Unattended wall-clock on a multi-story task without human input | **≥ 8h**, resumable across process death | Hibernation/resume test |
| T6 | **Resource footprint** | Control-plane RSS, idle CPU | **< 300 MB RSS**, **< 1% idle CPU** (§7) | Profiling gate in CI |
| T7 | **Large-codebase capability** | Cold index + first useful retrieval on a ≥ 1M-LOC repo | Index < 10 min, recall@10 ≥ target on labeled query set | Indexer benchmark |
| T8 | **Determinism** | Cassette replay byte-equality | 100% | Replay CI gate |
| T9 | **Self-improvement** | Accepted RHI mutations that beat the noise floor | > 0, with zero TCB modifications admitted | RHI ablation |

**The honesty rule, learned the hard way.** The predecessor project shipped four gates hardcoded to
`True`, dead cost accounting, and stubs that fabricated success — every measurement taken over them
was uninterpretable and had to be discarded. **Instruments are built and verified before the
capability they measure.** A gate that cannot fail is a bug, and it is the most expensive class of
bug this project can have.

---

## 4. Non-negotiable architectural invariants

These are the anti-rewrite core. Each has a **mechanical enforcement**, because an invariant
enforced only by discipline is not an invariant — it is a wish.

| # | Invariant | Enforcement mechanism (CI-gated) |
| :--- | :--- | :--- |
| **I1** | **Pure domain.** Core logic imports no DB driver, no filesystem, no HTTP client. | Import-boundary linter; build fails on violation |
| **I2** | **Typed ports.** All I/O crosses a `Protocol`/trait/interface boundary. | Static type check, strict mode, zero errors |
| **I3** | **Wire-serializable ports.** Every port method is `async`; only serializable payloads cross. No file handles, callables, generators, or live objects. | Port conformance suite asserts round-trip serialization |
| **I4** | **Adapter substitutability.** Every adapter for a port passes the *same* parametrized conformance suite. | One suite, N adapters, run in CI |
| **I5** | **Single dispatch choke point.** All effects route through one authorized call site; grants verified at the point of effect, not merely at issuance. | Architecture test asserting no bypass path |
| **I6** | **Frozen extension resolution.** Adapters/tools/skills register via entry points, resolved once at composition, then frozen. No runtime scanning, no monkey-patching. | Composition test; runtime registration raises |
| **I7** | **Generator ≠ Evaluator.** The agent that writes code cannot modify the tests that grade it. Tests injected read-only from the base commit. | `tests_unmodified` hard gate over real diffs |
| **I8** | **Immutable TCB.** Policy, evaluator, gates, benchmark definitions, and CI config are unmodifiable by the agent or the outer loop. | TCB diff rejection in CI |
| **I9** | **Hard gates admit; proxies rank.** A learned scorer may order candidates and may never admit one or override a gate failure. | Type-level separation of `rank()` and `admit()` |

**Why I3 is the one that saves the project.** Wire-serializability is what lets any port move
out-of-process — to a Rust sidecar, a container, a remote peer — *without changing a single caller.*
It is nearly free on day one and impossible to retrofit. It is the single highest-leverage
constraint in this document.

**Deliberate revision to the "freeze contracts in week 1" plan.** Schemas written before any code
exercises them are wrong in ways only a running system reveals. Therefore: Phase 0 produces
**provisionally frozen** schemas; they are **ratified** after the walking skeleton (§12, Phase 1a)
round-trips them end to end. One ratification window, then the freeze is real and breaking changes
require a version bump. This is the difference between a contract and a guess with type annotations.

---

## 5. Capability inventory

Every capability requested, restated precisely enough to build and measure. **Tier** is when it
lands: `core` = Phase 1, `growth` = Phase 2–3, `research` = gated on an empirical trigger, never a date.

| Capability | Precise definition | Tier | Primary inspiration |
| :--- | :--- | :--- | :--- |
| **Long-session autonomy** | Run unattended ≥ 8h; survive process death; resume from durable state with grants re-minted, not restored | core | Hermes (hibernation), SAGIHA (`FrozenRunState`) |
| **Short-term memory** | Exchange-granular compaction with token headroom; summary turns; never mid-tool-call truncation | core | OpenCode (auto-compact at 95%), Claude Code |
| **Long-term memory** | Bi-temporal episodic store; FTS5 search over past sessions with LLM re-summarization on recall; linked knowledge net with backlinks | core | Hermes (session search), SAGIHA (knowledge net) |
| **Code indexing** | Tree-sitter AST-bounded chunks + BM25/FTS5 lexical tier + code graph (imports/calls/co-change); incremental file-watch updates | core | Aider (repomap + PageRank), SAGIHA |
| **Documentation indexing** | Same pipeline over prose; retrieval-excluded frontmatter for superseded docs | core | This repo's `retrieval: excluded` convention |
| **Dense retrieval** | Embedding tier over the lexical tier | research | Trigger: recall@10 misses traced to vocabulary mismatch |
| **Prompt caching** | Cache-stable prefix layout: `tools → system → memory → static repo context → dynamic turns`. Explicit cache breakpoints. Never mutate the prefix mid-session. | core | **Anthropic cache protocol**, DeepSeek automatic prefix caching |
| **Cache economics** | Track hit rate as a first-class metric; alert below threshold; cost model accounts write (1.25×) vs. read (0.1×) asymmetry | core | Anthropic pricing model |
| **Skills** | Agent-authored, versioned, self-improving procedure files; open `agentskills.io` format; created after complex tasks, refined during use | growth | **Hermes** (closed learning loop) |
| **Code-mode tool orchestration** | Agent writes a script that calls tools via RPC, collapsing an N-round-trip pipeline into one context-cheap turn | growth | **Hermes** (RPC tool scripts) |
| **Workflow DAG** | `WorkflowStep[In, Out]` nodes with typed sockets; graph serialized to config; **partial re-execution with per-node output memoization keyed by input digest** | core | **ComfyUI** (node graph, cached partial re-exec) |
| **Config-driven / parametric** | Re-order, swap, or parameterize any pipeline stage in `config.toml` with zero kernel changes | core | ComfyUI, SAGIHA composition root |
| **Dual-process loop** | System 1 ReAct for localized edits; System 2 verifier-guided Best-of-N + sequential repair across isolated worktrees; deterministic escalation ladder | core | SAGIHA, Grok Build (worktree concurrency) |
| **Parallel isolation** | Ephemeral git worktrees, one per candidate; pooled and reused; no file-lock collisions | core | **Grok Build**, SAGIHA |
| **Sandboxing** | Rootless container perimeter; egress allowlist; credential isolation; untrusted-by-default external content | core | OpenHands (gVisor), SAGIHA (Podman) |
| **Hooks & permissions** | Pre/post-tool interception; deny-first permission model for destructive effects | core | **Claude Code CLI** |
| **LSP diagnostics** | Warm language-server pool giving real-time type errors as a gate signal, not just tests | growth | OpenCode, SAGIHA |
| **Sub-agent delegation** | Spawn isolated sub-agents with scoped tool registries and their own context budget | growth | Claude Code, Hermes |
| **MCP interop** | Consume external MCP tools (grant-gated as untrusted); expose internal tools as an MCP server | growth | Claude Code CLI |
| **Meta-loop (RHI)** | Offline optimization of prompts, tool schemas, and model routing from trajectory corpus, accepted only when the lift beats a measured A/A noise floor | growth | SAGIHA RHI |
| **Learned candidate scorer** | Surrogate reward model ranking rollouts before expensive verification | research | Trigger: labeled rollout corpus large enough to beat rank-by-tests-passed |
| **Scheduling** | Cron-driven autonomous missions with delivery to external channels | growth | **Hermes** (scheduler) |
| **Deterministic replay** | Digest-keyed cassette record/replay; byte-equal step sequences; zero network in CI | core | SAGIHA |
| **Trajectory export** | SFT/DPO dataset export with eligibility gating, redaction, license check | growth | Hermes (trajectory compression), SAGIHA exporter |
| **Observability** | Structured event stream; offline trace mining; failure taxonomy | growth | OpenHands (event stream) |

---

## 6. Reference mining plan

Each cloned reference produces **one artifact** — a teardown document (§9, D-03) with a *take* and a
*reject* column. Reading code without producing an artifact is entertainment, not research.

| Reference | Extract | Deliberately reject |
| :--- | :--- | :--- |
| **Claude Code CLI** (`src/claude_code`) | Cache-stable prompt layout; pre/post-tool hooks; deny-first permissions; `CLAUDE.md` memory injection; JSONL trajectories; streaming TUI ergonomics | TypeScript control plane; single-workspace model (no parallel candidates) |
| **Hermes** (`src/hermes_agent`) | **Closed learning loop** (agent-authored self-improving skills); FTS5 session search + LLM re-summarization; **RPC code-mode tool scripts**; serverless sandbox hibernation (Modal/Daytona); cron scheduler; multi-channel gateway | Breadth over depth — six sandbox backends and six chat platforms are surface area we do not need in Phase 1 |
| **Grok Build** (`src/grok_build`) | Rust crate layout for performance sidecars; worktree concurrency; codegen discipline | Wholesale Rust core (§8, R4) — the domain is network-bound, not CPU-bound |
| **OpenCode** (`src/open_code`) | Auto-compaction at context threshold; LSP integration shape; SQLite session/message persistence; Bubbletea TUI patterns | Architecture wholesale — archived project, superseded; ReAct loop is less rigorous than ours |
| **SAGIHA** (`src/sagiha`) | CAR model; capability grants + dispatch choke point; port conformance suites; import-linter contracts; A/A noise floor; docs budget gate; **the H1–H4 honesty audit as a permanent cautionary tale** | Anything measured before its instruments were verified |
| **Anthropic caching protocol** | Prefix-match invalidation semantics; explicit breakpoints; TTL tiers; write/read cost asymmetry | — |
| **DeepSeek** | Automatic prefix caching economics; open-weight self-hosted tier for cheap bulk roles | Training-side techniques (MLA, GRPO) — out of scope, we do not train models |

---

## 7. Performance and resource budget

"Low RAM and CPU" made falsifiable. These are **CI-gated ceilings**, not aspirations.

| Resource | Ceiling | Rationale |
| :--- | :--- | :--- |
| Control-plane RSS (idle) | < 150 MB | The orchestrator is I/O-bound glue; anything larger means we are holding data that belongs on disk |
| Control-plane RSS (peak, single run) | < 300 MB | Excludes sandbox containers and LSP servers, which are budgeted separately |
| Idle CPU | < 1% | A hibernating agent must be free to leave running |
| Index memory, 1M-LOC repo | < 500 MB | Forces disk-backed FTS/graph, not in-memory structures |
| Cold index time, 1M-LOC repo | < 10 min | Beyond this, adoption fails on first contact |
| Incremental re-index, single file | < 200 ms | Must keep up with an editing agent |

**On "1M+ context."** A 1M-token window is a capability, not a strategy. Filling it costs real money
per turn, degrades attention on the middle of the context, and destroys cache economics. The
invariant is: **retrieval precision over context stuffing.** The 1M window is a *safety margin* for
tasks that genuinely need breadth, and the metric that matters is **resolve rate per dollar**, not
tokens placed in the window. Any design that reaches for a bigger window before exhausting retrieval
quality is optimizing the wrong variable.

---

## 8. Risk register — what actually kills this project

| # | Risk | Severity | Mitigation |
| :--- | :--- | :--- | :--- |
| **R1** | **Model tier dominates the score.** Client constrains cost; absolute score follows the model, not our work. | **Critical** | Contract on **lift** (T1), not absolute (T2). State this in the proposal *before* signing. |
| **R2** | **Benchmark saturation / migration.** Verified is ~96% and being retired; the goalpost moves again. | High | Target Pro; keep the Evaluator a port so a new suite is a new adapter, not a rewrite. |
| **R3** | **Contamination.** Public benchmark solutions are in training data; our number is inflated. | High | T3 private held-out suite, reported alongside every public number. |
| **R4** | **Premature Rust rewrite.** Weeks burned on a second toolchain for a network-bound workload. | High | Profile first. Port only measured hot paths behind an existing port (I3 makes this free). |
| **R5** | **Measuring on lying instruments.** The predecessor's exact failure mode. | **Critical** | Instruments before capability; every gate has a test proving it *can* fail. |
| **R6** | **Chasing noise.** Accepting harness changes that are random variance. | High | A/A noise floor measured before any "must not regress" rule is enforced. |
| **R7** | **Full benchmark as a per-commit CI gate.** Cost and latency make the loop unusable. | Medium | Curated 20–50 task smoke subset per PR; full suite nightly / pre-release. |
| **R8** | **Research components on a calendar.** Learned scorers starved of data underperform heuristics. | Medium | `research` tier items gated on empirical triggers only (§5). |
| **R9** | **Scope sprawl from reference mining.** Copying Hermes's six sandbox backends and six chat channels. | Medium | Reject column in §6 is binding. |
| **R10** | **Doc drift.** Two copies of a contract; agent retrieves the stale one. | Medium | One owner per topic; code wins for contracts; normative word budget with a CI ratchet. |

---

## 9. The Phase 0 document set — write in this order

Each document has an **acceptance criterion**: the condition under which it is done. Documents are
written in dependency order; parallelizable groups are marked.

### Group A — Concept and decisions (blocks everything)

| ID | Document | Acceptance criterion |
| :--- | :--- | :--- |
| **D-01** | `01-concept/vision-and-scope.md` | A reader can state what the system does, what it refuses to do, and the L0–L4 boundary, without reading code |
| **D-02** | `01-concept/glossary.md` | Every capitalized term used in D-03…D-20 is defined exactly once |
| **D-03** | `01-concept/reference-teardowns.md` | §6 table expanded per reference with a *take* and *reject* column and file-level citations |
| **D-04** | `08-decisions/` ADR-0001…N | One ADR per §4 invariant and per §11 open decision, each with **reversal conditions** |

### Group B — Contracts (the expensive-to-change layer; parallel after A)

| ID | Document | Acceptance criterion |
| :--- | :--- | :--- |
| **D-05** | `03-contracts/port-catalog.md` | Every port named, with its one-line responsibility and its adapters (present and planned). Definitions live in code; this navigates |
| **D-06** | `03-contracts/domain-schemas.md` | Every payload crossing a port is serializable; round-trip proven by the conformance suite |
| **D-07** | `03-contracts/event-catalog.md` | Every event the system emits, generated from code, CI-checked for drift |
| **D-08** | `03-contracts/tool-catalog.md` | Every tool, its effect class (PURE/MUTATING/DESTRUCTIVE), and its authorization requirement |
| **D-09** | `03-contracts/error-taxonomy.md` | Every failure mode is a typed error with a retry/abort/escalate disposition |
| **D-10** | `03-contracts/wire-protocol.md` | The UI↔engine contract: event stream schema, transport, and how TS types are generated from it |

### Group C — Architecture (parallel with B)

| ID | Document | Acceptance criterion |
| :--- | :--- | :--- |
| **D-11** | `02-architecture/kernel-and-dispatch.md` | The choke point and grant lifecycle are specified precisely enough to test for bypass |
| **D-12** | `02-architecture/context-and-cache.md` | The prefix layout is byte-stable and the cache invalidation rules are explicit |
| **D-13** | `02-architecture/memory-and-retrieval.md` | STM compaction policy, LTM schema, index tiers, and the dense-tier trigger condition |
| **D-14** | `02-architecture/workflow-dag.md` | Node/socket typing, graph serialization format, and the memoization key for partial re-execution |
| **D-15** | `02-architecture/security-and-threat-model.md` | Every threat has a mitigation and a test; untrusted-data envelope specified |
| **D-16** | `02-architecture/performance-budget.md` | §7 ceilings with the profiling method that enforces each |

### Group D — Method (parallel with B, C)

| ID | Document | Acceptance criterion |
| :--- | :--- | :--- |
| **D-17** | `05-measurement/benchmark-strategy.md` | Suites, noise floor protocol, contamination control, CI tiering (smoke vs. nightly) |
| **D-18** | `05-measurement/self-improvement-loop.md` | RHI mutable surface vs. TCB, acceptance statistics, rollback |
| **D-19** | `06-method/ci-and-quality-gates.md` | Every §4 invariant maps to a named CI job |
| **D-20** | `07-roadmap/phase-plan.md` | §12 expanded into phases with per-phase exit gates and empirical triggers |

### Group E — Governance (last)

| ID | Document | Acceptance criterion |
| :--- | :--- | :--- |
| **D-21** | `README.md` + `STATUS.md` | STATUS makes **zero** claims not supported by a line-level read of code. On day one it says "nothing is implemented" |
| **D-22** | `AGENTS.md` | Invariants an AI maintainer must never violate, stated imperatively |

---

## 10. Phase 0 exit gate

All must be true before the first `src/` commit:

- [ ] D-01 … D-22 exist and each meets its acceptance criterion
- [ ] Every §4 invariant has a named CI job in D-19, **even if the job is not yet implemented**
- [ ] Every §5 `core` capability has an owning document
- [ ] Every §5 `research` capability has a written **empirical trigger**, not a date
- [ ] Every §11 open decision is closed by an ADR with reversal conditions
- [ ] Schemas are **provisionally frozen** (ratification deferred to Phase 1a per §4)
- [ ] The §3 target table is agreed **in writing with the client**, including R1
- [ ] Zero broken relative links; normative word budget recorded as the ratchet baseline

---

## 11. Open decisions — blocking, require a human answer

These cannot be resolved from the code or from best practice. Each becomes an ADR.

| # | Decision | Options | Default recommendation |
| :--- | :--- | :--- | :--- |
| **Q1** | **Project name** | — | Pin before D-01; it appears in every path and package |
| **Q2** | **Control-plane language** | Python (fast iteration, best ecosystem, matches predecessor) vs. Go (single binary, low RSS) vs. Rust (fastest, slowest to build) | **Python** — the workload is network-bound; put hot paths in sidecars behind I3 |
| **Q3** | **Model tier the client will fund** | Frontier-only / mixed routing / open-weight self-hosted | **Mixed routing** — frontier for coding, cheap tier for planning and summarization. **This drives §3 more than any other choice.** |
| **Q4** | **UI surface and when** | TUI-first / desktop GUI / both / headless-only | **TUI-first**, GUI after the wire protocol (D-10) is ratified |
| **Q5** | **Wire format** | WS+JSON (schema-generated TS) vs. gRPC/Protobuf | **WS+JSON** for the UI leg; reserve Protobuf for a genuine cross-language sidecar boundary if R4's trigger ever fires |
| **Q6** | **Private held-out benchmark repo** | Which repository, licensed how | Required by T3; must not be public |
| **Q7** | **Greenfield vs. port** | New repo vs. evolve `src/sagiha` | **New repo**, mining SAGIHA per §6 — the predecessor was a one-day learning MVP and its measurement history is discarded anyway |
| **Q8** | **Compute budget for benchmarking** | $ per full benchmark run × runs per week | Sets R7's tiering; a full Pro run is not free |

---

## 12. After Phase 0 — preview only

Not binding. D-20 owns this; it is here so §9 has a destination.

| Phase | Delivers | Exit gate |
| :--- | :--- | :--- |
| **1a — Walking skeleton** | One end-to-end vertical slice: model → tool → worktree → test → gate → trajectory. Deliberately dumb adapters. | A trivial task resolves end to end; **schemas ratified**; replay byte-equal |
| **1b — Instruments** | Evaluator, harvester, A/A noise floor, cost accounting, smoke suite in CI | Noise floor **published**; every gate has a test proving it can fail |
| **2 — Capability** | Retrieval + code graph, System 2 Best-of-N + repair, container perimeter, compaction | T1 lift ≥ +10 pts with CI excluding the noise floor |
| **3 — Scale & autonomy** | Long-session hibernation, skills, workflow DAG, sub-agents, MCP | T5 (8h unattended), T7 (1M LOC), T6 (footprint) |
| **4 — Meta-loop** | RHI: prompt/routing optimization accepted only above the noise floor | T9, zero TCB modifications admitted |

**Sequencing principle: instruments before capability, slices before components, triggers before
calendars.** Every phase ships something end-to-end and measurable. No phase ships a component
whose value cannot yet be measured.

---

## 13. Sources

Benchmark landscape (§1), retrieved 2026-08-03:

- [SWE-bench Verified Leaderboard (August 2026) — BenchLM](https://benchlm.ai/benchmarks/sweVerified)
- [SWE-bench Verified Leaderboard — Steel.dev](https://leaderboard.steel.dev/leaderboards/swe-bench-verified/)
- [SWE-bench Pro Leaderboard (2026) — MorphLLM](https://www.morphllm.com/swe-bench-pro)
- [SWE-bench Pro Public Leaderboard — Scale Labs](https://labs.scale.com/leaderboard/swe_bench_pro_public)
- [SWE-bench Verified — llm-stats](https://llm-stats.com/benchmarks/swe-bench-verified)
- [SWE-bench in 2026: Benchmarks vs Scaffolding Reality](https://www.digitalapplied.com/blog/swe-bench-verified-june-2026-benchmark-vs-scaffolding-analysis)
- [SWE-bench Verified — Epoch AI](https://epoch.ai/benchmarks/swe-bench-verified)

> Leaderboard figures are predominantly **vendor self-reported**. Treat every number in §1 as a
> claim to be independently reproduced, including our own.
