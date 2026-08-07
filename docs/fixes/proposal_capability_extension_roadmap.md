---
status: rationale
updated: 2026-08-07
---

# Proposal: Capability Extension Roadmap — Memory, Knowledge Graphs, MCP, Browsing, and What Each Costs

**Status: proposal. Nothing here is decided, and nothing here is measured.**

This document takes the capability layer from
[`proposal_abstraction_and_harness_composition.md`](./proposal_abstraction_and_harness_composition.md)
and asks the next question: *what plugs into it, in what order, and what does each one cost in
correctness terms?* It exists partly to record four corrections to an earlier draft of this
material, because the errors are the instructive part.

---

## 0. Four corrections, stated first

An earlier draft of this chapter made four claims that this project's own rules forbid. They are
recorded here rather than quietly fixed, because each is a live temptation that will recur.

### C1 — A competitor comparison table with no comparative instrument

The draft contained a table with columns "Claude Code / OpenHands / Kimi CLI" vs. "AETHER" and
cells reading *~60% Token Reduction*, *~90% Token Reduction*, *~80% Cost Reduction*, *~65× USD
Savings*, *~50% Token Reduction*.

Every cell is inadmissible, for three independent reasons:

1. **We have never run those harnesses.** [`spec.md` §9](../spec.md#9-standing-rules) forbids
   citing a competitor's published numbers as evidence, and [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published)
   is categorical: *"A number we did not measure on our own instruments never appears in a
   result, a claim, or a regression gate."*
2. **The mechanisms being credited do not exist.** `LayeredAssembler` is `TASK-056`, unbuilt.
   `RoutingModelProvider` is `TASK-042`, unbuilt. `Compactor` is `TASK-024`, unbuilt. A savings
   figure for an unwritten component is not an estimate, it is a wish.
3. **`measurement.md` §6 names the instrument this claim requires** and it is `TASK-015`'s
   comparative-lift rig — bare model, AETHER, and OpenHands, same model, same manifest, through
   **our** evaluator. The rig's seam exists; the OpenHands arm is explicitly out of scope until
   after the floor. Until that arm runs, the competitive claim is *unsubstantiable by
   construction*, which is exactly why `TASK-015` was written.

The `~65×` figure specifically was lifted from
[`proposal_workflows_hybrids_improvements.md`](./proposal_workflows_hybrids_improvements.md) §6,
where it is labelled **arithmetic over a rate card at list price, not a measurement**, and where
it compares a hybrid arm against an *all-frontier AETHER arm at the same node count* — not
against any competitor. Moving it into a competitor column changed what it means.

**The correct form** is §5 of this document: a hypothesis table, each row naming the experiment
that would settle it.

### C2 — A provider cache-hit claim

The draft said prompt-token costs *"drop by 80%–90% via hardware KV-cache hits."*
[ADR-0010](../decisions/0010-context-prefix-layers.md) and
[`measurement.md` §5](../measurement.md#5-gate-design) both specify the opposite metric on
purpose: **the I10 gate is harness-side byte-identical-prefix stability over a fixed recorded
replay, not a provider-reported hit rate.** Provider cache semantics diverge (explicit Anthropic
`cache_control` blocks vs. implicit OpenAI-compatible prefix caching), and
`openai_compatible.py:40` records that breakpoints are deliberately not emitted there at all. The
local B2 endpoint may expose no cache metric whatsoever, so a gate keyed to a provider number
would be unmeasurable on the reference instrument.

The claim we can make and gate is: *layers L1–L4 are byte-identical across turns of a run.* What
a provider does with that is a secondary metric where it exists.

### C3 — The loops were relabelled

The draft described the **outer loop** as *"walks declarative YAML topologies, checks static graph
contracts, skips cached nodes via memoization."* That is the **inner** loop — `workflow/executor.py`,
one task. The outer loop is `measurement/runner.py`: a run over N tasks × arms producing paired
outcomes for the statistics engine. The distinction is not pedantry; the memoization task
(`TASK-032`) speeds up the *inner* loop so the *outer* loop's ablations become affordable, and
conflating them makes the sequencing argument unreadable.

### C4 — "Admits or deletes variants automatically"

The draft described the meta-loop as admitting variants automatically after McNemar/Holm. Nothing
in this system admits anything automatically. [ADR-0003](../decisions/0003-statistical-admission-protocol.md)
requires a **pre-declared** family merged before any arm runs, N **derived** for ≥0.80 power, and
a human reading the result; [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
requires human review for anything touching the TCB. The statistics engine's job is to *refuse* —
it will not compute corrected p-values for an undeclared family. Automation of admission is the
one thing that would let a self-improving system weaken its own judge over time.

---

## 1. Memory, and the contamination problem nobody has flagged

Memory is the highest-value capability on this list and the one with the sharpest measurement
hazard. Both halves need stating.

### 1.1 Short-term memory — mostly built, one gap

| Mechanism | Status |
| :--- | :--- |
| Tail-biased truncation of gate output | **Built.** `measurement/evaluator.py::tail_biased`, used by `repair.py` at `REPAIR_OUTPUT_CHARS = 3000` and by the gate itself, so *the repair prompt and the gate never disagree about what the failure was* |
| Failing-assertion isolation | **Built.** `repair.py:78-88` scans for `assert` / `AssertionError:` / `FAIL:` and hoists it |
| L5 dialogue history as a first-class object | **Missing.** There is no assembler, so there is no L5 |
| Structural compaction | **`TASK-024`, unbuilt.** Blocked on the assembler |

The earlier draft proposed a new `TracebackTrimmer`. It already exists under the name
`tail_biased`, and the *reason* it lives in `measurement/` rather than in a node is the
non-obvious part worth preserving: the truncation the prompt sees is the same truncation the gate
recorded.

### 1.2 Long-term memory — and why it is an instrument hazard

A `LessonStore` that carries insights from task A into task B is not a neutral capability on a
benchmark. **If tasks A and B are in the same manifest, a lesson learned on A and applied to B is
train-on-test.** It breaks three things at once:

- **The paired design.** McNemar assumes the two arms see each task under identical conditions.
  An arm whose behaviour on task 40 depends on tasks 1–39 has an order effect the pairing does
  not model.
- **The split discipline.** [`measurement.md` §4.2](../measurement.md#42-splits-and-why-they-are-pinned)
  pins DEV/HOLDOUT/SEALED so a mechanism tuned on DEV cannot leak into an admission run. A
  persistent store is a channel that crosses that boundary invisibly, because nothing in the
  manifest records it.
- **Reproducibility.** `measurement.md` §6 requires a run to name its instrument. A store mutated
  by previous runs makes the same config produce different results, and the instrument tuple
  cannot capture it.

This is not an argument against long-term memory — it is the single most likely lever on
repository-specific performance. It is an argument that it needs **four constraints, not zero**:

1. The store is **part of the instrument tuple**: `sha256` of its contents enters the run hash, or
   the run is not reproducible.
2. It is **off by default**, an `AblationFlags` field like every other mechanism.
3. It is **scoped and cleared per split.** A lesson learned on a DEV task may never be visible on
   a HOLDOUT or SEALED run. Enforced in the engine, not by convention.
4. Its ablation reports **order sensitivity** — the same manifest in a shuffled order must give
   the same resolve rate, or the mechanism is producing an order effect rather than a lift.

**A `Memory` port is named in [`spec.md` §4](../spec.md#4-ports)'s growth tier**, admitted only
with an adapter ([ADR-0005](../decisions/0005-eight-ports-adapter-first.md)). That is the entry
route, and it is post-floor.

### 1.3 Knowledge graphs — a `ContextSource`, not a port

The "Obsidian-style graph" idea is sound and it does not need new architecture. A symbol/import
relationship graph is a **`ContextSource`** (`TASK-054`) built over the `Indexer` port, which
already exists and already passes conformance and is currently reachable from nothing.

Two corrections to the earlier framing:

- **Semantic/embedding retrieval is not the same tier.** `spec.md` §4 lists `CodeGraph` and
  `Memory` as growth-tier ports; [ADR-0011](../decisions/0011-no-lsp-adapter.md) deliberately
  keeps the semantic tier out and defers to the project's own toolchain. A `VectorIndexSource`
  is a new port with a new adapter, an ADR-0005 entry, not a source implementation.
- **It is a mechanism, so it needs an ablation.** Symbol-graph retrieval vs. whole-file retrieval
  is exactly the comparison the capability layer exists to make cheap. It promotes on a floor-
  clearing result or it is deleted ([`spec.md` §7](../spec.md#7-measurement)).

---

## 2. Prompt layering — what is true, and what is aspirational

| Claim | Status |
| :--- | :--- |
| Five layers L1–L5, append-only within a run | **Specified** (ADR-0010), **unbuilt** (`TASK-056`) |
| ≤4 cache breakpoints placed at layer transitions | Specified; `ModelMessage.cache_breakpoint` exists and **nothing sets it** |
| L1–L4 byte-identical across repair turns | **The goal**, and the CI gate. Not currently true — layering is `f"{instructions}\n\n## Header\n{text}"` in `architect.py` |
| Provider cost drops 80–90% | **Not a claim this project may make.** See C2 |

One structural note the earlier draft got right and is worth keeping: the reason competitors'
prompt caches thrash is that a growing dialogue is concatenated into a single shifting string, so
any change invalidates the whole prefix. The five-layer split is the fix, and its correctness is
checkable *without* a provider: replay a fixed trajectory, hash the L1–L4 prefix at every turn,
and assert it never changes. That is a real gate, it can fail, and it needs no vendor cooperation.

---

## 3. Tools: MCP, browsing, and the egress question

All three are **adapters of the existing `ToolRegistry` port** — no new port
([ADR-0016](../decisions/0016-mcp-integration-trust-model.md) says so explicitly for MCP).
`BuiltinToolRegistry` already labels every output `Provenance.UNTRUSTED_EXTERNAL` **at
construction**, which is the timing that matters (ADR-0015): a caller never has to remember to
taint a tool result afterwards.

Three things the earlier draft understated:

**The tool perimeter is currently the weakest part of the system.** `BuiltinToolRegistry._bash`
uses `create_subprocess_shell` **uncontained on the host** while the evaluator is containerized.
`STATUS.md` records this as an accepted deviation with `TASK-018`'s second half as the fix.
**Adding MCP or a browser tool before that container exists multiplies an already-asymmetric
perimeter**, and MCP servers are third-party code by definition.

**A browser tool is a new data-egress surface, and so is any paid model route.** Hybrid
topologies send repository contents to a third-party endpoint that all-local topologies do not;
a browser adds outbound requests driven by content the agent did not write. Neither is forbidden,
both need to be a declared field in whatever config governs a run — and `--network none` on the
*evaluator* says nothing about the *tool* container, which is a different image with a different
lease class precisely so a runaway tool loop cannot starve the judge.

**I11 is not currently enforced on the model path.** `DefaultPolicyEngine`'s predicate is correct
— a capability-widening request justified by an untrusted span fails closed — but nothing on the
model path produces untrusted spans, and repository content is labelled `AGENT` rather than
`UNTRUSTED_EXTERNAL` specifically so the tool loop keeps working. Adding tools whose outputs
*are* correctly labelled untrusted will make `DispatchFacade.shell` (which sets
`widens_capability=True`) start failing closed. **That is the gate working**, and it is
`TASK-030a`'s escalation taxonomy that makes it survivable. Tools before `TASK-030a` means either
a broken tool loop or a laundered provenance label.

---

## 4. Ordering

```
  ┌─ Sprint 4 ─────────────────────────────────────────────────────────────┐
  │  Instrument restoration  →  A/A FLOOR                                  │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
  ┌─ Sprint 5 ─────────────────────▼──────────────────────────────────────┐
  │  agency/ · ContextSource · Inference · Assembler · ModelNode · RunConfig│
  └────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  ┌───────────────┐      ┌────────────────────┐     ┌─────────────────────┐
  │ CHEAP & SAFE  │      │ NEEDS A PERIMETER  │     │ NEEDS AN INSTRUMENT │
  │ SymbolSource  │      │ TASK-018 container │     │ LessonStore         │
  │ GraphSource   │      │  → MCP registry    │     │ VectorIndexSource   │
  │ Compaction    │      │  → browser tool    │     │ (contamination §1.2)│
  │ (TASK-024)    │      │ TASK-030a taxonomy │     │ growth-tier ports   │
  └───────────────┘      └────────────────────┘     └─────────────────────┘
   ablation-gated         security-gated              measurement-gated
```

The left column is the one to start with: `SymbolSource` and a graph source are pure
`ContextSource` implementations over an adapter that already exists and already passes
conformance. They add no egress, no new port, and no persistent state, so their only gate is the
ordinary one — clear the floor or be deleted.

---

## 5. Hypotheses, replacing the competitor table

Every row is a **hypothesis with a named experiment**, per `measurement.md` §6's rule that
third-party figures may *motivate an ablation* and nothing more.

| Hypothesis | Mechanism | The experiment that settles it | Blocked on |
| :--- | :--- | :--- | :--- |
| Symbol-scoped retrieval beats whole-file retrieval at equal budget | `SymbolSource` | Paired arms, same manifest/model/seed, primary outcome pass@1, secondary prompt tokens | Floor, `TASK-054` |
| Tail-biased gate output beats untruncated | already built | Ablation arm with truncation disabled | Floor |
| L1–L4 prefix stability is achievable at ≥99% over a fixed replay | `LayeredAssembler` | The `TASK-056` CI gate — **harness-side, no provider involved** | `TASK-056` |
| Per-role routing gives non-inferior resolve rate at lower cost per resolved task | `RoutingModelProvider` | Hybrid family, 3 declared hypotheses, derived N | Floor, `TASK-042`, **`TASK-043`** (or every arm reports $0.0000 and the check passes vacuously) |
| Cross-task lessons lift repository-specific performance without order effects | `LessonStore` | Ablation **plus a shuffled-order replication** — a lift that disappears under shuffling is an order effect | Floor, §1.2's four constraints |
| AETHER's lift exceeds OpenHands' on the same model and manifest | the whole harness | **`TASK-015`'s OpenHands arm through our evaluator.** There is no other admissible route to this claim | Floor, `TASK-015` completion |

The last row is the mission statement. It has exactly one instrument, it is already a funded
task, and until it runs the honest answer to "how do we compare to Claude Code or OpenHands" is
**we do not know, and we have not measured it.**

---

## 6. What this document does not claim

- **No lift, no cost saving, and no competitive comparison.** Every quantity above is a
  hypothesis with an experiment attached.
- **No security claim for MCP, browser, or routing.** The sandbox is the perimeter
  ([ADR-0008](../decisions/0008-shell-ast-classifies.md)), and the tool sandbox does not exist yet.
- **No new ports are proposed here.** `Memory` and `CodeGraph` are named in `spec.md` §4's growth
  tier and enter under ADR-0005 with a first adapter, or not at all.
- **Cross-task memory is proposed as a hazard as much as a feature**, and §1.2's four constraints
  are the minimum, not a wish list.
