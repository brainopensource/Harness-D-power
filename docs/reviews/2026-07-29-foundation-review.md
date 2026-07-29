---
status: advisory
date: 2026-07-29
scope: Full tree — 74 docs (~8,400 lines), src/ (~2,800 lines), tests/ (16 tests), CI, sprint plan. Sprint 2 in progress at review time (HEAD 0f61d5a).
---

# **Foundation Review — Architecture, Code & Delivery Sequencing**

> Verification commands run at review time: `uv run pytest -q` (16 passed), `uv run pyright` (0 errors),
> `uv run ruff check` (clean), `uv run lint-imports` (5 contracts kept, 1 vacuous warning).
> Every `D` finding below was confirmed against code, not prose.

---

## **1. Executive Verdict**

**Coherent, disciplined, and demonstration-poor.** The foundation is *not* overbuilt in code — ~2,800
lines, most of it contracts — and the enforcement machinery (import-linter layering, port-shape
meta-conformance, pyright strict, config refusals) is real and running. But the system has never
executed an autonomous step that used a tool: the ReAct loop's tool-dispatch branch is structurally
dead code (D1), the composition root binds a stub model in every mode (D3), the tool registry is
empty, and the CLI exposes only `version`. The 21 ports are backed by 4 adapters; capability
security is currently ceremony on a happy path that nothing exercises adversarially.

The sharpest problem is not architecture — it is **sequencing**. The project's own 2026-07-28 review
concluded the moat is the measurement layer and E0 comes first. Sprint 2 built kernel plumbing
instead, and its listed next steps (MCP driver, OTel exporter) extend the periphery further while
the core loop is broken and unmeasured. The docs are roughly 3:1 ahead of code by volume and
5–8:1 ahead by demonstrated behavior.

**Verdict per category asked:** not overbuilt (code), not prematurely coupled (boundaries are
genuinely clean), but **under-demonstrated at the core and over-specified at the periphery**.
The correct next move is one closed, measured loop — not more surface.

---

## **2. Validated Capabilities**

Claims below are backed by code that runs and tests/gates that pass today.

| ID | Capability | Evidence |
| :--- | :--- | :--- |
| V1 | Layered architecture is structurally enforced | `.importlinter`: 5 contracts kept (ports-pure, domain-pure incl. no `httpx`/`sqlite3`, TCB isolation, layers). CAR contract is vacuous until `agency/` has code. |
| V2 | Ports are wire-safe by construction | `tests/contracts/test_port_shape.py` — every port method async, payloads serializable, no `dict[str, Any]` without exemption, no `Grant` on any signature, aware datetimes. This suite is a genuine asset. |
| V3 | Config refuses insecure states at construction | `src/sagiha/domain/config.py::validate_security_invariants` + `tests/contracts/test_composition.py` — subprocess+autonomous refused, host network refused, `require_tests_unmodified=False` refused, role→tier consistency. |
| V4 | Dispatch choke point exists and fail-closes | `src/sagiha/kernel/dispatch.py` — authorize → grant → lease → execute → record, with denial short-circuit; `kernel/bus.py` interceptors deny on timeout or exception. Happy path unit-tested. |
| V5 | Append-only trajectory persistence | `src/sagiha/adapters/trajectory/sqlite.py` — WAL, DAG `StepId`, steps+events round-trip (but see D6). |
| V6 | Typed event schema with anti-drift gate | 32 events in `src/sagiha/domain/events.py` with `replay_relevant`/emitter/consumer metadata; `scripts/gen_event_catalog.py --check` runs in CI. |
| V7 | Type/lint hygiene | pyright strict on `src/`, ruff, 16 tests green in <1s. |

What is **not** validated by anything: an agent loop, a tool execution initiated by a model, a gate
evaluation, a replay verification, a policy denial in flight, memory retrieval quality, any cost or
latency number.

---

## **3. Defects (code-verified)**

| ID | Defect | Location | Consequence |
| :--- | :--- | :--- | :--- |
| **D1** | **ReAct loop can never dispatch a tool.** `step()` scans `model_response.content` for `isinstance(block, ToolCall)`, but `Message.content` is `list[ContentBlock]` — a discriminated union containing `ToolUseBlock`, not `ToolCall`. Pydantic validation makes the branch unreachable (confirmed at runtime: a `tool_use` block parses as `ToolUseBlock`; a raw `ToolCall` payload is rejected). | `src/sagiha/kernel/react.py:63-66`, `src/sagiha/domain/content.py:72-81` | The autonomous loop has never executed a model-initiated tool call. The passing test masks this by asserting only `step_id` fields. |
| **D2** | **Cassette replay ignores the request.** Replay serves entries by insertion index and silently repeats the last entry when exhausted. No request digest matching, no mismatch failure. | `src/sagiha/adapters/model/cassette.py:54-65` | "Byte-for-byte deterministic replay" is untestable as built; a drifted prompt replays the wrong response without error. |
| **D3** | **`build_kernel` binds a replay cassette in every mode**, including `mode="live"` (the `else` branch constructs the same replay provider). | `src/sagiha/composition.py:65-74` | Silent misconfiguration; the config contract (`live`/`record`/`replay`) is a fiction at composition. |
| **D4** | **`EffectClass` is never consulted.** `get_effect_class` has zero callers; dispatch and replay ignore it. | `src/sagiha/adapters/tools/registry.py:38-39` | ADR-0012's replay-safety mechanism (never re-execute `DESTRUCTIVE`) is decorative. |
| **D5** | **Failure signaling is incoherent.** Dispatch emits `ToolCallFailed(error_kind="execution_error")` when `result.truncated` is true — truncation is not failure. Handler exceptions are converted to ordinary `ToolResult`s whose only failure signal is prose text (`ToolResult` has no `is_error`; only the unused `ToolResultBlock` does). The `Disposition` taxonomy (RETRY/DEGRADE/SURFACE/ABORT) is never populated from real errors. | `src/sagiha/kernel/dispatch.py:103-119`, `adapters/tools/registry.py:49-55` | The agent cannot distinguish a failed tool from a successful one returning error-shaped text — a direct miss on the "failed tool vs failed hypothesis" requirement. |
| **D6** | **Stored events deserialize lossy.** `events_for_run` calls `Event.model_validate_json`, returning the *base* class — subclass payload fields are silently dropped on read. | `src/sagiha/adapters/trajectory/sqlite.py:121-135` | The audit trail is write-only today. Must resolve via the `ALL_EVENTS` discriminator before real trajectories accumulate. |
| **D7** | **`min_provenance` accepted, ignored.** `InMemoryMemory.recall` filters `kinds` and `valid_to` only. | `src/sagiha/adapters/memory/short_term.py:54-66`, `domain/memory.py:45` | A security-relevant filter silently no-ops; the provenance trust model is unenforced end-to-end (no prompt assembler exists to wrap `EXTERNAL` either). |
| **D8** | **Authorization is ceremony.** Policy allows everything not name-listed in `always_gate`; `scope_paths` are guessed from argument key names; the minted `Grant` is stored and popped but **never checked** against execution (no expiry check on the dispatch path, no path enforcement anywhere); `ResourceGovernor.acquire` never denies despite `max_concurrent_sandboxes`; `record_spend`/`remaining_budget` have zero callers. | `src/sagiha/kernel/policy/engine.py:34-66`, `kernel/governor.py:21-36` | "Secure by construction" currently means "structured to become secure." Acceptable for Sprint 2 — unacceptable to leave untested as tools become real. |
| **D9** | **Run state is unresumable.** Step sequence lives in `ReActEngine._step_sequence` (process memory), not derived from the `TrajectoryStore`. | `src/sagiha/kernel/react.py:43-48` | Interrupt/resume — an explicit product requirement — is impossible; a resumed run would collide on `PRIMARY KEY (run_id, branch_id, seq)`. |
| **D10** | **`ModelRequest` cannot describe a real request.** It carries only `messages` — no system prompt, no tool schemas, no sampling params, no model/role reference. | `src/sagiha/domain/content.py:91-92` | No real provider adapter can be written against it, and **every cassette recorded against this shape is invalidated when it changes**. This is the single most urgent contract fix. |
| **D11** | **Effect classification authority is inverted.** `ToolCall.effect` is asserted by the producer of the call (ultimately the model); the registry's classification is the trustworthy source and should be resolved at dispatch. | `src/sagiha/domain/content.py:95-103` | A model could label `git push` as `PURE`. Fix while the field is young. |

---

## **4. Critical Gaps**

| ID | Gap | Why it blocks scaling |
| :--- | :--- | :--- |
| G1 | No run loop. `ReActEngine.step()` is a single step; there is no `run()` with stop conditions, no verify stage, no Orchestrator implementation, no escalation, no cancellation path. | The understand→plan→act→verify→reflect loop exists only in DMARTIC prose. |
| G2 | Zero built-in tools; `DefaultToolRegistry` is constructed empty in composition. | Nothing for the loop to do even once D1 is fixed. |
| G3 | No Evaluator implementation → no `GateReport` has ever been produced. "Hard gates admit" is aspirational. | The project's central verification claim is unexercised. |
| G4 | No CLI run path. User-visible capability today: `sagiha version`. | Nothing is demonstrable to a user; the Day-Zero story in getting-started is aspirational. |
| G5 | **CI does not run `tests/unit/` or coverage.** The conformance job runs `pytest tests/contracts/` only; `fail_under = 80` is configured but never executed; the replay job is a stub that always skips. | Kernel behavior can regress silently while CI stays green. Cheapest high-value fix in the repo. |
| G6 | No E0 measurement substrate — no harvested tasks, no A/A noise floor, no baseline numbers — despite the roadmap ordering E0 first and the prior review naming it the moat. | Every future claim ("routing helps", "retrieval helps", "best-of-N helps") is unfalsifiable until this exists. |
| G7 | No prompt assembly: no system prompt, no tool schema rendering, no history packing, no `<untrusted-data>` wrapping of `EXTERNAL` provenance, no compaction. | Context economics and injection defense are both unimplemented. |
| G8 | No live model adapter (Anthropic/OpenAI SDKs declared as extras, unused; no Ollama adapter despite the local-benchmarking docs and ADR-0015 groundwork). | The loop cannot be exercised against a real model even manually. |
| G9 | The loop emits no `StepStarted`/`StepCompleted`/`ModelCall*` events — only dispatch emits. | Even the implemented slice is not fully traceable end-to-end. |

---

## **5. Unproven Assumptions**

| ID | Assumption | Risk if false | Smallest proving experiment |
| :--- | :--- | :--- | :--- |
| U1 | The dispatch choke point actually constrains agency code. | Capability security is a diagram. | Behavioral security tests: deny path, `always_gate` human-approval path, out-of-scope path write refused, forged `grant_id` rejected. The CAR import contract becomes non-vacuous only when `agency/` has code — add a canary module then. |
| U2 | Deterministic replay is achievable at useful fidelity. | Replay-based CI and evaluation collapse. | Record a 5-step run against a local model; replay with request-digest verification. Define **graded fidelity now** (see §10) instead of promising byte-for-byte. |
| U3 | The 21 port shapes survive contact with real adapters. | Churn in "stable" contracts; invalidated cassettes and conformance suites. | Write two real adapters (one ModelProvider, one Workspace) before labeling more ports `stable`. The 2026-07-28 review already demonstrated contracts don't survive first contact; `ModelRequest` (D10) proves it again. |
| U4 | SQLite event capture is cheap enough on the hot path. | Trace pipeline becomes the bottleneck it warns about. | Benchmark events/sec on a 200-step synthetic run before adding OTel double-writes. Almost certainly fine — measure once, stop worrying. |
| U5 | Best-of-N, AOI, RHI will pay for themselves. | Expensive machinery with no measured lift. | Already correctly gated behind E0 + A/A noise floor. Keep that discipline; build none of it before Block 2 exists. |

---

## **6. Safe Deferrals**

All of these can wait without harming the core design, because they sit behind already-typed ports
or additive event consumers: RHI/MetaImprover, AOI coprocessors, dense retrieval (ADR-0014),
System-2 best-of-N with N>1, A2A/remote pilots, performance sidecars, Graphiti-class episodic
memory, container sandbox (dev-mode subprocess is acceptable at `interactive` autonomy — the config
invariant already refuses the dangerous combination), warm LSP pool, **and notably the two items
Sprint 2 lists as next steps: the stdio MCP driver and the OTel exporter.** MCP multiplies tool
surface before one tool works end-to-end; OTel duplicates an event stream already persisted to
SQLite. Both are additive later; neither unblocks anything now.

---

## **7. Rewrite Risks — cheap now, expensive later**

Ordered by the cost curve, steepest first:

1. **`ModelRequest` shape (D10)** — every recorded cassette embeds it. Fix before any cassette fixture is committed.
2. **Typed event deserialization + upcasters (D6)** — every stored trajectory embeds event JSON. Fix before real runs accumulate.
3. **Resume identity (D9)** — derive `seq` from the store; add a `runs` table with status. Retrofitting resume onto in-memory state means migrating trajectory semantics.
4. **Effect-class ownership (D11)** and **grant scoping from tool schema, not guessed arg keys (D8)** — both are one-line-per-tool now, a security audit later.
5. **CI gap (G5)** — silent regressions compound into archaeology.
6. Event payloads embed full domain models (`TrajectoryStep` inside `StepCompleted`, etc.) and steps are stored twice (steps table + events). Acceptable — but pick one authoritative read path (steps table) and document the other as derived, or the "one source of truth" rule erodes.

---

## **8. Minimal Target Architecture (first autonomous, measurable loop)**

Keep exactly what exists, fix the defects, and add the smallest set that closes the loop:

```
Config → build_kernel ──► Kernel { bus, policy, governor, registry, trajectory, model }
                              │
             sagiha run ──► RunLoop (new): while not done and budget:
                              assemble prompt (system + tools + history)   ← G7 minimal
                              ModelProvider.complete / stream              ← Ollama + cassette
                              parse ToolUseBlock → ToolCall (D1 fix)
                              dispatch() choke point (unchanged)
                              append step; emit step/model events (G9)
                              stop: end_turn | budget | max_steps | approval
                              verify: Evaluator.evaluate → GateReport      ← subprocess acceptance checks
             sagiha replay ─► same loop, cassette provider, digest-verified (D2 fix)
```

Components: the existing kernel, **one** run loop, **five** built-in tools (`read_file`, `list_dir`,
`grep`, `apply_edit`, `run_command`) implemented over a subprocess `Workspace` adapter, **two**
model adapters (cassette fixed + OpenAI-compatible/Ollama), a minimal `Evaluator` that shells out
acceptance `check` commands, and two CLI verbs. Everything else in `ports/` stays as typed
contracts with `experimental`/`provisional` stability markers — they are cheap to keep and should
not grow conformance suites until an adapter exists.

---

## **9. Incremental Roadmap**

**Block 1 — Close the loop** (Sprint 3, see `docs/sprints/sprint-3.md`)
- *Capability*: `sagiha run` fixes a failing test in a fixture repo end-to-end on a cassette in CI, and against local Ollama manually. `sagiha replay` verifies the recorded run.
- *Contracts*: `ModelRequest` v2; `ToolUseBlock→ToolCall` resolution at the registry; typed event read path; `runs` table + resume.
- *Acceptance*: e2e cassette test green in CI; replay digest-verify green; full `pytest` + coverage in CI; security deny-path tests green.
- *Non-goals*: MCP, OTel, sandbox, retrieval, best-of-N, routing.
- *Depends on*: nothing.

**Block 2 — Measure (E0-lite)**
- *Capability*: `sagiha bench` runs 10–30 tasks harvested from the ADR-0015 repo and emits a report: task success, gate pass rate, cost/success, latency, steps. A/A noise floor on ≥3 tasks.
- *Contracts*: benchmark task format (TaskSpec + fixture commit + acceptance checks); report schema.
- *Acceptance*: committed baseline JSON; re-run reproduces within noise floor on cassettes.
- *Non-goals*: leaderboard breadth; SWE-bench claims.
- *Depends on*: Block 1.

**Block 3 — Enforce authority**
- *Capability*: path-scoped write authorization, blocking `ApprovalRequested` flow, governor admission (deny at `max_concurrent`), spend recorded from real `TokenUsage` and enforced.
- *Acceptance*: conformance suite for PolicyEngine (deny, expiry, scope violation, forged grant); out-of-worktree write refused in an e2e test.
- *Depends on*: Block 1 (tools must exist to be denied).

**Block 4 — Retrieve and remember**
- *Capability*: FTS5 lexical index + code-graph expansion (per ADR-0014, no dense tier); SQLite-backed `Memory` with provenance filtering fixed (D7); recall@k measured on a labelled query set; retrieval on/off ablation via Block 2.
- *Depends on*: Blocks 1–2 (retrieval lift must be measurable or it doesn't ship).

**Block 5 — Isolate and integrate**
- *Capability*: worktree manager, container sandbox + egress allowlist, then MCP driver and OTel exporter.
- *Depends on*: Block 3 (sandbox is the perimeter; policy must already be real).

---

## **10. Measurement Plan**

All metrics derive from the persisted event log — that is the architecture's genuine advantage;
no separate metrics pipeline is needed.

| Metric | Source | Definition |
| :--- | :--- | :--- |
| Task success | `RunCompleted.gate_report` | `admitted == True`; report alongside gate pass-rate per criterion. |
| Cost per successful task / per step | `ModelCallCompleted.cost`, `TokenUsage` | Sum per run ÷ successes; distribution per step. |
| Latency | `RunStarted`→`RunCompleted` timestamps; per-step from `StepStarted`→`StepCompleted` | Wall-clock; report p50/p95. |
| Retrieval quality | Labelled query set (Block 4) | recall@10, MRR; *contribution* = Block-2 success delta with retrieval ablated. |
| Cache effectiveness | `TokenUsage.cache_read_tokens / input_tokens` | Alert < 0.80 once prompt caching exists (per context-and-cache doc). |
| Replay fidelity (graded) | `sagiha replay --verify` | **L0**: event count+types match; **L1**: step sequence and tool calls match by digest; **L2**: byte-identical payloads for `replay_relevant` events. Report the level achieved — do not promise L2 globally. |
| Tool-policy denials & safety | `ToolCallDenied`, `ApprovalRequested/Resolved` | Denial count by reason; human-approval latency; zero out-of-scope writes in e2e suites. |
| Recovery | Scripted kill at step N + `sagiha run --resume` | Resume success rate; duplicate-step count must be zero (D9 fix). |

---

## **11. Direct Recommendations**

**Keep** (working, load-bearing): domain models; port meta-conformance suite; import-linter
contracts; config refusals; dispatch choke-point structure; event catalog generation; the
decision discipline of the ADR log (0005, 0008, 0010, 0012, 0014 are all correct calls).

**Fix now** (before more surface): D1–D6, D9–D11; CI running the full test suite with coverage (G5);
`build_kernel` honoring `model.mode` (D3).

**Simplify**: Sprint 2's definition of done — drop MCP and OTel from it; a sprint's exit should be
a demonstrated capability, not adapter count. Treat the steps table as the single authoritative
read path for trajectories.

**Redesign**: failure signaling — add `is_error` to `ToolResult`, populate `Disposition` from real
error taxonomy, stop conflating truncation with failure (D5). Replay — request-digest matching with
loud mismatch (D2).

**Postpone**: MCP driver, OTel exporter, container sandbox, LSP, dense retrieval, best-of-N N>1,
AOI, RHI — all correctly deferred already; the only change is moving MCP/OTel out of Sprint 2.

**Delete** (doc hygiene, X-findings): the duplicated `Protocol`/`BaseModel` definitions still living
in `docs/03-contracts-and-models/task-and-acceptance.md` and
`docs/02-architecture/neural-symbolic-memory.md` (whose `Memory` protocol shows `neighbors`/
`backlinks` that the real port does not have) — replace with references to `src/`, per the repo's
own rule. Fix the two stale contradictions: Phase-4 "BM25 + dense" vs ADR-0014, and the RHI doc's
"one derived from the other" trace-ownership sentence vs the normative EventBus model.

---

*Judged by demonstrated autonomous capability, safety, maintainability, and measured improvement:
the foundation earns its contracts but has not yet earned its second layer of ambition. Close the
loop, measure it, then grow.*
