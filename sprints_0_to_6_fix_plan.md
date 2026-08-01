---
status: rationale
updated: 2026-08-01
retrieval: excluded
---

# SAGIHA v2 — Sprints 0–6 Remediation Execution Plan

| Field | Value |
| :--- | :--- |
| **Document ID** | `sprints_0_to_6_fix_plan` |
| **Source of defects** | [`Harness_LLM_orchestrator_project_review.md`](Harness_LLM_orchestrator_project_review.md) §4, §7 |
| **Branch** | `refactor_aether_v2` (do **not** branch further; do **not** push) |
| **Baseline HEAD** | `eae4c22` |
| **Created** | 2026-08-01 |
| **Status** | ☐ Not started |

> **Rules of engagement — read once, then never ask.**
> 1. **Every decision is already made** in §2. Implementers do not deliberate, do not open
>    alternatives, and do not ask questions. If a situation genuinely falls outside §2, apply
>    §2.D0 (the default-resolution rule) and record it in §5.
> 2. **One commit per wave**, at the end of that wave, only after its exit gate is green.
>    **Never `git push`.** Pushing is a separate, later, human decision.
> 3. **Mark progress in this file** — tick the checkbox on each step as it lands, and fill the
>    wave's row in §4 (Execution Log) with the real commit SHA and the real gate numbers.
> 4. **Numbers come from commands, never from memory.** This is the C-2 defect; do not repeat it.
> 5. **Waves are strictly ordered.** W2 depends on W1's helper, W5 depends on every prior wave
>    being green. Do not reorder. Waves 6–9 may be reordered among themselves.

---

# §1 — Scope

## 1.1 In scope

All Critical, Major, and Minor defects in `Harness_LLM_orchestrator_project_review.md` §4, plus
the `scripts/verify.sh` harness that makes the STATUS table honest.

| Wave | Theme | Defects closed | Priority |
| :--- | :--- | :--- | :--- |
| **W0** | Baseline capture + `verify.sh` | *(enabler)* | P0 |
| **W1** | Retrieval honesty | **C-1** | P0 |
| **W2** | Port conformance & type check | **C-3**, **C-R1**, **m-4** | P0 |
| **W3** | Lint & format green | **m-14**, ruff, format | P0 |
| **W4** | Docs governance green | **C-2b**, **C-3d**, **m-12** | P0 |
| **W5** | SSOT truth + ADRs | **C-2**, **M-6**, **M-7**, **m-8**, **m-9**, **m-13** | P0 |
| — | — | **↑ P0 COMPLETE — tag-ready ↑** | — |
| **W6** | Retrieval quality bundle | **m-3**, **M-3**, **M-5**, **M-4** | P1 |
| **W7** | Quality / completeness | **M-8**, **m-1**, **m-2**, **m-5**, **m-7** | P2 |
| **W8** | Perimeter CI | **M-2** | P1 |
| **W9** | Benchmark suite & ablations | **M-1** | P1 |

## 1.2 Out of scope — do not touch

v2-S7 (Story-DAG, MCP client, streaming TUI, OTel), Conductor C0+, dense retrieval (ADR-0014),
AOI models, RHI Tier C, A2A. Also out of scope: every item in the review's
**"NOT DEFECTS — do not fix these into overclaims"** table. In particular, do **not** "fix"
`coverage_not_decreased=None`, do **not** enable `search`/`retrieval` by default, and do **not**
make `MCP.list_tools()` raise.

---

# §2 — Decisions Register

Every ambiguity the review left open is resolved here, imperatively. Rationale is recorded so the
decision can be audited later, not so it can be relitigated now.

### D0 — Default-resolution rule (applies to anything not covered below)

> When a choice arises that §2 does not cover, take the option that **(a)** makes an instrument
> more honest, **(b)** deletes surface rather than adding it, and **(c)** is smallest. Record it
> in §5 with one sentence of rationale. Never expand scope to resolve an ambiguity.

---

### D1 — `Indexer` contract: rename `neighbors(path)` → `search(query)`, and **remove** `neighbors` from the port

**Decision.** `ports/indexer.py` becomes exactly three methods:

```python
class Indexer(Protocol):
    async def find_symbols(self, query: str, limit: int = 20) -> list[Symbol]: ...
    async def get_skeleton(self, path: str) -> str: ...
    async def search(self, query: str, limit: int = 20) -> list[RetrievalHit]: ...
```

`neighbors` is **deleted from the port entirely**, not kept as a graph-expansion method.

**Rationale.** The review offered option A (rename the port parameter) and option B (split the
APIs, keeping `neighbors(path)` for graph expansion). Both were incomplete. Verified facts:

- The only production caller is `composition.py:131`, which passes a **goal string** — so the
  operation genuinely is search, and the port's `path` parameter was always the lie.
- Graph expansion **already exists** as `CodeGraph.impacted_by(file_path, hops)` with a working
  Tree-sitter adapter. A second `neighbors(path)` on `Indexer` would duplicate it.
- **ADR-0023 (port-rent rule)** forbids contract surface with no adapter. Keeping
  `neighbors(path)` on the port with zero implementations creates unpaid rent on day one.

Option A was rejected because it preserves the semantic lie in the contract. Option B's second
half was rejected because it violates ADR-0023 and duplicates `CodeGraph`.

**Blast radius (verified):** 1 production call site (`composition.py:131`), 7 test call sites
(`tests/contracts/test_indexer_conformance.py` ×3, `tests/unit/test_fts5_indexer.py` ×3,
`tests/unit/test_index_service.py` ×2). Small and mechanical.

**Requires ADR-0026.**

---

### D2 — `max_chunk_tokens`: **delete the field**, do not implement splitting

**Decision.** Remove `RetrievalConfig.max_chunk_tokens` and every parameter threading it
(`composition.py` → `IndexService` → `analyze_python_tree` / `analyze_python_source` /
`chunk_python_source`). Replace with a single module-level constant in the new shared module:

```python
# src/sagiha/adapters/indexer/walk.py
MAX_CHUNK_TOKENS: Final = 1024   # fixed policy until an ablation justifies tuning (ADR-0027)
```

**Rationale.** The review said "implement splitting **or** delete the field." Deletion wins:

- Implementing statement-boundary splitting is a retrieval-quality change with **no way to
  measure whether it helps** — the suite does not exist (M-1). Shipping an unmeasured heuristic
  into the one subsystem that just produced a Critical defect is exactly backwards.
- Deletion is small, fully reversible, and immediately honest.
- It simultaneously fixes the second half of M-4 that the review flagged: `fts5.py:68` hardcodes
  `1024` independently, so the direct `reindex_file` path already ignored the config. One
  constant collapses both.

**Compatibility — verified safe.** `RetrievalConfig` uses `ConfigDict(frozen=True)` and does
**not** set `extra="forbid"`. Pydantic's default is `ignore`, so an existing `sagiha.toml` that
still carries `max_chunk_tokens` continues to load without error. No migration needed.

**Requires ADR-0027.**

---

### D3 — `adapters/search/sequential.py`: **delete the module and its export**

**Decision.** `git rm src/sagiha/adapters/search/sequential.py`; strip the import and `__all__`
entry from `adapters/search/__init__.py`.

**Rationale.** The review offered delete-or-raise. Delete wins: `BestOfNSearch` with
`n_candidates=1` already covers the sequential case (confirmed at `best_of_n.py:211`
`_propose_sequential`), so a `NotImplementedError` shell would be a pointer to code that already
exists — pure noise. Under the v2-S1 H3 doctrine, a module whose three methods return fabricated
branch IDs, `None`, and `branch_ids[0]` is a lying stub; the honest disposition of a lying stub
whose function is already implemented elsewhere is removal.

**Check before deleting:** if any test imports `SequentialCandidateSearch`, delete that test too —
it tests fabrications.

---

### D4 — `m-13` (empty `runtime/` and `aoi/` packages): **NO-OP — the audit finding was wrong**

**Decision.** Change nothing. Correct the record in §5.

**Rationale.** Re-verification during planning found that both packages **already carry exactly
the explanatory docstrings m-13 asked for**:

- `src/sagiha/runtime/__init__.py` — *"v2-S5 landed the rootless Podman perimeter in
  `sagiha.adapters.sandbox`. This package remains the CAR Runtime layer home … the Workspace
  adapter (`ContainerSandbox`) is the security boundary agents execute inside."*
- `src/sagiha/aoi/__init__.py` — *"Advisory co-processor models (shadow mode only). Deferred past
  v0.1."*

Furthermore, **deleting them would break the build**: `.importlinter` names `sagiha.runtime` in
three contracts (`agency-not-runtime`, `domain-is-pure`, `layers`) and `sagiha.aoi` in
`tcb-isolation`. Removing the packages would break 4 of 5 import contracts to fix a cosmetic
complaint. m-13 is withdrawn.

---

### D5 — `m-9` (TaintGate does not block `run_command`): **documentation only, zero code change**

**Decision.** Add the rationale to `docs/02-architecture/security-and-threat-model.md#t7`. Do
**not** implement the "tainted + autonomous ⇒ deny non-PURE `run_command`" tightening the review
floated as an option.

**Rationale.** The current behavior is deliberate and asserted in code
(`assert _TAINT_BLOCKED_TOOLS <= MUTATION_TOOLS`): gates must run `git` under taint or H1
regresses. Tightening the policy is a **security-behavior change** that alters which runs
complete; it needs a threat-model review and a canary suite, neither of which is in scope for a
remediation plan. The defect is that the tradeoff is undocumented. Document the tradeoff.

---

### D6 — `m-7` (export tool schemas): **config-driven reconstruction + explicit warning**, not a trajectory snapshot

**Decision.** In W7, make the export path build schemas through the same helper the registry uses
(`adapters/tools/builtins.py:245`, driven by the active `Config`) instead of the static
`BUILTIN_SCHEMAS` dict. When exporting a run whose tool set cannot be reconstructed with
certainty, emit `logger.warning` naming the run id — never silently emit a schema list the run did
not have.

**Rationale.** The review preferred storing a registry snapshot on the run. That is the right
long-term answer and the wrong thing to do now: it is a trajectory-schema change with a migration,
landing in a remediation wave, to serve an export path whose consumers do not yet exist. The
config-driven reconstruction is a two-line change that is correct for every run recorded under the
current config, and the warning makes the residual uncertainty **visible instead of silent** —
which is the actual honesty requirement. Record the snapshot approach as the S7 follow-up.

---

### D7 — `m-2` (init module discovery): strip `src/`, include non-package modules

**Decision.** In `outer_loop/init/generate.py::_discover_python_modules`: strip a leading `src/`
segment before dotting the path, and collect non-`__init__.py` modules that sit under a discovered
package root (not only top-level ones). Reuse the shared `SKIP_DIRS` from W6's `walk.py`.

**Rationale.** Verified that `rglob("*.py")` already finds packages at any depth — prior report
B's description was imprecise. The two real defects are the `src.sagiha.domain` naming artifact
and the `elif "/" not in rel` clause that drops submodules. Fix exactly those two.

---

### D8 — `m-12` (untagged docs): tag all 8 first, **then** make `docs_budget.py` fail on untagged

**Decision.** Two ordered steps inside W4. Tag assignments are fixed now, no deliberation:

| File | Assign |
| :--- | :--- |
| `implementation/refactor_sagiha_v2_guidelines.md` | `status: historical` |
| `implementation/sprints_tasks_order_deps_plan.md` | `status: historical` |
| `rationale/done/sprint_v2_s4_feedback.md` | `status: rationale` |
| `rationale/done/sprint_v2_s4_fixes.md` | `status: rationale` |
| `rationale/reference/LLM_models_benchmarkings_2026.md` | `status: rationale` |
| `rationale/reviews/prompt_sprint_review_v3.md` | `status: rationale` |
| `superpowers/plans/2026-07-31-v2-s6-retrieval-code-graph.md` | `status: historical` |
| `frontend/frontend_prompt_detailed_todo.md` | `status: rationale` |

All eight also get `retrieval: excluded`. **None is tagged `normative`** — every one is a plan,
a review, or a reference, and the two `implementation/` guides describe *how work was sequenced*,
which is history, not contract. Flipping the enforcement flag before tagging would leave the
build red for the duration of W4; tag first.

---

### D9 — `m-14` (lint scope): exclude **vendored trees only**; fix project files

**Decision.** Add to `[tool.ruff]` in `pyproject.toml`:

```toml
extend-exclude = [
    "aether_examples",
    "src/claude_code",
    "src/grok_build",
    "src/hermes_agent",
    "src/open_code",
]
```

`keep_alive.py` (4 errors) and `scripts/extract_gemini_share.py` (1 error) are **project files** —
fix their lint, do not exclude them. Do not delete `keep_alive.py`; it is staged in the working
tree and removing another author's file is not a lint fix.

**Rationale.** Mirrors the rationale already written for pyright at `pyproject.toml:63-69`
(vendored reference harnesses are third-party trees that drown the signal). Excluding project code
to make a gate green is the dishonest version of this fix and is forbidden.

---

### D10 — `C-2b` (docs budget): demote `implementation/contracts-to-code.md`

**Decision.** Retag `docs/implementation/contracts-to-code.md` from `status: normative` to
`status: rationale` + `retrieval: excluded`. Verified: 709 words → **15,183 − 709 = 14,474**, a
526-word margin under the 15,000 ceiling.

**Rationale.** It is implementation guidance ("contracts to code"), not a contract. Demotion beats
deletion because the content is useful; deletion of 183 words scattered across four normative
files would be arbitrary editing of documents nobody asked to change, and would leave a 0-word
margin that the next PR immediately breaks.

---

### D11 — `C-3d` (106 dead links): three mechanical batches, absolute URLs banned

**Decision.**
1. Repoint every `refactor_sagiha_v2_guidelines.md` reference to
   `docs/implementation/refactor_sagiha_v2_guidelines.md` (correct relative depth per file).
2. The ~4 references to the deleted `rationale/reviews/2026-07-29-foundation-review.md`: **delete
   the link, keep the prose**, since the target no longer exists and inventing a replacement
   target would be fabrication.
3. Convert every `file:///home/rock_dev/...` absolute URL to a repo-relative path. These are
   concentrated in `docs/frontend/frontend_prompt_detailed_todo.md` and
   `docs/rationale/done/sprint_v2_s4_feedback.md`.

**Standing rule added in W5:** absolute `file://` links are prohibited in `docs/`. They resolve
only on the authoring machine.

---

### D12 — `scripts/verify.sh` is the sole writer of the STATUS regression table

**Decision.** Build it in **W0**, before any fix, so every wave measures itself with the same
instrument. It runs all seven gates plus the port count, prints host facts (Podman present/absent,
Python version, git SHA), and exits non-zero if any gate fails. From W5 onward, the STATUS
regression table is populated **only** by copying its output.

**Rationale.** C-2 exists because a human typed gate results from memory. The fix for a
memory-transcription defect is to remove the human from the transcription path. Building it first
also means W1–W4 each get a one-command proof of progress.

---

### D13 — Contract changes require ADRs; ADRs are budget-exempt so this is free

**Decision.** Two new ADRs, written in W5:

- **ADR-0026 — `Indexer.search` replaces `Indexer.neighbors`** (D1). Records the port-rent
  reasoning and that graph expansion lives on `CodeGraph.impacted_by`.
- **ADR-0027 — Fixed chunk-size policy; `max_chunk_tokens` removed** (D2). Records that the knob
  was accepted-and-discarded, that deletion beats an unmeasurable heuristic, and names the
  trigger for revisiting: a populated benchmark suite (M-1).

**Rationale.** Both are changes to a published contract. `docs/08-decisions/` is exempt from the
word budget, so recording them costs nothing against C-2b. Next free number is **0026** (0025 is
the current highest).

---

### D14 — Commit discipline

**Decision.** One commit per wave, at the wave's end, only after its exit gate passes. Message
format:

```
fix(v2-s0-s6): <wave title> [W<n>]

<one line per defect closed, e.g.:>
- C-1: escape FTS5 queries; stop swallowing OperationalError
- ...

Gates after this wave: pytest <n> · pyright <n> · ruff <n> · format <n> ·
budget <n> · links <n> · catalog <ok|fail> · lint-imports <n>/5

Refs: Harness_LLM_orchestrator_project_review.md §4
```

**Never `git push`.** Do not create tags. Do not open a PR. Staging the two review documents and
this plan happens in W0's commit.

---

# §3 — Wave Plan

Each wave: steps → exit gate → commit. Tick boxes as you go.

---

## ☑ Wave 0 — Baseline capture and the verification harness

**Closes:** *(enabler for every later wave; addresses the mechanism half of C-2)*

- [x] **0.1** Create `scripts/verify.sh` (executable, `set -uo pipefail`, **not** `-e` — it must
      run all gates and report all failures, not stop at the first). It must:
      - print host facts: `git rev-parse --short HEAD`, `python --version`,
        `podman --version || echo "podman: absent"`;
      - run and capture, each with its real exit code:
        `uv run pytest -q` · `uv run pytest -q -m "not podman"` · `uv run pyright src/sagiha` ·
        `uv run lint-imports` · `uv run ruff check .` · `uv run ruff format --check .` ·
        `python3 scripts/docs_budget.py --max 15000` · `python3 scripts/check_links.py` ·
        `python3 scripts/gen_event_catalog.py --check`;
      - print the port count: `grep -rn "(Protocol)" src/sagiha/ports/ | wc -l`;
      - emit a markdown table on stdout in exactly the shape of the STATUS regression table;
      - exit `1` if any gate failed, `0` only if all passed.
- [x] **0.2** Run it. Save output to `docs/rationale/done/verify-baseline-W0.txt`.
      Expect: **5 red** (pyright 3, ruff 34, format 17, budget 15,183, links 106).
      **Measured: 5 red** — pyright 3, ruff 34, format **18**, budget 15,183, links 106.
- [x] **0.3** Stage `Harness_LLM_orchestrator_project_review.md`, `concept_review.md`, and this
      plan. *(Already tracked at `1fd9ff9`; nothing to stage — see L-7.)*

**Exit gate:** `scripts/verify.sh` runs end-to-end and reports 5 failures without crashing. It is
*expected to exit 1* here — that is the correct baseline.

**Commit:** `chore(v2-s0-s6): audit reports + verify.sh harness [W0]`

---

## ☑ Wave 1 — Retrieval honesty (C-1)

**Closes:** **C-1** *(Critical — do this before anything that measures retrieval)*

- [x] **1.1** In `src/sagiha/adapters/indexer/fts5.py`, add a module-level helper:
      ```python
      _FTS_OPERATORS: Final = frozenset({"AND", "OR", "NOT", "NEAR"})

      def _fts_query(text: str) -> str:
          """Convert free text into a safe FTS5 MATCH expression.

          FTS5 parses its argument as query syntax, so raw goal text containing
          `(`, `)`, `'`, `-` or `:` is a syntax error, not a search. Tokenize, drop
          bare operators, quote every term, OR them together for recall-oriented seeding.
          """
          tokens = [t for t in re.findall(r"\w+", text) if len(t) >= 2 and t.upper() not in _FTS_OPERATORS]
          return " OR ".join(f'"{t}"' for t in tokens)
      ```
- [x] **1.2** Route `neighbors` (renamed to `search` in W2) **and** `find_symbols` through
      `_fts_query`. If `_fts_query` returns `""` (no usable tokens), return `[]` **without**
      touching the database — that empty is a true empty and may be returned honestly.
- [x] **1.3** Narrow the swallow. Replace the bare
      `except sqlite3.OperationalError: return []` with:
      ```python
      except sqlite3.OperationalError as exc:
          if "no such table" in str(exc):
              return []          # cold index — a true empty
          logger.warning("FTS5 query failed for %r: %s", query, exc)
          raise
      ```
      Apply the same treatment to every other `except sqlite3.OperationalError` in the file.
- [x] **1.4** Add regression tests to `tests/contracts/test_indexer_conformance.py`:
      - `neighbors/search("Fix the bug in greet() so it returns a name")` returns the **same
        paths** as `("greet")`;
      - queries containing `'`, `-`, `:` and `()` all return non-empty against the fixture;
      - a query of only punctuation returns `[]` and issues **no** SQL;
      - a genuinely malformed internal state raises rather than returning `[]`.
- [x] **1.5** Re-run the review's C-1 reproduction snippet (Appendix A). All three goal-shaped
      queries must now return ≥1 hit.

**Exit gate:** `uv run pytest -q` green with the new tests; the C-1 reproduction returns hits.

**Commit:** `fix(v2-s0-s6): escape FTS5 queries, stop swallowing OperationalError [W1]`

---

## ☐ Wave 2 — Port conformance and type check (C-3 → C-R1 → m-4)

**Closes:** **C-3**, **C-R1**, **m-4** · **Order is mandatory:** the conformance test lands
*first*, fails, and is then made to pass by the contract fix. That sequence proves the test works.

- [ ] **2.1 (C-3)** Create `tests/contracts/test_adapter_conformance.py`. For each pair, a typed
      assignability assertion that pyright checks at the call site plus a pytest construction
      check. Cover all eight: `FTS5Indexer→Indexer`, `TreeSitterCodeGraph→CodeGraph`,
      `LocalWorkspace→Workspace`, `ContainerSandbox→Workspace`, `BestOfNSearch→CandidateSearch`,
      `SQLiteTrajectoryStore→TrajectoryStore`, `DefaultPolicyEngine→PolicyEngine`,
      `DefaultResourceGovernor→ResourceGovernor`.
      ```python
      def _accepts_indexer(_: Indexer) -> None: ...
      def test_fts5_satisfies_indexer(tmp_path: Path) -> None:
          _accepts_indexer(FTS5Indexer(db_path=str(tmp_path / "i.db")))
      ```
- [ ] **2.2** Confirm the new file makes `uv run pyright src/sagiha tests/contracts` report the
      `FTS5Indexer`/`Indexer` mismatch **at the new assertion site**. If it does not, the test is
      wrong — fix the test before proceeding.
- [ ] **2.3 (C-R1, per D1)** In `src/sagiha/ports/indexer.py`: rename `neighbors` → `search`,
      parameter `path: str` → `query: str`. **Delete** `neighbors` from the Protocol.
- [ ] **2.4** In `src/sagiha/adapters/indexer/fts5.py`: rename the method to `search`.
- [ ] **2.5** Update `src/sagiha/composition.py:131` — `await indexer.search(goal, limit=top_k)`.
- [ ] **2.6** Update the 7 test call sites: `tests/contracts/test_indexer_conformance.py` (×3),
      `tests/unit/test_fts5_indexer.py` (×3), `tests/unit/test_index_service.py` (×2).
- [ ] **2.7 (m-4)** Add public write methods to `FTS5Indexer`, mirroring the existing public
      `chunk_count()`:
      ```python
      def replace_file_chunks(self, path: str, chunks: Sequence[Chunk],
                              symbols: Sequence[tuple[str, str, str, int, str]]) -> None: ...
      def clear_path(self, path: str) -> None: ...
      ```
- [ ] **2.8** Rewrite `adapters/indexer/service.py` `_reindex_python` and `_reindex_markdown` to
      call those methods. **Delete both `sqlite3.connect(self._indexer._db_path)` blocks.** No
      `db_path` property — that would silence pyright while leaving `IndexService` coupled to the
      FTS schema (explicitly rejected by the review).
- [ ] **2.9** `tests/unit/test_index_service.py` reaches `index_service._indexer` directly at 4
      sites. Leave those — a test reaching into the object under test is acceptable — but retarget
      them to the renamed `search`.

**Exit gate:** `uv run pyright src/sagiha` → **0 errors**. `uv run pytest -q` green.

**Commit:** `fix(v2-s0-s6): Indexer.search contract, adapter conformance tests, encapsulate FTS5 writes [W2]`

---

## ☐ Wave 3 — Lint and format green (m-14)

**Closes:** **m-14**, ruff, format

- [ ] **3.1** Add the `extend-exclude` block from **D9** to `[tool.ruff]` in `pyproject.toml`,
      with a comment pointing at the pyright rationale at `pyproject.toml:63-69`.
- [ ] **3.2** `uv run ruff check --fix .` then `uv run ruff format .`
- [ ] **3.3** Hand-fix what `--fix` cannot: the `E501` long lines, the `UP035`/`UP006` deprecated
      typing imports, and the `ASYNC240`/`ASYNC251` blocking-call-in-async findings.
      **`ASYNC240`/`ASYNC251` are real defects, not style** — a blocking `Path` method or
      `time.sleep` inside an async function stalls the event loop. Fix them properly
      (`anyio.to_thread.run_sync` / `anyio.sleep`); do not `# noqa` them.
- [ ] **3.4** Fix `keep_alive.py` (4) and `scripts/extract_gemini_share.py` (1). Do not exclude,
      do not delete.
- [ ] **3.5** Re-run `uv run pytest -q` — formatting touched 17 files; confirm nothing broke.

**Exit gate:** `uv run ruff check .` → **0** · `uv run ruff format --check .` → **0** ·
`uv run pytest -q` green.

**Commit:** `style(v2-s0-s6): scope ruff to project code, clear all lint and format findings [W3]`

---

## ☐ Wave 4 — Docs governance green (C-2b, C-3d, m-12)

**Closes:** **C-2b**, **C-3d**, **m-12**

- [ ] **4.1 (C-2b, per D10)** Retag `docs/implementation/contracts-to-code.md` →
      `status: rationale` + `retrieval: excluded`. Verify: `docs_budget.py --max 15000` → exit 0,
      expect ≈ **14,474**.
- [ ] **4.2 (m-12, per D8)** Add the eight `status:`/`retrieval:` frontmatter blocks per the D8
      table. Re-run the budget — the count must not rise (none is tagged `normative`).
- [ ] **4.3 (m-12)** Modify `scripts/docs_budget.py` to **exit non-zero** when any file under
      `docs/` lacks a `status:` tag, instead of merely listing them. Ordering matters: 4.2 first,
      or the build goes red mid-wave.
- [ ] **4.4 (C-3d, per D11 batch 1)** Repoint all `refactor_sagiha_v2_guidelines.md` references
      to `docs/implementation/refactor_sagiha_v2_guidelines.md` at the correct relative depth.
      Known sites include `docs/STATUS.md` and `docs/08-decisions/0024-e0-is-a-tool-not-a-port.md`.
- [ ] **4.5 (batch 2)** Remove the ~4 links to the deleted
      `rationale/reviews/2026-07-29-foundation-review.md`, keeping surrounding prose intact.
- [ ] **4.6 (batch 3)** Convert every `file:///home/rock_dev/...` URL under `docs/` to a
      repo-relative path.
- [ ] **4.7** Iterate `python3 scripts/check_links.py` until it reports **0**. Fix targets, not the
      checker.

**Exit gate:** `docs_budget.py --max 15000` → exit 0 · `check_links.py` → exit 0 ·
`gen_event_catalog.py --check` → exit 0.

**Commit:** `docs(v2-s0-s6): clear word budget, repair 106 dead links, tag every doc [W4]`

---

## ☐ Wave 5 — SSOT truth and ADRs (C-2, M-6, M-7, m-8, m-9, m-13)

**Closes:** **C-2**, **M-6**, **M-7**, **m-8**, **m-9**; formally withdraws **m-13**
**This wave completes P0. Do not start it until W1–W4 are all green.**

- [ ] **5.1 (D13)** Write `docs/08-decisions/0026-indexer-search-replaces-neighbors.md` per D1.
- [ ] **5.2 (D13)** Write `docs/08-decisions/0027-fixed-chunk-size-policy.md` per D2.
- [ ] **5.3 (M-7)** Replace "21 → 15" at `docs/implementation/development_plan_v2.md:19` and
      `:221` with "17 (ADR-0019 as restated, plus ADR-0024)". Leave
      `next_gen_architecture_specs.md:46` and `codebase_delta_refactor.md:30` alone — both are
      `status: historical` and record what was believed at the time.
- [ ] **5.4 (M-6)** Tick the 18 delivered-but-unchecked epic boxes in `development_plan_v2.md`.
      Verify each against git history before ticking; if any is genuinely undelivered, leave it
      unchecked and record that in §5 — do not tick to make a document tidy.
- [ ] **5.5 (m-8)** Amend the S5 credential wording in `development_plan_v2.md` and
      `docs/STATUS.md` to state exactly what exists: host-environment scrub plus
      `SECRET_MATERIALIZE_NAMES` path exclusion. Remove "per-grant short-lived injection"; note it
      as an S7 candidate.
- [ ] **5.6 (m-9, per D5)** Add the `run_command`-under-taint rationale to
      `docs/02-architecture/security-and-threat-model.md#t7`: gates must run `git` under taint or
      H1 regresses; under `runtime=container` the perimeter is the real boundary. **No code
      change.**
- [ ] **5.7 (D11)** Add the "no absolute `file://` links in `docs/`" rule to the docs conventions
      section (wherever `check_links.py`'s contract is described).
- [ ] **5.8 (C-2)** Run `scripts/verify.sh`. Confirm **all seven gates green**. Save output to
      `docs/rationale/done/verify-W5-p0-complete.txt`.
- [ ] **5.9 (C-2)** Replace the `docs/STATUS.md` "Frozen Regression Signals" table by **copying
      5.8's output**. Add the three missing rows (docs budget, link integrity, event catalog).
      Fix the test arithmetic: **321 non-Podman + 11 Podman = 332**, with the host fact stated.
      Add the line: *"This table is generated by `scripts/verify.sh`. Do not edit by hand."*
- [ ] **5.10 (m-13, per D4)** Record the withdrawal of m-13 in §5. No code change.

**Exit gate:** `scripts/verify.sh` exits **0**. Every number in `docs/STATUS.md` traceable to
5.8's saved output.

**Commit:** `docs(v2-s0-s6): ADRs 0026-0027, SSOT truth, STATUS from verify.sh [W5]`

> ### 🏁 **P0 COMPLETE.** The tree is now tag-ready. Tagging and pushing remain human decisions and
> are **not** part of this plan.

---

## ☐ Wave 6 — Retrieval quality bundle (m-3, M-3, M-5, M-4)

**Closes:** **m-3**, **M-3**, **M-5**, **M-4** · P1 — prerequisites for ever enabling retrieval

- [ ] **6.1 (m-3)** Create `src/sagiha/adapters/indexer/walk.py` exporting `SKIP_DIRS`,
      `TEXT_EXTENSIONS`, `MAX_CHUNK_TOKENS` (per D2), and `module_name(path) -> str`.
- [ ] **6.2 (m-3)** Import from it in all four duplication sites and delete the local copies:
      `indexer/fts5.py:22`, `indexer/service.py:18`, `code_graph/treesitter.py`,
      `outer_loop/init/generate.py:12`.
- [ ] **6.3 (M-3)** `walk.module_name` uses the **full dotted path** form
      (`pkg/util.py → "pkg.util"`), matching today's `treesitter._module_name`. Delete both local
      `_module_name` definitions. This changes indexer `symbol_path` values — expect
      `tests/unit/test_fts5_indexer.py` and the chunking tests to need updated expectations.
- [ ] **6.4 (M-3)** Add a conformance assertion: for a fixture file, every chunk `symbol_path`
      prefix matches a graph `defines` name for the same path.
- [ ] **6.5 (M-4, per D2)** Delete `RetrievalConfig.max_chunk_tokens`; remove the parameter from
      `IndexService.__init__`, `analyze_python_tree`, `analyze_python_source`,
      `chunk_python_source`, and the `composition.py:157` call site. Delete the
      `del max_chunk_tokens` line. Replace `fts5.py:68`'s literal `1024` with
      `walk.MAX_CHUNK_TOKENS`.
- [ ] **6.6 (M-5)** In `chunking.py`, prepend the envelope to indexed chunk text:
      `f"{path}\n{symbol_path}\n{signature}\n---\n"` + body. Keep `Chunk.text` carrying the
      envelope (it is what gets indexed and what gets shown); if any consumer needs the raw span,
      add a separate field rather than stripping at read time.
- [ ] **6.7 (M-5)** Update conformance assertions: a search for a **path fragment** and a search
      for a **dotted symbol name** must both return the chunk.

**Exit gate:** `scripts/verify.sh` exits 0. **Retrieval stays `enabled=false`** — this wave
improves the mechanism, it does not license a default flip. That requires W9.

**Commit:** `refactor(v2-s0-s6): shared indexer walk vocabulary, chunk envelope, drop dead chunk knob [W6]`

---

## ☐ Wave 7 — Quality and completeness (M-8, m-1, m-2, m-5, m-7)

**Closes:** **M-8**, **m-1**, **m-2**, **m-5**, **m-7** · P2

- [ ] **7.1 (M-8, per D3)** Delete `src/sagiha/adapters/search/sequential.py`; strip its import
      and `__all__` entry from `adapters/search/__init__.py`; delete any test that imported it.
- [ ] **7.2 (m-1)** In `cli.py:648`, when `--reindex` is passed or `.sagiha/code_graph.db` exists,
      construct/load `TreeSitterCodeGraph` and pass it to `generate_agents_md` instead of `None`.
- [ ] **7.3 (m-2, per D7)** Fix `_discover_python_modules`: strip a leading `src/`; include
      non-`__init__` modules under discovered package roots; use `walk.SKIP_DIRS`.
- [ ] **7.4 (m-5)** Make full reindex prune orphans: track seen paths during `_reindex_all` and
      delete chunk/symbol/edge rows for unseen paths. Test: index, delete a file, reindex, assert
      its chunks are gone.
- [ ] **7.5 (m-7, per D6)** Route the export CLI's schema construction through the config-driven
      registry helper; `logger.warning` naming the run id when the tool set cannot be
      reconstructed with certainty. Note the trajectory-snapshot approach as the S7 follow-up in
      the module docstring.

**Exit gate:** `scripts/verify.sh` exits 0.

**Commit:** `fix(v2-s0-s6): remove lying search stub, wire init graph, prune index orphans [W7]`

---

## ☐ Wave 8 — Perimeter CI (M-2)

**Closes:** **M-2** · P1

- [ ] **8.1** Land the job proposed in `docs/implementation/ci-podman-perimeter.md` into
      `.github/workflows/ci.yml`: a Podman-capable runner executing `pytest -m podman` plus the
      workspace conformance suite parametrized over `LocalWorkspace` and `ContainerSandbox`.
- [ ] **8.2** The job must **fail**, not skip, when Podman is absent on a runner that is supposed
      to have it. A perimeter test that silently skips is an unenforced perimeter — the M-2 defect
      wearing a green checkmark.
- [ ] **8.3** Add the egress canary: assert direct outbound fails and that only allowlisted hosts
      traverse the CONNECT proxy.
- [ ] **8.4** Add a Podman row to `scripts/verify.sh` output reflecting host presence.

**Exit gate:** CI config validates; the job passes locally via `act` or an equivalent dry run.

**Commit:** `ci(v2-s0-s6): gate the Podman perimeter and egress canary [W8]`

---

## ☐ Wave 9 — Benchmark suite and ablations (M-1)

**Closes:** **M-1** · P1 · **Requires network access and a dataset decision outside this tree.**

> **Hard precondition: W1 must be complete.** Running a retrieval ablation before C-1 is fixed
> manufactures a false negative and publishes it. This is stated in the review and restated here
> because it is the single most expensive mistake available in this plan.

- [ ] **9.1** Import (do not harvest) a ≥30-task suite with pinned base commits — SWE-bench Lite
      subset is the decided source. Harvesting from this repo yielded 0/23 and is not retried.
- [ ] **9.2** Commit it at `benchmarks/definitions/s0-core.json` (the path the plan and the
      `noise-floor.md` template already reference).
- [ ] **9.3** Run `sagiha bench --suite benchmarks/definitions/s0-core.json --aa --runs 2` and
      replace `docs/rationale/benchmarks/noise-floor.md` with the real output.
- [ ] **9.4** Unguard the `bench-aa` CI job.
- [ ] **9.5** Run the three ablations — BoN vs single-shot, retrieval on/off, init on/off.
- [ ] **9.6** Publish each result **or shelve it honestly**. A default flip to `enabled=true` is
      permitted only for a capability whose delta beats the measured A/A floor. A negative result
      is published as a negative result and the default stays off.

**Exit gate:** `noise-floor.md` populated from a real run; each ablation either published with
numbers or explicitly recorded as not-yet-measured.

**Commit:** `bench(v2-s0-s6): pinned s0-core suite, populated noise floor, ablations [W9]`

---

# §4 — Execution Log

Fill one row per wave, at commit time, from real command output. **Do not pre-fill.**

| Wave | Status | Commit SHA | pytest | pyright | ruff | format | budget | links | catalog | imports | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| *baseline* | — | `eae4c22` | 332 | 3 ❌ | 34 ❌ | 17 ❌ | 15,183 ❌ | 106 ❌ | ok | 5/5 | audit HEAD |
| W0 | ☑ | `5a8ea4c` | 332 | 3 ❌ | 34 ❌ | 18 ❌ | 15,183 ❌ | 106 ❌ | ok | 5/5 | baseline reproduced; 5 red as expected (format 18, not 17) |
| W1 | ☑ | `PENDING-W1` | 342 | 3 ❌ | 34 ❌ | 18 ❌ | 15,183 ❌ | 106 ❌ | ok | 5/5 | +10 tests; C-1 closed, other gates untouched by design |
| W2 | ☐ | | | | | | | | | | pyright must be 0 |
| W3 | ☐ | | | | | | | | | | ruff + format must be 0 |
| W4 | ☐ | | | | | | | | | | budget + links must be 0 |
| W5 | ☐ | | | | | | | | | | **all 7 green — P0 done** |
| W6 | ☐ | | | | | | | | | | |
| W7 | ☐ | | | | | | | | | | |
| W8 | ☐ | | | | | | | | | | |
| W9 | ☐ | | | | | | | | | | |

---

# §5 — Decision & Deviation Log

Append-only. Record (a) decisions already made during planning that changed a review finding, and
(b) any D0 resolution taken during implementation.

| # | Date | Wave | Decision / deviation | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| L-1 | 2026-08-01 | plan | **m-13 withdrawn.** `runtime/` and `aoi/` already carry the explanatory docstrings the finding requested, and both are named in `.importlinter` contracts — deleting them would break 4 of 5 import contracts | Re-verification during planning; the audit finding was cosmetic and partly incorrect |
| L-2 | 2026-08-01 | plan | **C-R1 resolved beyond the review's options:** `neighbors` is *deleted* from `Indexer`, not retained as graph expansion | ADR-0023 port rent — zero adapters would implement it, and `CodeGraph.impacted_by` already covers the use case (D1) |
| L-3 | 2026-08-01 | plan | **M-4 resolved as deletion**, not implementation | An unmeasurable chunking heuristic cannot be validated without M-1; deletion is honest and reversible (D2) |
| L-4 | 2026-08-01 | plan | **m-9 is documentation-only**; the proposed policy tightening is not implemented | It is a security-behavior change requiring threat review and a canary suite, out of scope for remediation (D5) |
| L-5 | 2026-08-01 | plan | **m-7 uses config-driven reconstruction + warning**, not a trajectory snapshot | Snapshot is a schema migration serving a consumer that does not exist yet; the warning makes residual uncertainty visible (D6) |
| L-6 | 2026-08-01 | plan | **`ASYNC240`/`ASYNC251` treated as defects, not style** — fixed properly, never `# noqa` | Blocking calls in async functions stall the event loop; suppressing them would be lint-theatre (W3.3) |
| L-7 | 2026-08-01 | W0 | **Step 0.3 is a no-op.** The two review documents and this plan were already committed at `1fd9ff9`; there was nothing unstaged to stage | Verified with `git status --short` (clean tree) before starting W0 |
| L-8 | 2026-08-01 | W0 | **Baseline format count is 18, not the 17 the plan predicted.** All other four red gates match exactly | D0: numbers come from commands, not from the plan's prediction. Recorded as measured; the audit ran on a different working tree state |
| L-9 | 2026-08-01 | W0 | **Branch is `refactor_aether_V210`, not `refactor_aether_v2`** as the plan header states | The branch was renamed before execution began; all other rules (never push, no tags, no PRs) apply unchanged |
| L-10 | 2026-08-01 | W1 | **Step 1.2's `find_symbols` half is not applied.** Only `neighbors` routes through `_fts_query` | D0. Verified premise error: `find_symbols` queries the `symbols` table with `name LIKE '%q%'` (`fts5.py:152`), not `chunks MATCH`. It never parses FTS5 syntax, so it cannot exhibit C-1, and forcing a `"a" OR "b"` expression through `LIKE` would *introduce* a defect. Its contract is documented substring-by-name search and its caller is the agent-facing tool, which passes symbol names, not goals |
| L-11 | 2026-08-01 | W1 | **Step 1.5's "all three must return ≥1 hit" holds for two of three.** `"handle user's input"` returns 0 against the snippet's one-line corpus (`def greet(name): return 1`) | Not a regression — that is now a *true* empty: the corpus contains none of `handle`/`user`/`input`. Verified by re-running with a file containing those tokens, which returns 1 hit. The C-1 symptom (a swallowed `OperationalError` masquerading as no-matches) is gone; the two goal-shaped queries with matching tokens both return hits |
| | | | | |

---

# §6 — Risk Register

| Risk | Wave | Mitigation |
| :--- | :--- | :--- |
| W1's `_fts_query` OR-joining every token tanks precision (everything matches something) | W1 | Accept for now — recall-oriented seeding is correct for a *seed*, and precision is unmeasurable until W9. Revisit with the ablation, not before |
| W2's port rename breaks an unnoticed caller | W2 | Verified: exactly 1 production + 7 test call sites. `pyright` catches any missed site because the method no longer exists on the Protocol |
| W3's `ruff format` touches 17 files and hides a real change in the diff | W3 | Commit formatting in its own wave (this one), never mixed with logic changes. Re-run pytest after formatting (step 3.5) |
| W4's link repair breaks an anchor rather than a file path | W4 | `check_links.py` validates anchors; iterate to 0 rather than assuming |
| W6's `module_name` change silently invalidates existing `.sagiha/index.db` files | W6 | The index is a rebuildable cache (ADR-0011). Note in ADR-0027 that W6 requires a reindex; no migration is owed for a cache |
| W9 publishes a negative result caused by a remaining bug | W9 | Hard precondition on W1 (stated in the wave). Do not run ablations against a subsystem with open Critical defects |
| Someone pushes mid-plan | all | D14: never push. Pushing is a separate human decision after P0 |

---

# §7 — Definition of Done

**P0 (Waves 0–5) is done when:**

1. `scripts/verify.sh` exits **0** — all seven gates green.
2. Every number in `docs/STATUS.md`'s regression table was copied from a saved `verify.sh` run,
   and the table says so.
3. ADR-0026 and ADR-0027 exist and record the two contract changes.
4. `sprints_0_to_6_fix_plan.md` §4 has real SHAs for W0–W5 and §5 records every deviation.
5. Six commits exist on `refactor_aether_v2`. **Nothing has been pushed.**

**The full plan (Waves 0–9) is done when**, additionally, retrieval and search each have a
published measured delta against a real A/A noise floor — or an explicit, published record that
they do not beat it and therefore remain off.

---

*End of `sprints_0_to_6_fix_plan.md`. Begin at Wave 0. Do not deliberate — §2 already decided.*
