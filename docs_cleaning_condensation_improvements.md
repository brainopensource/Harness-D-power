---
status: rationale
updated: 2026-08-07
---

# Docs — Cleaning, Condensation and Context Engineering

**Scope.** Every `.md` under `docs/` except `_archive/` (being deleted) and `overview/` (in
progress). That is **78 files · 12,863 lines · 121,267 words · ~162k tokens** — more than the
entire `src/aether/` tree, which is 6,320 lines of Python.

**Why this matters beyond tidiness.** A developer opening Sprint 4 cannot read 162k tokens of
documentation, and an agent working in this repo cannot fit it in context alongside the code.
The question is not "which docs are good" — most are — but **which docs must be in context for
the next two sprints**, and what the rest costs to keep.

---

## 0. Correction, stated first

**`scripts/docs_budget.py` run without arguments cannot fail.** `main()` does
`if args.max is None: return 0` **before any check**, so the no-argument invocation prints the
full report — including its own list of files with undeclared `status:` — and exits 0 anyway.

I used that invocation repeatedly in this session and reported the docs budget as green. It
is not. CI invokes it correctly (`.github/workflows/ci.yml:67` →
`docs_budget.py --max 15000`), and run that way it **exits 1** on **11 files**:

```
fixes/proposal_workflows_S3-5_meta.md        (status: proposal — not in the taxonomy)
workflows/README.md                          (untagged)
workflows/architecture.md                    (untagged)
workflows/high_level_project.md              (untagged)
workflows/inner_loop.md                      (untagged)
workflows/main_features.md                   (untagged)
workflows/outer_loop.md                      (untagged)
overview/full_documentation_06_frontend…md   (untagged — out of scope here)
_archive/competitors_research/… ×3           (untagged — being deleted)
```

Two consequences worth separating:

1. **The whole `workflows/` directory is untagged**, so its 3,048 words are invisible to the
   word budget. `docs/README.md`'s own rule says why that matters: *"an untagged file is
   invisible to the budget, which would make 'no frontmatter' a way to add normative words for
   free."*
2. **The script has a mode that reports failures and exits 0.** That is the defect class
   `measurement.md` §5 names — *a gate that cannot fail is not a gate* — living inside the
   docs gate itself. Anyone verifying by hand will reach for the bare invocation.

**Fix (5 minutes, do it in Sprint 4 Task 3):** make `--max` default to `15000` instead of
`None`, so the bare invocation is the CI invocation. Keep an explicit `--max 0` or
`--report-only` if a report-without-gate mode is genuinely wanted.

---

## 1. Mandatory — must stay, and stay current

These are the working set for Sprints 4 and 5. **~57k tokens**, which is the number to design
around.

### Tier 1 — binding contracts (never condense)

| File | Words | Why mandatory |
| :--- | ---: | :--- |
| `spec.md` | 2,083 | The only statement of what is true. I1–I11, the lattice, port rules, TCB residency |
| `measurement.md` | 2,148 | The instrument protocol. §4.1 and §6 are Sprint 4's acceptance criteria |
| `agile/roadmap.md` | 1,257 | `normative`; its dependency edges bind |
| `agile/milestones.md` | 1,714 | `normative`; gates decide when a phase ends |
| `decisions/` (19 ADRs) | 10,911 | Every decision with its reversal condition. Budget-exempt by convention, and correctly so — each ADR *replaces* long-form derivation elsewhere |
| `STATUS.md` | ~1,600 | The only honest account of what is built. Read before believing any other doc |

**Total: ~19,700 words / ~26k tokens.** This tier is already lean. `spec.md` at 2,083 words
covering eleven invariants and a nine-port lattice is genuinely dense — do not touch it.

### Tier 2 — the active plan

| File | Words | Why mandatory |
| :--- | ---: | :--- |
| `agile/backlog.md` | 13,793 | 71 tasks with exit criteria. **The largest single file in the tree** — see §2.1 |
| `agile/sprints/sprint-04.md` + `-dev-prompt.md` | 6,073 | The sprint being executed |
| `agile/sprints/sprint-05.md` | ~1,900 | The sprint after |
| `agile/coverage_audit.md` | 2,142 | The six gaps and the tasks that close them |
| `rationale/benchmarks/noise-floor.md` | ~400 | Sprint 4's deliverable lands here |

### Tier 3 — design sources, read per-task not cover-to-cover

| File | Words | Read when |
| :--- | ---: | :--- |
| `fixes/proposal_abstraction_and_harness_composition.md` | 7,525 | Sprint 5 — the design of record for `agency/` |
| `fixes/proposal_sota_gap_analysis.md` | 2,766 | Sprint 6 planning — localization, ranking, edit formats |
| `fixes/proposal_workflows_hybrids_improvements.md` | 3,169 | M4 routing work |
| `development/schemas_and_contracts.md` | 2,268 | When touching a schema |
| `development/core_skeletons_and_protocols.md` | 2,581 | Superseded by code where they disagree — **the code wins** |

---

## 2. Condense — real duplication, ranked by tokens recovered

### 2.1 `agile/backlog.md` — 13,793 words, and roughly 40% is restatement

Each task appears **twice**: once as a `### TASK-0xx` entry with description, target files,
normative specs and exit criteria, and again as a row in the *Backend Roadmap Complexity*
tables with a "Technical Complexity & Rationale" paragraph that re-derives the same reasoning
in prose.

The complexity tables carry two things the task entries do not: the 0–5 score and the *why
this task lands where it does* judgement. Both are worth keeping. The 60–100-word rationale
paragraphs are not — they restate the exit criteria in a different voice.

**Proposal:** keep the score and the one-line "The Developer — why" column; delete the long
rationale column, which is the duplicated half. **Recovers ~4,000 words (~5k tokens) from the
single most-read file in the tree.**

### 2.2 `docs/workflows/` (3,048 w) vs `development/system_workflows_and_diagrams.md` (1,485 w)

Two independent homes for Mermaid diagrams of the same system. `workflows/` has six untagged
files; `system_workflows_and_diagrams.md` is an **orphan** — nothing links to it.

Both also duplicate content that is now authoritative elsewhere: `workflows/inner_loop.md` and
`outer_loop.md` describe loops that
`fixes/proposal_abstraction_and_harness_composition.md` §2 defines precisely and correctly,
and `workflows/architecture.md` overlaps `vision.md` §3 and `spec.md` §3.

**Proposal:** merge into **one** `docs/architecture_diagrams.md`, `status: rationale`, keeping
only diagrams that are not derivable from `spec.md` §3 or `vision.md` §3. Delete
`development/system_workflows_and_diagrams.md`. **Recovers ~2,500 words and closes 6 of the 11
gate failures in §0.**

### 2.3 `fixes/` — 13 files, 30,624 words, the largest folder

`docs/README.md` still describes it as *"The Phase 0 lock audit (D1–D21) and its execution
roadmap"* — accurate for one file when it was written, and now the folder is a quarter of the
whole tree. Three groups:

**Superseded — fold into their successor:**

| File | Words | Successor |
| :--- | ---: | :--- |
| `proposal_architectural_abstraction_and_harness_engineering_gem.md` | 755 | Its own header says it defers all backend architecture to `proposal_abstraction_and_harness_composition.md`. Only §1.2 (React-Flow subgraph canvas) and §2.2 (JSON-RPC shapes) are unique — move those two sections in and delete the file |
| `proposal_workflows_S3-5_meta.md` | 656 | Superseded by `proposal_workflows_hybrids_improvements.md`, which was written explicitly to extend it and corrects its cost claims. Also the **one file with an invalid `status: proposal`** |
| `proposal_capability_extension_roadmap.md` | 2,360 | Overlaps `proposal_sota_gap_analysis.md` heavily (both cover memory, MCP, browsing, caching). **Orphan** — nothing links to it |

**Orphaned, zero inbound links:** `proposal_agile_benchmarkings_refinement.md` (2,129 w) —
its M4/M5 gate drafts are cited by `sprints/README.md` as *"not ratified as milestones"*, so
either promote those gates into `milestones.md` (which `coverage_audit.md` G4 already asks for)
or archive the file. Do not leave a document whose only content is unratified gates.

**Historical, retag not delete:** `proposal_architecture_audit.md`,
`proposal_improvements_and_fixes.md`, `proposal_harness_evolution.md`,
`implemented_sprint_3.5_complete_report.md`, `sprint-3.5-inner-loop-improvements.md`. These
record *why* decisions were made and are cited from live docs. They should carry
**`status: historical`** — the taxonomy's third value, currently used by **zero files** — which
signals "do not read for current truth" without deleting the trail.

**Recovers ~5,900 words** from the three superseded files, and correctly labels ~9,000 more.

### 2.4 `future_improvements/` (2 files, 2,673 w) — both orphaned

`aether_vs_kimi-cli.md` and `aether_vs_reasonix.md` are competitor comparisons written against
the *spec*, not against a code read. `fixes/proposal_competitors_execution_mechanics_evaluation.md`
does the same job from verified source, and its §0 documents that two of four such
investigations cited trees they had not read.

They also contain the claim shape `spec.md` §9 forbids — comparative assertions with no
comparative instrument (`TASK-015`'s OpenHands arm is the only admissible route).

**Proposal:** fold anything still useful into the verified evaluation doc, delete the folder.
**Recovers 2,673 words and removes a standing §9 hazard.**

### 2.5 `concepts/` (8 files, 15,624 w) — correct as-is, verify the flag

Phase 0 decision trail. Already `retrieval: excluded` on all eight, which is exactly right:
history that should not enter a working context. **No change** beyond confirming the flag is
honoured by whatever tooling consumes it.

---

## 3. Remove

| Target | Words | Reason |
| :--- | ---: | :--- |
| `docs/_archive/` | ~287k | Already slated. It is 70% of the tree by words and the reason `retrieval: excluded` exists |
| `development/system_workflows_and_diagrams.md` | 1,485 | Orphan; merged per §2.2 |
| `future_improvements/` | 2,673 | Orphan; superseded per §2.4 |
| `fixes/proposal_architectural_abstraction_…gem.md` | 755 | Two sections merged, rest superseded |
| `fixes/proposal_workflows_S3-5_meta.md` | 656 | Superseded; invalid status tag |
| `development/generated/aether_event_catalog.md` | 116 | **Do not delete — verify instead.** Generated with a CI drift check, and `gen_event_catalog.py --check` currently **exits 1** against an `_archive` path. Repoint it (Sprint 4 Task 3) or the generator outlives its target |

---

## 4. Structural improvements

### 4.1 `docs/README.md` is stale and is the entry point

It is `normative`, it is the first file anyone opens, and its index omits **`workflows/`,
`benchmarks/`, `rationale/`, `future_improvements/`** — four of eleven directories — while
describing `fixes/` as a single audit document. Fix the index; it is the cheapest correction
here and it has the highest read-count.

### 4.2 Make `status: historical` real

The taxonomy declares three values and **zero files use `historical`**. Everything that is
finished-and-superseded is tagged `rationale`, which means "reasoning behind current design"
and invites reading it as current. Applying `historical` to the five files in §2.3 makes the
distinction machine-checkable rather than tribal.

### 4.3 One `retrieval:` convention, documented

`retrieval: excluded` already exists on 13 non-archive files and is doing real work — it is the
project's context-engineering primitive and it is undocumented in `README.md`. Document it, and
extend it to a three-value field:

```yaml
retrieval: always     # Tier 1 — load in every session (spec, measurement, STATUS)
retrieval: on-demand  # Tier 2/3 — load when the task touches it
retrieval: excluded   # history, superseded, archive
```

That turns §1's tiering into metadata an agent or a script can act on, instead of prose in
this document.

### 4.4 A per-sprint reading manifest

`sprint-04-dev-prompt.md` §2 already does this by hand — four tables of *path · why · what to
take from it*, with the audit trail keyed per task so nobody reads six proposals to start Task
1. **That pattern is the fix, and it should be the template for every future sprint prompt.**
It is what makes a 162k-token tree usable from a ~40k-token working set.

---

## 5. Projected result

| | Files | Words | ~Tokens |
| :--- | ---: | ---: | ---: |
| Today (excl. `_archive`, `overview`) | 78 | 121,267 | ~162k |
| After §2 condensation and §3 removals | ~70 | ~103,000 | ~137k |
| **Tier 1 + Tier 2 working set** | **~20** | **~43,000** | **~57k** |
| Tier 1 alone (binding contracts) | 23 | ~19,700 | ~26k |

The headline is not the 15% reduction. It is that **the working set becomes explicit**: a
developer or an agent starting Sprint 4 loads ~57k tokens, not 162k, and knows which of the
remaining 105k to reach for and when.

---

## 6. Sequencing

| When | Do |
| :--- | :--- |
| **Sprint 4, Task 3** *(already scoped there)* | Fix `docs_budget.py`'s `--max` default (§0) · tag `workflows/` · fix the `proposal` status tag · repoint the event-catalog gate · fix `README.md`'s index (§4.1) |
| **Sprint 4, any time** | Delete `_archive/` · delete `future_improvements/` (§2.4) · apply `status: historical` (§4.2) |
| **Sprint 5, alongside the refactor** | Merge the diagram sets (§2.2) · fold the superseded `fixes/` proposals (§2.3) · trim `backlog.md`'s duplicated rationale column (§2.1) |
| **Before Sprint 6** | Document `retrieval:` (§4.3) · write `sprint-06-dev-prompt.md` from §4.4's template |

## 7. What this proposal does not claim

- **No document is claimed to be wrong.** Nearly all of this tree is accurate; the problem is
  volume and duplication, not error. The one exception is §0, which is a real gate defect.
- **The `_archive/` decision is not mine.** It was already made; this document only counts it.
- **`concepts/` is not over-documented.** 15,624 words of decision trail with
  `retrieval: excluded` is the correct handling of history, and `vision.md` §4 explains why
  that trail is the most valuable thing the prototype produced.
- **No token figure here is measured.** Token counts are `words × 4/3`, a standard English-prose
  approximation. They are for planning a context budget, not for a claim.
