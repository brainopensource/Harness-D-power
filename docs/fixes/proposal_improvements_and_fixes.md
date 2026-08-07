---
status: historical
retrieval: excluded
updated: 2026-08-06
---

# PROPOSAL — Improvements & Fixes to Lock `docs/` for Development

> **EXECUTED 2026-08-06.** This proposal has been applied to the tree and is now history; it
> is not maintained. What is true is [`../spec.md`](../spec.md) and
> [`../decisions/`](../decisions/README.md).
>
> **Two divergences from the text below, recorded so the difference is not read as drift:**
>
> 1. **Item 27 went the other way.** The recommendation was to rename `docs/concepts/` →
>    `docs/00/`; the decision was to **keep `concepts/`** and fix the seven inbound links.
>    The live tree names its directories (`decisions/`, `agile/`, `development/`, `fixes/`);
>    `00/` was the archive's numbering convention and the archive is slated for deletion.
> 2. **Item 29 went the other way.** The `status: operational` tag was not introduced.
>    Gate-bearing files (`agile/milestones.md`, `agile/roadmap.md`) were retagged
>    `status: normative` instead — they bind, so they count. Measured cost: 910 words against
>    ~11,000 of headroom, so a third tag bought nothing a retag did not.
>
> **One defect this proposal missed**, found by running the gate rather than reading it: five
> files under `docs/` carried no `status:` frontmatter — the four in this directory and
> `concepts/rewrite_v300_agi_path_after_all_milestones_are_delivered.md`. The docs-budget job
> was failing on those, not on word count (3,009 against a 15,000 ceiling). D6 diagnosed an
> inflated ceiling; the gate was red for an unrelated reason.

Consolidated, file-by-file change list. Every item cross-references the audit (D-numbers, [`proposal_architecture_audit.md`](./proposal_architecture_audit.md)) or the refinement docs. Ordered so the tree can be locked in **three PRs**: PR-1 (S1 blockers), PR-2 (spec/ADR amendments), PR-3 (hygiene). New ADRs are drafted in outline at the end.

---

## PR-1 — Blockers (must land before Sprint-01 executes)

### `docs/agile/sprints/sprint-01.md`
1. **Add Task 0 (blocking, first PR)**: migrate `.importlinter` `tcb-isolation` targets and CI `TCB_PATHS` from `src/sagiha/…` to `src/aether/…` in the same change as the first `src/aether/` file; acceptance = path-constant drift test demonstrably fails on the old selection. (D4)
2. **Task 2**: reconcile with ADR-0005 — either restrict to ports whose adapters land this sprint, or (recommended) pair each protocol with a mock adapter + conformance test in the same change, under the amended ADR-0005 (below). (D3)
3. **Task 3 gate**: replace "zero network errors" with "resolves 100% of base commits for the pinned floor-manifest task set; cache content-addressed and offline-replayable." (audit §1.3)
4. **DoD item 4**: fix `--max 54000` → the real ceiling (15,000 unless deliberately raised; if raised, record why in `docs/README.md`). (D6)
5. **Add**: B4 typed `GateReport` tri-state as a Sprint-01/02 domain task — it is a pure domain type and a precondition of the A/A floor. (D2)

### `docs/agile/roadmap.md`
6. **Re-order the DAG**: `B4 → A/A floor` (B4 precedes the floor, not M2). B3: floor may precede it only with the B3 canary executed in the floor environment first; encode that as a note on the edge. (D2, refinement §1.2a–b)
7. Fix matrix row "B2 depends on B1" (mermaid is right; they are independent). (D20)
8. Split M2's tripwire: M2-eng (5d) and M2-abl (sized after the floor reveals per-task wall-clock). (refinement §1.2e)

### `docs/agile/milestones.md`
9. **M0**: add Exit Gate 0 = TCB path migration landed and negatively tested. (D4)
10. **M1a Gate 3**: re-scope to the boundaries the skeleton actually needs (ModelProvider, Workspace/WorktreeManager, Evaluator, ToolRegistry) with the rest entering per ADR-0005 as adapters land — or fund the missing adapters (PR-1 item 12). (D15)
11. **M2**: add Exit Gate 4 = "repair loop v1 (bounded `evaluate→repair→apply` iteration) enabled; repair-on vs repair-off ablation clears the floor." Make it the *first* capability ablation, before the generated-context and Architect/Editor ablations. (D7)

### `docs/agile/backlog.md`
12. **Add missing tasks** (D15, D16):
    - TASK-000: TCB path migration (above).
    - TASK-005: conformance meta-suite harness (one parametrized suite, N adapters — I4's enforcement mechanism, currently unfunded).
    - TASK-006: mock adapter set + record/replay cassettes (mandated by the Phase 0 context brief's Tier-4 list; absent from the backlog).
    - TASK-013: B4 typed instrument-error/`GateReport` (pulled forward).
    - TASK-023: repair node + bounded-iteration construct.
    - TASK-024: compaction v1 (context-overflow gate: a task exceeding the window completes via compaction on a pinned long-task fixture).
    - TASK-033: Best-of-N cache sequencing (ADR-0010 consequence, currently task-less).
    - TASK-034: `ResourceGovernor` reserve/commit/release (spec §5's budget triple, currently task-less).
    - TASK-014: task-manifest tooling + per-task bidirectional canary (gold patch passes / empty patch fails), exclusion list published. (refinement §2.2)
    - TASK-015: comparative-lift rig (`HarnessUnderTest` runner seam; OpenHands as first external arm). (refinement §2.5)
13. **Split TASK-030** into TASK-030a (shell-AST classifier, `kernel/`) and TASK-030b (TaintGate, `agency/context/`, per new ADR-0015) — different mechanisms, different layers. (D16)

---

## PR-2 — Normative amendments

### `docs/spec.md`
14. **§3**: publish the full import lattice including `workflow/`, `measurement/`, `evolution/`, `engine.py`, `composition.py` (proposal: `engine > (agency, workflow) > kernel > adapters > ports > domain`; `evolution` imports ≤ `ports` and is imported by nothing; `measurement` reachable from kernel-side only), and state that the import-linter contracts encode the whole lattice. (D9)
15. **§4**: TCB port residency rule — concrete implementations of TCB ports (`PolicyEngine`, `Evaluator`) live inside TCB paths (`kernel/`, `measurement/`), never `adapters/`; import contracts select them there. (D8)
16. **§5/§2**: add I11 (TaintGate) as a real invariant with enforcement (pinned injection-corpus red-team gate: zero capability grants from untrusted spans), replacing the current single sentence. Point at ADR-0015. (D16)
17. **§9**: add the predecessor-code clause: repository-internal predecessor code may be ported verbatim when its claimed properties verify line-by-line, provenance noted in the module docstring. (D18)
18. Add a one-paragraph **port versioning rule**: protocols additive-only within a minor version; breaking change = new protocol name entering under ADR-0005. (audit §2)
19. Fix all `00/` links (see PR-3 item 27 for the directory decision).

### `docs/measurement.md`
20. **§3**: incorporate ADR-0003 rev.2 — derived N with pre-registered discordance assumption and 80% power at the minimal effect of interest; tiered N (50 smoke / ~150 admission / ~300 publication) or group-sequential with α-spending; pass-aggregation rule (primary = pass@1, first seeded pass; extra passes = flakiness estimate only); machine-declared gate family committed to TCB before any arm runs. (D1, D14, refinement §2.4)
21. **§2 B1**: re-scope to manifest-driven repo cache per suite (Verified's 12 repos ≠ Pro's set; enumerate from pinned manifests, verified at pin time). (D12)
22. **§2 B2**: reword "Resolved" → "Endpoint available (B2a resolved); adapter + conformance gate (B2b) open." (D13)
23. **§4**: pin the lift baseline (single completion, official inference template, no execution feedback, pinned temperature/seed/model version; template hash recorded). Either add a Terminal-Bench instrument note or mark its target "aspirational — no instrument yet; not a gate." Add the split discipline (DEV/HOLDOUT/SEALED) and contamination controls (perturbed-task indicator; task-validity canary with published exclusions). (D12, refinement §2.1–2.3)
24. **§6**: add "the task manifest and split assignment are TCB artifacts."
25. Note that the I10 cache metric = harness-side prefix stability over fixed replay (provider-reported hit rate secondary), since `cache_control` semantics are provider-specific and the B2 endpoint may expose none. (D10)

### `docs/decisions/`
26. Amendments:
    - **ADR-0001**: status → `Accepted (provisional)` to match the README's "three still open." (D17)
    - **ADR-0003 → rev.2**: power/tiered-N, pass-aggregation, declared-family mechanism, cost criterion = cost-per-resolved-task non-inferior within declared margin (default ≤ +20%). (D1, D11, D14)
    - **ADR-0005**: add the mock-adapter clause — a mock adapter + conformance test satisfies "first adapter" *only when* the first real adapter is named in the same ADR/task; otherwise the port waits. (D3)
    - **ADR-0010**: enumerate the five layers (proposal: L1 system/policy · L2 tool schemas · L3 repo brief [the ablated layer] · L4 task statement · L5 dialogue/trajectory) and reserve the "context prefix layout" diagram slot for it. (D10)
    - **ADR-0013**: add the bounded-iteration construct for the repair edge (a cycle with static unroll bound; expressible within the DAG model), and note the M1a pipeline gains `evaluate →(fail,k)→ repair → apply` at M1a+/M2. (D7)

---

## PR-3 — Hygiene

27. **`docs/00/` vs `docs/concepts/`**: pick one. Recommendation: rename the directory to `docs/00/` (matches every inbound link, the Phase 0 documents' self-references, and the numbered-tier convention) — 7+ links across README/vision/spec/measurement/decisions then need zero edits; only the audit-mission inventory alias changes. Extend the link checker to all of `docs/**.md` and demonstrate it fails on a planted dead link (a gate must be able to fail). Correct the `STATUS.md` link-gate row until then. (D5)
28. Create `docs/rationale/benchmarks/` (with `status: rationale` README) or repoint ADR-0001/roadmap/milestones publication paths to `docs/benchmarks/`. (D19)
29. **Budget governance**: close the "tag-yourself-exempt" channel — either milestone gate tables count against the normative budget, or introduce an enforced `status: operational` tag with its own ceiling. One paragraph in `docs/README.md` + the docs_budget script change. (D21)
30. `STATUS.md`: after PR-1, update the `tcb-check` row (no longer keyed to `src/sagiha/`) and the link-gate row.

---

## New ADRs to draft (outlines)

**ADR-0014 — Workflow topology is data.** Context: loop-engineering cadence and machine self-redesign both require topology variants without code PRs; ADR-0006's mutable surface excludes topology. Decision: topologies are hash-pinned declarative artifacts validated by a TCB schema/executor; static checks = socket type-compatibility, non-bypassable evaluator node, bounded iteration, declared fan-out; topologies join the ADR-0006 mutable surface, admitted only via ADR-0003 rev.2. Consequences: M1a skeleton is the first data topology (zero momentum cost); rollback = pin change. Reversal: ADR-0013's existing escape hatch extends — if unearned at M2, collapse to sequential pipeline. (Full rationale: [`proposal_harness_evolution.md`](./proposal_harness_evolution.md) §2.)

**ADR-0015 — TaintGate provenance model.** Context: pillar-3 injection defense currently one sentence. Decision: every context span carries a provenance label (`trusted-system`, `operator`, `agent`, `untrusted-external`, `untrusted-derived`); propagation is deterministic (outputs computed over untrusted spans are `untrusted-derived`); binding rule: untrusted/derived spans can never satisfy a policy predicate that grants or widens capability. Enforcement: pinned injection corpus in CI, gate = zero grants; corpus is TCB. Reversal: none on the binding rule; corpus contents revisable with audit trail.

**ADR-0016 — MCP integration trust model** *(decide now, build at growth tier)*. Decision: MCP lands as one `ToolRegistry` adapter; tool catalogs snapshotted at composition (preserves I6); MCP outputs are `untrusted-external` (ADR-0015); per-tool capability grants through the existing choke point. Entry per ADR-0005: with its first adapter, not before.

**ADR-0017 — Sub-agent capability attenuation** *(decide now, build at M3+)*. Decision: a sub-agent is a workflow subgraph with a scoped context and a capability set strictly ⊆ its parent's; budgets sub-divide through reserve/commit/release; `Orchestrator` remains a non-port. Reversal: if subgraph scoping proves insufficient for genuinely heterogeneous agents, revisit as a port under ADR-0005.

---

## What to remove

- The **Terminal-Bench committed target** as a gate (keep as aspiration) until an instrument exists — currently a number never measured on your instruments functioning as a commitment, against `spec.md` §9's own rule. (D12)
- The `--max 54000` figure. (D6)
- The "12 upstream repositories" hard-coding in B1's framing. (D12)
- The ambiguity "≥ 2 passes per arm" as currently worded — replaced by the aggregation rule. (D14)

## What explicitly *not* to change

- The lift-first doctrine, the A/A-floor gate on publication, tri-state gates, stubs-raise, reversal conditions, gate-driven scheduling, Python-first-with-triggers, no-LSP, sandbox-is-the-perimeter, IP-is-packaging. These survived adversarial review intact; they are the tree's assets. The audit's severity is a compliment to the standard the documents set for themselves — they are being held to it.
