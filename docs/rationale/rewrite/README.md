---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Phase 0 Rewrite Set

> [!NOTE]
> **LLM / AI AGENT NOTICE**: Everything in this directory is Phase-0 rationale for the AETHER
> rewrite. None of it is binding and none of it defines a contract. Contracts live in
> `src/aether/ports/` and `src/aether/domain/` — code wins. Read these for *why*, not *what*.

Twelve documents answering [`review_project_rewrite_v300.md`](../reviews/review_project_rewrite_v300.md)
(the track-A RFP) under the parent [Phase-0 charter](../reference/PLANNING.md).

Track B — a parallel, independent proposal by a second Tech Lead, addressed by
[`review_project_rewrite_v300B.md`](../reviews/review_project_rewrite_v300B.md) — targets
`docs/rationale/rewrite_b/` and is deliberately not reconciled with this set. Comparing two
independent architectures is the point of running both.

---

## Reading order

**Start here if you read nothing else:** [`rewrite_v300_measurement_strategy.md`](./rewrite_v300_measurement_strategy.md).
It contains the four blockers that have prevented this project from producing a single valid
benchmark number, and everything else is downstream of fixing them.

### Group A — foundation

| Document | Answers | Contains |
| :--- | :--- | :--- |
| [`rewrite_v300_reference_teardowns.md`](./rewrite_v300_reference_teardowns.md) | RFP §3, D-03 | Take/reject per cloned reference; the study policy; capability provenance |
| [`rewrite_v300_auditoria_sagiha.md`](./rewrite_v300_auditoria_sagiha.md) | RFP §5.1 | Keep / Refactor / Delete over 12,949 LOC; the migration ledger |
| [`rewrite_v300_decisoes_runtime.md`](./rewrite_v300_decisoes_runtime.md) | RFP §4-A, §5.2 | Python vs Go vs Rust; FFI vs IPC latency; commercial packaging and IP |

### Group B — mechanism specs

| Document | Answers | Contains |
| :--- | :--- | :--- |
| [`rewrite_v300_mecanismo_edicao.md`](./rewrite_v300_mecanismo_edicao.md) | RFP §4-B | The repair loop; anchored edits; verification tiers; Architect/Editor |
| [`rewrite_v300_contexto_memoria.md`](./rewrite_v300_contexto_memoria.md) | RFP §4-C | Cache breakpoints and their traps; compaction; retrieval; memory |
| [`rewrite_v300_seguranca_sandbox.md`](./rewrite_v300_seguranca_sandbox.md) | RFP §4-D | CAR model; perimeter; TaintGate; TCB; the isolation defect |
| [`rewrite_v300_autonomia_agi.md`](./rewrite_v300_autonomia_agi.md) | RFP §4-E | Hibernation; skills; code mode; RHI; the Conductor |

### Group C — synthesis

| Document | Answers | Contains |
| :--- | :--- | :--- |
| [`rewrite_v300_measurement_strategy.md`](./rewrite_v300_measurement_strategy.md) | D-17 | Re-baselined landscape; the four blockers; noise floor; CI tiering |
| [`rewrite_v300_decisoes_adr.md`](./rewrite_v300_decisoes_adr.md) | RFP §5.3, D-04 | A-001…A-017; Q1–Q8 closed or escalated; all 27 prior ADRs adjudicated |
| [`rewrite_v300_blueprint_arquitetura.md`](./rewrite_v300_blueprint_arquitetura.md) | RFP §5.4 | Invariants; layers; port catalog; loop; event stream; package layout |
| [`rewrite_v300_uiux_tui.md`](./rewrite_v300_uiux_tui.md) | D-10, Q4 | Wire protocol; TUI progression; the LIVE/MOCK discipline |
| [`rewrite_v300_roadmap_sprints.md`](./rewrite_v300_roadmap_sprints.md) | RFP §5.5 | M0–M5 with quantitative exit gates; dependency graph; risks |

---

## The five findings that shaped the set

1. **Zero valid benchmark numbers exist.** Four concrete blockers, all fixable, all in
   [measurement strategy §2](./rewrite_v300_measurement_strategy.md). One of them — a model endpoint —
   is a commercial decision, not engineering, and it is on the critical path.
2. **The landscape moved under the charter.** SWE-bench Pro's leader is ~80.3%, not the 69.2% recorded
   two days earlier. Verified saturates at ~96%. Targets re-baselined to Pro ≥80% / Verified ≥96%,
   with lift published alongside because absolute score is dominated by model tier.
3. **Prompt caching is architecture, not optimization.** Two traps are specific to coding agents and
   invisible until the invoice arrives: the 20-block lookback window, and Best-of-N fan-out turning
   N−1 cache reads into N−1 cache writes. Both have cheap fixes that must be designed in.
4. **Five of SAGIHA's seventeen ports have no implementation.** Declaring a boundary is not having
   one. AETHER starts with eight and adds each new port together with its first adapter.
5. **The predecessor's real asset is its discipline, not its code.** Reflection-based port contracts,
   import-linter layering, loud stubs, tri-state gates, and a documented history of deleting a
   component rather than shipping a false-success shell. A rewrite that ports the code and drops the
   discipline is a regression wearing a version bump.
6. **Hermes' best ideas are in its failure handling, not its feature list.** Read at depth
   ([teardowns §1](./rewrite_v300_reference_teardowns.md)), the seven mechanisms worth taking are:
   compaction summaries treated as an instruction channel *and* a trust boundary; loop guardrails as
   typed policy with three signals rather than one counter; background review forking onto the
   parent's warm prefix; a skill **curator** that consolidates rather than only archiving; an API
   error taxonomy where "compress context" is a recovery action; a single trajectory format shared by
   runner, batch and training compressor; and a lifecycle guard against the agent restarting its own
   supervisor. Each closed a real gap in this set rather than confirming it.
7. **The most productive documentation reference was a field guide, not a codebase.** `src/claude_refs/` contributed
   quantitative constraints no code teardown yields: the non-linear context cliff, the ~150-instruction
   adherence ceiling, failure-triggered context drift, blast-radius success rates, three sandbox escape
   vectors, and the sub-agent isolation rule. Every one of those numbers is someone else's and enters
   as a **hypothesis with a named experiment**, per
   [measurement strategy §1](./rewrite_v300_measurement_strategy.md).

### One open item for the reviewer

`src/claude_refs/claude-code-analysis` is a third-party **reverse-engineering teardown** of a closed
source tree. It is MIT-licensed, public, and not code — but its provenance sits in the grey zone of
[A-007](./rewrite_v300_decisoes_adr.md), which defers artifacts derived from closed sources. It has
been used only at capability-inventory altitude, with the tension flagged in
[teardowns §3b.2](./rewrite_v300_reference_teardowns.md) rather than resolved silently. Nothing in the
set depends on it; if the reading is too permissive, the deletion cost is low.

---

## Conventions

Every file here carries `status: rationale` and `retrieval: excluded` — outside the normative word
budget, and skipped by the indexer, because retrieving superseded reasoning as though it were current
is how an agent acquires contradictions.

The nine RFP-mandated filenames are kept **verbatim**, Portuguese slugs included, because the RFP
specifies them. The three additions (`reference_teardowns`, `measurement_strategy`, `uiux_tui`) use
English slugs. Document bodies are English per [A-008](./rewrite_v300_decisoes_adr.md).

Reference harnesses are cloned to `src/<name>/` — gitignored, excluded from `ruff` and `pyright`,
never imported. Referenced here as code spans, never as links, since the trees do not exist in CI.
