---
status: rationale
updated: 2026-08-07
scope: docs/ (excluding docs/_archive) — documentation, governance and plan audit
---

> [!NOTE]
> **Remediation landed 2026-08-07.** Acted on: the dangling `docs/rationale/benchmarks/` paths
> (§5, including ADR-0002's reversal condition), the link gate itself, the stale gate claims in
> `STATUS.md` (§3), the I10 gap and the lattice statement in `PHASE-0-LOCK.md` (§4 D3/D7), the
> ADR counts and stale `development/` references in `README.md`, and the six duplicate task ids
> plus the two wrong task descriptions in `backlog.md` (§6.2 P1/P2/P3).
>
> **`docs/overview/` was quarantined, not deleted** — the owner chose that over §2's
> recommendation. It is now `status: historical` + `retrieval: excluded` with a banner saying
> what it is; `TASK-084` decides whether it is deleted or generated.
>
> A **fifteenth** dangling path was found while fixing the others and is not in §5:
> `gen_aether_event_catalog.py` still wrote to `docs/development/generated/`, so the
> event-catalog gate was **red while `STATUS.md` reported it green** — a second instance of §3's
> finding, and the reason `TASK-085` exists.
>
> **This report is left as written**, for the same reason as Part 1.

# AETHER — Tech Lead Audit v3.2.0 · Part 2: Documentation, Governance & Plan

**Scope**: `docs/` excluding `docs/_archive/` (legacy, `retrieval: excluded`, excluded by
instruction). 63 documents, 113,410 words, of which 11,776 count against the normative budget.
**Part 1** (`aether_tech_lead_review_v320.md`) is the code audit; findings are cross-referenced
as `F1`…`F18`.

---

## 1. Verdict on the documentation

**This is the best-governed documentation tree I have audited on a project this size, and it has
one structural failure that undoes a measurable part of that work.**

The tree does things almost nobody does:

- It holds itself to **mechanical gates** — a 15,000-word normative ceiling, a `status:` taxonomy
  where untagged fails, a link checker, an event-catalog drift check — and it ships
  `tests/unit/test_docs_gates.py`, which plants a dead link and an untagged file to prove the
  gates can go red. A gate that cannot fail is not a gate; this tree knows that and acts on it.
- **`STATUS.md` and `PHASE-0-LOCK.md` §4 are more honest than most post-mortems.** "Marked ✅
  with unmet exit criteria," "vacuous contract target," "grep returns nothing" — these are
  written by the team about its own work, unprompted.
- **Every fact has a declared owner** (`README.md` §"Who owns which fact"), and the rule
  *"if you find the same thing stated in two places, the second one is the bug"* is stated as
  binding.
- **ADRs carry reversal conditions.** 21 of them. This is the discipline the tree is proudest of
  and it earns it.

The structural failure is that a **seventh top-level folder, `docs/overview/`, was added in
violation of the tree's own most important rule**, and it is the source of every dead link the
gate now reports. §2.

---

## 2. `docs/overview/` — the governance breach

`README.md` states the shape as **six folders, one purpose each**:

```
docs/
├── *.md              WHAT IS TRUE
├── decisions/        WHAT WAS DECIDED
├── architecture/     HOW THE SYSTEM WORKS
├── agile/            WHAT WE ARE DOING
├── benchmarks/       EVIDENCE
├── concepts/         HISTORY
└── proposals/        UNDECIDED
```

`docs/overview/` is not in that list, is not in the "Who owns which fact" table, and is not
mentioned anywhere in `README.md`. It contains six files totalling **~8,500 words** whose own
headers describe them as re-renderings of documents that already exist:

| File | Declares itself a restatement of |
| :--- | :--- |
| `full_documentation_01_core_architecture_and_invariants.md` | `spec.md`, `vision.md`, `STATUS.md`, `README.md`, four `development/` docs |
| `full_documentation_02_adr_decisions_and_governance.md` | `decisions/README.md` and ADRs 0001–0018 |
| `full_documentation_03_abstraction_and_composition_proposal.md` | seven files under `docs/fixes/` and `docs/future_improvements/` |
| `full_documentation_04_agile_roadmap_backlog_and_milestones.md` | `roadmap.md`, `backlog.md`, `milestones.md`, all sprint files |
| `full_documentation_05_measurement_benchmarks_and_statistics.md` | `measurement.md`, three `rationale/benchmarks/` files |
| `full_documentation_06_frontend_architecture_and_bridge.md` | the entire `docs_front/` tree |

This is a direct violation of the rule the tree names as its own: *"What is forbidden is stating
the same fact twice, because the second copy drifts and nobody knows which one is current."*

**And it has already drifted.** Three examples, all mechanically checkable:

1. `full_documentation_02`'s title says **"ADRs 0001–0018"**. There are 21 ADRs. It is missing
   0019–0021 — which `decisions/README.md` itself says *"resolve what the project is."* A reader
   who starts in `overview/` learns the project is a SWE-bench harness and never learns about the
   three horizons.
2. `full_documentation_03` cites eight source paths under `docs/fixes/` and
   `docs/future_improvements/`. **Neither directory exists.** `fixes/` was renamed `proposals/`;
   `README.md` records that rename as the reason the proposal-lifecycle rule was written.
3. `full_documentation_01` and `_05` cite `docs/development/` and `docs/rationale/benchmarks/`.
   Both were renamed (`development/ → architecture/`, `rationale/benchmarks/ → benchmarks/results/`)
   in the commit range this branch contains.

**All 13 non-archive dead links reported by `check_links.py` are inside `docs/overview/`.**
Remove the folder and the link gate goes green for the live tree.

> **Recommendation.** Delete `docs/overview/`. It is a fifth copy of facts that already have four
> authoritative homes, it is stale in three independently verifiable ways, and it is the sole
> cause of the tree's only red gate. If a single-file export is genuinely wanted for onboarding or
> diligence, generate it — the same way `architecture/generated/aether_event_catalog.md` is
> generated with a drift check — rather than maintaining it by hand.

---

## 3. Gate ledger — verified by running the gates

`STATUS.md`'s rule is that no gate is reported green without the command that produced it. I ran
them. Three of its claims no longer hold.

| Gate | `STATUS.md` claims | Actual (2026-08-07) | Assessment |
| :--- | :--- | :--- | :--- |
| `pytest tests/aether tests/conformance tests/integration` | Green — 314 passed, 4 skipped | **378 passed, 6 skipped** | Green. Count is stale, not wrong |
| `lint-imports` | Green — 9/9 contracts | **9 kept, 0 broken** | Green, but see §4 — five of the nine police `sagiha` |
| `docs_budget.py --max 15000` | Green | **11,776 / 15,000 — OK** | Green |
| **Relative links** | **"Green — was red with 10 dead links before this sprint … fixed"** | **RED — 109 dead links across 93 files; 13 outside `_archive`** | **Stale claim** |
| Event catalog drift | Green — 8 events | 8 events in `EVENT_TYPES` | Consistent |

`PHASE-0-LOCK.md` §3 says "384 tests"; `STATUS.md` says 314. Neither matches 378. These are
cosmetic, but the tree's own standard is that a pasted number is pasted from a run — and the link
gate is not cosmetic: it is reported green while red, which is the exact failure mode
`test_docs_gates.py` was written to prevent. The gate works; the claim about it was not re-run.

---

## 4. Normative drift — where the docs and the code disagree

The tree's rule is *"when a document and the code disagree, the document is the bug."* Applied
literally, these are bugs.

| # | Document | Claim | Code | Severity |
| :--- | :--- | :--- | :--- | :--- |
| **D1** | `spec.md` §5 | "Repository files, issue text, tool output, test output and web results are `untrusted-external` **at birth**. Propagation is deterministic and monotone" | Repo files → `AGENT` (`generate.py:109`), test output → `AGENT` (`repair.py:160`). **No propagation code exists**; `UNTRUSTED_DERIVED` is never assigned anywhere | **High** — see `F5`/`F10` |
| **D2** | `spec.md` §6 | The TCB includes "**workflow schema, validator and executor**" | `.importlinter` `aether-tcb-isolation` `source_modules` lists `kernel.policy`, `kernel.dispatch`, `measurement.{evaluator,manifest,statistics}` — **not** `workflow.validator` or `workflow.executor` | **Med** — `F11` |
| **D3** | `PHASE-0-LOCK.md` L1 | Locked lattice: `engine > workflow > agency > measurement > kernel > adapters > ports > domain` | `.importlinter` encodes `engine > (agency \| workflow) > measurement > …` — agency and workflow are **siblings**, which `repair.py:24-29` relies on. ADR-0018, which would make L1 true, is **`Proposed`**, not accepted | **Med** — the lock states a lattice that is not the one enforced |
| **D4** | `PHASE-0-LOCK.md` L1 | "Enforced by `.importlinter`, **9 contracts**, 0 broken" | 9 total: **4 AETHER + 5 `sagiha`**. The retired tree carries a majority of the count cited as evidence for the AETHER lattice | **Low** — misleading, not false |
| **D5** | `spec.md` §2 (I7) | Enforced by "`tests_unmodified` hard gate" | `grep -rn "tests_unmodified" src/aether/` → nothing | Recorded — `TASK-049`, `PHASE-0-LOCK` §4 |
| **D6** | `spec.md` §2 (I9) | "Type-level `rank()` / `admit()` separation" | No ranker, no type separation | Recorded — `TASK-067` |
| **D7** | `spec.md` §2 (I10) | "CI floor on byte-identical-prefix rate over a fixed replay" | No assembler, no breakpoints, no such CI job | **Med** — unlike D5/D6, I10 is **not** in `PHASE-0-LOCK` §4's gap table |
| **D8** | `spec.md` §3 | Lattice diagram shows `evolution/`, `agency/`, `tui/` | None of the three exist | Recorded for `evolution/`; `tui/` is `TASK-075`, unrecorded as a spec/code gap |
| **D9** | `measurement.md` §4.1 | Baseline uses "official SWE-bench inference template" | The template is formatted with `instance_id`, not a problem statement | **Critical — `F1`, unrecorded** |
| **D10** | `pricing.py` docstring + `engine.py:186-190` | "A real ceiling, not a comment" | The ceiling is never debited by spend | **High — `F3`**, and `TASK-044`'s description of the mechanism is itself wrong |

**D7 deserves a line of its own.** `PHASE-0-LOCK.md` §4 is explicitly titled *"Locked as known
gaps — recorded, not hidden"* and lists nine. I7, I9 and I11 are there. **I10 is not**, yet its
stated enforcement mechanism is as absent as I7's. Three of eleven invariants are enforced by
nothing and only two are on the register. The gap table's own promise — *"none may be quietly
rediscovered as a surprise"* — is not met for I10.

---

## 5. Broken references the link gate cannot see

`check_links.py` is deliberately narrow: it resolves **markdown links** only. A file path written
in backticks is invisible to it. Both renames in this branch left backtick references behind, and
two of them are in binding documents:

| Location | Dangling path | Why it matters |
| :--- | :--- | :--- |
| `decisions/0002-no-number-before-the-floor.md:26` | `docs/rationale/benchmarks/noise-floor.md` | **This is ADR-0002's reversal condition.** The one decision in the tree whose stated reversal conditions are "none" identifies the file that unblocks publication — and names a path that does not exist. The real file is `benchmarks/results/noise-floor.md` |
| `decisions/0001-python-first-compiled-on-trigger.md:57` | `docs/rationale/benchmarks/` | ADR-0001's F1 fork trigger points at a missing directory |
| `PHASE-0-LOCK.md:118` | `rationale/benchmarks/noise-floor.md` | **Phase 1's exit condition** |
| `agile/milestones.md:60` | `docs/rationale/benchmarks/` (link text) → `../benchmarks/results/README.md` (target) | Text and target disagree; the gate passes because it only checks the target |
| `agile/milestones.md:11` | link text `../README.md` → target `../benchmarks/results/README.md` | Same class: mislabelled but resolvable, so invisible to the gate |
| `agile/sprints/sprint-03.md:59`, `sprint-04.md:71`, `sprint-04-dev-prompt.md:38,544,611`, `sprints/README.md:52` | `docs/rationale/benchmarks/…` | Sprint 4 is the sprint that takes the floor, and its dev prompt tells the developer to write the result to a directory that does not exist |
| `backlog.md` `TASK-072`/`073`/`074` target files | `docs/rationale/benchmarks/*.md` | Three M4 tasks' declared output paths |

**This is a gate-coverage gap, not just a set of typos.** The tree's doctrine is that a rule
enforced by discipline is a wish. Paths in backticks are currently enforced by discipline. A
ten-line extension to `check_links.py` — resolve backticked strings that look like repo paths
(`^(docs|src|scripts|tests|benchmarks|workflows)/…`) and fail on misses — would have caught all
fourteen, including the two inside ADRs. It is the same argument
`tests/unit/test_path_constant_drift.py` already makes for import contracts.

---

## 6. Plan audit — `agile/`

### 6.1 What is right

The backlog is the strongest planning artifact in the tree. It **already contains** the
diagnoses for eight of Part 1's eighteen findings, each with target files, line numbers,
normative references and a falsifiable exit criterion — `TASK-042` through `TASK-046`,
`TASK-048`, `TASK-059`, `TASK-062`. Several are written more precisely than I would have written
them. `TASK-062`'s "why it matters" paragraph — that a hung tool call becomes `NONE`, `NONE` is
excluded from the denominator, and therefore repositories that prompt on stdin are dropped
*non-randomly* — is a genuinely subtle instrument-validity argument and it is correct.

The gate structure in `milestones.md` is falsifiable throughout: every exit gate names a test,
and the "negative test required" clause appears on the ones that need it.

### 6.2 Defects in the plan

| # | Location | Defect |
| :--- | :--- | :--- |
| **P1** | `backlog.md` | **Six task IDs are defined twice**: `TASK-071`, `072`, `073`, `074`, `075`, `015b` each appear as two `###` headings with different bodies (Epic 7 vs the M4 section). `TASK-072`'s two definitions have different target files. An ID that resolves to two tasks cannot be tracked |
| **P2** | `backlog.md` `TASK-044` | Description states the failure mechanism incorrectly — "an overrun is detected on the next reserve." It is detected on no reserve. Fixing what the task describes leaves the ceiling unenforceable (`F3`) |
| **P3** | `backlog.md` `TASK-049` | Deletion scope is `edit_format.py:198-202`. The `len(py_files) == 1` inferrer at `:193-196` guesses a write target the same way and is not in scope (`F7`) |
| **P4** | `roadmap.md` M1a++R | The gate blocking the floor funds I7 and test-source injection. It does not fund `F1` (no problem statement) or `F2` (provider error scored as failure), both of which corrupt the floor by the same argument the roadmap uses for B4 |
| **P5** | `milestones.md` | Exit gates stop at M1a++R. **M1b, M2, M3, M4 and M5 have no gate tables** — they exist in `roadmap.md` as tripwire rows only. Per ADR-0009 *"exit gates decide when a phase completes"*, five of eight milestones currently cannot complete |
| **P6** | `PHASE-0-LOCK.md` §5 | "**19 ADRs ratified**. ADR-0018 is Proposed" — there are 21, of which 20 are Accepted. `README.md` says 19 in one row and 22 in the folder diagram. `decisions/README.md` is correct; the two summaries are not |
| **P7** | `roadmap.md` / `milestones.md` | Neither names an **M6**, but `architecture/README.md`'s horizon map assigns `self_improvement.md` to **M6**, and `PHASE-0-LOCK.md` §4 says the mission gap was "closed by ADR-0019 and M5/M6." M6 exists in three documents and in no plan |
| **P8** | `backlog.md` `TASK-015` | Marked ✅ with the AETHER arm absent, not only the OpenHands arm. `PHASE-0-LOCK` §4 records the OpenHands omission; the missing harness arm means the rig cannot compute lift at all (`F8`) |

### 6.3 `proposals/` lifecycle

The rule is: *"a proposal older than two sprints is either ratified (delete it) or rejected
(delete it). `proposals/` holds only what is still undecided."* Three proposals are present:

| Proposal | State |
| :--- | :--- |
| `proposal_sota_gap_analysis.md` | Substantially **ratified** — its §2 localization finding is `TASK-064`, funded and scheduled. Should be deleted per the rule |
| `proposal_workflows_hybrids_improvements.md` | **Ratified** — it is cited as the source of Epic 6 (`TASK-042`–`046`), which exists in the backlog. Should be deleted |
| `proposal_competitors_execution_mechanics_evaluation.md` | Partly ratified (`TASK-062`, `TASK-035`'s background-effect refusal both cite it). Genuinely undecided remainder is small |

All three are dated within two sprints, so none is yet in breach — but two have already been
converted into ADR-adjacent backlog epics, which is the trigger the rule names. Worth noting that
`proposal_sota_gap_analysis.md` §0 is excellent work: it catches two *other* investigations citing
`src/openhands` and `src/claude_refs` for architecture they never read. That discipline — "read
from source is a fact, read from a competitor's analysis doc is a hypothesis" — is exactly right
and is the same discipline this report's §0 in Part 1 applies to its own brief.

---

## 7. Consolidated recommendations

Ordered by (instrument integrity × cost to fix later).

### Before the A/A floor — non-negotiable

1. **`TASK-076`** — problem statement becomes manifest data (`F1`, `D9`). Without it the floor
   measures a harness that was never told what to do.
2. **`TASK-077`** — terminal `StopReason` maps to `GateStatus.NONE` (`F2`). Without it a
   rate-limited provider depresses one arm's resolve rate invisibly.
3. **`TASK-078`** — the ledger debits actual spend (`F3`). A publication run on a paid provider
   with a cap that cannot fire is an unbounded spend authorisation.
4. **Re-run the link gate and correct `STATUS.md`.** It reports green while red. Everything else
   in that file is trustworthy, which is exactly why one false green is expensive.

### Documentation — one deletion, two corrections

5. **Delete `docs/overview/`.** Seventh folder, fifth copy, stale in three ways, and the sole
   source of every live dead link.
6. **Fix the fourteen backticked `docs/rationale/benchmarks/` references**, starting with
   ADR-0002's reversal condition and `PHASE-0-LOCK.md` §7's Phase 1 exit condition. Then extend
   `check_links.py` to see backticked repo paths, so the class cannot recur.
7. **Add I10 to `PHASE-0-LOCK.md` §4's gap table.** Three invariants are enforced by nothing; two
   are on the register.

### Plan hygiene

8. **De-duplicate the six repeated task IDs** (`P1`).
9. **Correct `TASK-044`'s and `TASK-049`'s stated mechanisms** (`P2`, `P3`) — a task whose
   description names the wrong cause produces a fix that does not fix it.
10. **Write exit-gate tables for M1b–M5** (`P5`). Under ADR-0009 a milestone without gates cannot
    complete, and five of eight are in that state.
11. **Reconcile the lattice statement** (`D3`): either ratify ADR-0018 and change `.importlinter`,
    or amend `PHASE-0-LOCK.md` L1 to state the lattice that is actually enforced. A lock record
    that states an unenforced constraint is the failure mode the lock exists to prevent.

---

## 8. Closing assessment

The strongest thing about this project is not any component. It is that the team wrote
`measurement.md` §1 — *"AETHER has never produced a valid benchmark number. Not a low one —
none"* — and then built four sprints of instrument before touching capability. Almost nobody
does that, and it is the reason the findings in Part 1 are fixable in about eight days instead of
being discovered after a publication run.

The failure mode this project must guard against is **not** under-engineering. It is the one
`docs/overview/` demonstrates: producing a second, plausible-looking copy of something that
already has an authoritative home, letting it drift, and then having two answers to the same
question. That is the documentation form of exactly what `F3` is in code — a ledger that reports
spend in one dictionary and enforces it against another.

Every rule needed to prevent both is already written down in this tree. The gap is enforcement
coverage, not doctrine.

---

*No code or existing documentation was modified in producing this report. Gate results in §3 are
from commands run against the working tree on 2026-08-07; the commands are named so they can be
re-run.*
