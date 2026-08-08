---
status: rationale
updated: 2026-08-07
---

# Sprint 3 Developer Prompt — The Repair Edge and the Floor

*Handoff prompt for whoever (human or agent) executes Sprint 3. Grounded in the actual
Sprint 1/2 codebase, not just the sprint doc — read this before `sprint-03.md`.*

---

## Context

You're picking up AETHER v3.0.0 after Sprint 1 (pure domain/ports/kernel choke point) and
Sprint 2 (real adapters + the M1a walking skeleton — `retrieve → generate → apply →
evaluate` runs end to end through `engine.run()`, uncontained, no benchmark number
published per ADR-0002). Everything in `src/aether/{domain,ports,kernel,adapters,measurement,
workflow}/`, `composition.py`, and `engine.py` is real and tested — read it before writing
anything that duplicates it.

**This is the hinge sprint.** Before it: zero capability numbers exist, by design
(`docs/decisions/0002-no-number-before-the-floor.md`). After it: the A/A floor's discordance
rates derive N for every future admission run, and M2-onward finally gets sized off real
per-task wall-clock instead of a guess. Nothing you do here is optional scaffolding — Task 5
is the sprint's entire reason to exist, and Tasks 1–4 are its preconditions.

Read in this order before starting: `docs/vision.md` §4 (why this project distrusts its own
numbers), `docs/measurement.md` §2–6, `docs/decisions/0002-no-number-before-the-floor.md`,
`docs/decisions/0003-statistical-admission-protocol.md`, `docs/agile/sprints/sprint-03.md`
(the normative task list — this document is commentary on it, not a replacement).

## Non-negotiable house rules, learned the hard way in Sprints 1–2

- **No `--force` flags, ever.** The topology validator, the manifest validity gate, and the
  family gatekeeper all exist specifically so a failing check cannot be bypassed. If a check
  is inconvenient, fix what it's checking — don't add an escape hatch.
- **TCB residency is a real import-linter contract, not a convention.** `measurement/evaluator.py`
  already can't import `agency/` or `workflow/` (`aether-tcb-isolation` in `.importlinter`).
  Anything you add to `measurement/` that's genuinely TCB (the manifest, the statistics engine,
  the sandbox) needs the same discipline — check `.importlinter` before you write the module,
  not after CI fails.
- **Every gate ships with a negative test proving it can fail.** This isn't a nice-to-have —
  it's the project's founding rule (`vision.md` §4) after the predecessor's gates silently
  passed over broken instruments three separate times.
- **Wire-serializable payloads, JSON descriptors through the dispatcher.** Sprint 2 established
  the pattern in `composition.py`/`workflow/dispatch_facade.py`: effect payloads are Pydantic
  `Frozen` models, JSON-encoded into `EffectRequest.descriptor`, results come back through
  `EffectOutcome.result_json`. Follow it for any new effect_class (e.g. `sandbox` container
  ops) rather than inventing a second channel.
- **`GateStatus.NONE` is not `FAILED`.** This distinction (B4, already built) is what Task 3's
  repair-routing and Task 5's floor both depend on. If you find yourself writing `if not
  passed: repair()`, you've silently merged `FAILED` and `NONE` — stop and use the tri-state.
- **A number without its instrument tuple isn't a result.** Manifest hash, model fingerprint,
  topology hash, container digests, lockfile hash, seed — every one, every time, per
  `measurement.md` §6 and the Sprint 3 DoD item 10.
- **Mocks live in `tests/aether/mocks.py`, real adapters in `src/aether/adapters/`, TCB
  implementations in `kernel/` or `measurement/` per residency, never `adapters/`.** This
  placement is what makes the import-linter contracts mean anything.

---

## The five tasks, in dependency order

### 1. `TASK-016` — Evaluation container & B3 canary (closes B3)

The literal defect class that fabricated numbers last time (`.pth` leak). Build
`src/aether/adapters/sandbox/podman.py` + `containers/eval/`: rootless Podman, `--network
none`, `--cap-drop all`, `--security-opt no-new-privileges`, `--userns=keep-id`, read-only
root, `--pids-limit`, CPU/memory from the `ResourceGovernor` lease you already have
(`kernel/governor.py`). **Exactly two mounts**: task worktree (RW), pinned image layers (RO)
— no home, no sockets. Container created **from digest, never tag**
(`environment_image_digest` is already a field on `EvalSpec`/the manifest schema — use it).

Wire this into `measurement/evaluator.py`'s `RealEvaluator` (or a sibling), replacing the
current uncontained `asyncio.subprocess` execution — but don't break the existing conformance
suite's fast path; keep an uncontained mode available for CI machines without Podman
(mirror the existing `SAGIHA_REQUIRE_PODMAN` / `tests/podman_support.py` hard-fail-if-promised
pattern from the predecessor tree — it already solved "skip locally, fail hard when a runner
claims to have it").

**The canary is the deliverable, not a checkbox**: a deliberately broken candidate (a patch
that trivially breaks the isolation, e.g. one that tries to read `../` outside the worktree,
or exfiltrate via network) must **fail** evaluation. Write this as an actual negative test
before you're done, and run it in the same environment Task 5's floor will run in — that's
an explicit precondition of Task 5, not a nice-to-have ordering.

### 2. `TASK-014` — Task-manifest tooling & bidirectional validity canary

`src/aether/measurement/manifest.py` + `src/aether/measurement/schemas/manifest_schema.yaml`.
The exact schema shape is already specified in `docs/architecture/schemas_and_contracts.md`
§2 — copy it, don't redesign it (same pattern as Sprint 2's `workflow_schema.yaml`).

Core logic: a task enters the manifest **only if the gold patch passes and the empty patch
fails** on your own instrument (Task 1's container + Sprint 2's `RealEvaluator`). This is
bidirectional and per-task — run both, both must land on the correct side, or the task is
excluded. **Publish every exclusion with a typed reason** (the schema's `exclusions` enum:
`gold_patch_fails | empty_patch_passes | image_unbuildable | flaky_tests |
upstream_retracted`) — silent exclusion is the exact overfitting vector `measurement.md`
warns about, and ~30% of public Pro tasks were estimated broken in a mid-2026 audit, so
expect a real exclusion list, not zero.

Split assignment (`dev`/`holdout`/`sealed`) is pinned **in the manifest** at build time —
it's TCB data, immutable once pinned; a change is a new manifest with a new hash. Manifest
identity is `sha256` over canonical JSON (sorted keys, no whitespace) — same convention as
Sprint 2's `test_command_hash`/`hash_command()` in `measurement/evaluator.py`, reuse that
helper's approach.

Use `docs/benchmarks/swe_verified_sample.md` / `swe_pro_sample.md`'s 15-task samples and
Sprint 1's `repo_cache.py` (already resolves base commits) as your first real manifest's
input — you don't need the full suite to prove the tooling works, and a 15-task manifest is
plenty to smoke B3's canary and seed Task 5's DEV split.

### 3. `TASK-023` — Repair node & bounded iteration (closes M1a+)

**This is the highest-leverage task in the sprint** — `vision.md` §2 names it *"the single
largest lever on score in the entire system."* `evaluate →(fail, k)→ repair → apply →
evaluate`, statically unrolled to `max_iterations` (bounded 1–16, per the schema you already
have in `workflow/schemas/workflow_schema.yaml`'s `repair` block — it's defined but unused
by Sprint 2's `linear_v1.yaml`).

Concretely, extend what Sprint 2 built rather than rewriting it:
- `workflow/validator.py`'s `check_bounded_iteration` already validates the schema-level
  `max_iterations` range and node-id cross-references for a `repair` block that's present —
  Sprint 2 left it exercised only vacuously (no topology used it). Task 3 is what actually
  puts a `repair` block in a real topology (`workflows/linear_repair_v1.yaml`) and proves the
  validator rejects a malformed one (missing bound, over-bound, dangling reference) with a
  real negative-test fixture, same pattern as `tests/aether/workflow/test_validator.py`.
- New `workflow/nodes/repair.py`: a `WorkflowStep` whose input includes the failing
  `GateReport` and prior context, output feeds back into `apply`. **A `GateStatus.NONE`
  report must never route into this node** — wire that check into `workflow/executor.py`'s
  edge-following logic (or the validator, whichever enforces it structurally rather than by
  convention) before you consider this done. Repairing against an instrument failure teaches
  the loop to fix your harness's bugs, not the task's.
- Each repair iteration reserves its **own** budget through `kernel/governor.py`'s
  `reserve/commit/release` — you already have real atomic reserve/commit/release with parent-
  lease refunding from Sprint 2 (`TASK-034`); a bounded loop of N iterations is N reservations
  against the node's (or a parent) budget, not one reservation stretched thin.
- Test output entering the repaired context needs to be **tail-biased truncated** — the
  traceback the failure needs, not the pass list burning tokens. `measurement/evaluator.py`
  already has a `_tail()` helper for this exact purpose (currently used for `GateReport.detail`)
  — reuse or extend it rather than writing a second truncation strategy.

This ships and is *measured* by its ablation at M2 — it does not need to prove itself
superior in this sprint, only to exist correctly and safely (bounded, `NONE`-excluded,
budget-honest).

### 4. `TASK-012` + `TASK-015` — Statistics engine & comparative rig

**Highest specialist-skill task in the sprint.** `src/aether/measurement/statistics.py`:
port the predecessor's `e0/statistics.py` **verbatim** (exact McNemar, Holm–Bonferroni,
seeded bootstrap) — this is the one asset from the prior codebase verified line-by-line, per
`spec.md` §9's predecessor-code clause. **Record its provenance in the module docstring.**
Don't "improve" it while porting; verbatim means verbatim, then extend.

On top of the verbatim port, add the rev. 2 layer per `docs/decisions/0003-statistical-
admission-protocol.md` and the `family_schema.yaml` shape already specified in
`schemas_and_contracts.md` §3: a seeded Monte-Carlo power simulation deriving N from
`(minimal_effect_pts, assumed_p01, assumed_p10, target_power)`, re-runnable from a family
file alone. **The module must refuse to compute corrected p-values for an undeclared
family** — this is the anti-p-hacking enforcement mechanism, make it a hard raise, not a
lint warning. Pin JSON fixtures for both the verbatim statistics and the power simulation
and gate on them, same discipline as everything else in this codebase.

`HarnessUnderTest` (`measurement/runner.py`): a seam producing paired outcomes for
`(harness, model, manifest)` through **your own** `Evaluator` (Sprint 2's `RealEvaluator`,
now containerized by Task 1). This sprint ships **only the seam plus the bare-model arm** —
one completion, official SWE-bench inference template, template hash recorded, no execution
feedback, temperature/seed pinned, identical model fingerprint to what the harness arm will
use. The OpenHands arm and the AETHER arm's own comparative run are explicitly **not** this
sprint — don't scope-creep into them.

### 5. Run the A/A variance floor — the sprint's actual deliverable

Everything above exists to make this measurable and trustworthy. Two identical AETHER
configurations, paired: same tasks (your Task 2 manifest's DEV split), same order, same
seeds. **N ≥ 50** at the smoke tier. Before you run it:

- **Blocking precondition**: Task 1's B3 canary executes *in this exact environment* and a
  deliberately broken candidate fails. If it passes here, stop — the floor is blocked
  regardless of anything else being ready.
- Report **discordance rates (p₀₁, p₁₀)** — these seed every future family's derived-N
  calculation. Without them, no later admission run in this project can be sized, ever.
- Record **per-task wall-clock** — this is the number that sizes M2-abl, currently the one
  unsized item in `roadmap.md`. Sprint 4 cannot be planned honestly without it.
- Name the full instrument tuple: manifest hash, split, model fingerprint, topology hash,
  container digests, lockfile hash, seed.
- Write it up at `docs/benchmarks/results/noise-floor.md`, same honesty discipline as
  Sprint 2's `performance_timers.md` — **a wide floor is a measurement, not a failure.**
  If nothing clears, that's the correct and expected thing to write down.

---

## Suggested sequencing

Task 1 (container) and Task 2 (manifest) can start in parallel — neither depends on the
other, and both are pure preconditions. Task 3 (repair) depends on nothing above and can
also start immediately in parallel — it's pure `workflow/`/`kernel/` work reusing Sprint 2's
governor and validator. Task 4 (statistics) is independent code but its comparative rig
needs Task 1's container to be meaningful, so land the verbatim statistics port early and the
`HarnessUnderTest` seam once Task 1 is real. **Task 5 is strictly last** — it needs Task 1's
canary passing in its own environment, Task 2's manifest to select tasks from, Task 3 to be
correct (repair participates in what's being measured), and Task 4's statistics module to
compute what it reports.

## Definition of done (in addition to the standing Sprint 1/2 DoD)

- Every new gate (canary, validity check, family gatekeeper) has a negative test proving it
  can fail — check this explicitly before calling any task complete, per this project's
  founding rule.
- `pytest`, `ruff`, `pyright --strict`, `import-linter` all green on everything touched,
  same bar Sprint 2 held (135/135 passing, 0 pyright errors, 9/9 contracts kept — don't
  regress that).
- `docs/STATUS.md` and `sprints/sprint-03.md`'s gate table updated with pasted, real gate
  results — no claim without a command output backing it, same rule the file already holds
  itself to.
- No capability number leaves this sprint without its full instrument tuple attached.
