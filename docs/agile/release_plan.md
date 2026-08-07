---
status: rationale
updated: 2026-08-07
---

# Release Plan — The Ten-Sprint Arc

**What this is.** A single view of the whole development arc, for planning and staffing. It
exists because [`roadmap.md`](./roadmap.md) is `normative` and binds dependency *edges*, and
[`sprints/README.md`](./sprints/README.md) deliberately refuses to plan past the A/A floor —
both correct, and neither answers *"what does the shape of the next year look like?"*

**What this is not.** Sprints 1–5 are grounded: 1–3.5 shipped, 4–5 have written plans.
**Sprints 6–10 are projections, not commitments.** [ADR-0009](../decisions/0009-gates-are-the-schedule.md)
forbids turning an unmeasured number into a schedule, and M2-abl's wall-clock is dominated by
inference across derived N — a quantity that does not exist until Sprint 4's floor reports
p₀₁/p₁₀ and per-task wall-clock. Read rows 6–10 as **ordering and content**, never as dates.

Gaps marked *(unfunded)* come from [`coverage_audit.md`](./coverage_audit.md).

---

## The arc

| # | Milestone · Status | Technical scope (tasks) | Deliverable / exit gate | What it unlocks for us |
|:--|:--|:--|:--|:--|
| **1** | M0 · B1 · B2a · B4 — ✅ **done** | `000` `001` `002` `003` `004` `005` `010` `013` — pure domain, 9 wire ports, TCB dispatch choke point, repo cache, tri-state `GateReport` | `domain-is-pure` + `tcb-isolation` green; drift test can fail | Every effect has one auditable path; instrument errors stop counting as failures |
| **2** | M1a · B2b — ✅ **done** | `011` `017` `018` `019` `020` `021` `022` `026` `034` — real adapters, 4-node linear DAG, governor ledger, event bus | `retrieve→generate→apply→evaluate` runs end to end from a validated topology | A task can actually be attempted; budgets are enforced, not estimated |
| **3** | M1a+ · B3 — ✅ **done** *(floor deferred)* | `012` `014` `016` `023` — bounded repair edge, Podman evaluator, pinned 84-task manifest, McNemar + derived-N | B3 canary 7/7; manifest `sha256:7c2c2467…`; power table reproduced in 12/12 cells | The judge is isolated and the statistics can refuse a bad claim |
| **3.5** | M1a++ — ✅ **done** *(unplanned; created instrument debt)* | `037`–`041` — edit-format seam, registry by kind, repair re-reads worktree, architect/reflector | 7 topologies validate; small models start passing | Loop engineering became data-driven — but I7 and the baseline broke |
| **4** | M1a++R · **A/A floor** — 📋 **planned** | `049` `049b` `050` `051` `052` `062` + the floor run | I7 gate can fail; CI green at step one; **p₀₁/p₁₀ + per-task wall-clock** in `noise-floor.md` | The first number this project is allowed to have. Every later N is derived from it |
| **5** | M1b — 📋 **planned** | `053`–`058` + `006` — ADR-0018 lattice, `agency/`, ContextSource · Inference · Parser · Assembler, `ModelNode`+`RoleSpec`, `RunConfig`, cassettes | `lint-imports` 9/9 with `agency` populated; golden-prompt equivalence; one typed engine input | A new agent role becomes 5 lines of data. GUI/CLI/TUI forms generate from one schema |
| **6** | M2-eng — ⬜ *projection, sized off S4* | `032` memoization · `064` localization · `066` SearchReplace · `068` attenuation · `069` turn budget | Unchanged subtrees skip; `ARCHITECT` is read-only **by type**; retrieval-recall diagnostic | Ablations become cheap to re-run; the harness can finally pick which files to open |
| **7** | M2-abl — ⬜ *projection, genuinely unsized* | `023`+`012` repair ablation (first) · `031/056` context · `025` Architect/Editor · `024` compaction | Each mechanism clears the floor at derived N on HOLDOUT — **or is deleted** | We learn which of our own ideas actually work. Losers leave the codebase |
| **8** | M3 — ⬜ *projection* | `035` branching + fan-out · `033` cache sequencing · `067` execution-based ranker · `059` strategies · `060` fragments | Every fan-out has a declared join; N child leases from one parent; rankers order, never admit | Best-of-N, rescue cascades, compound DAGs — the topologies that win benchmarks |
| **9** | **M4-a Benchmark Delivery** — ⬜ *(unfunded)* | `036` images · `071` SWE-bench manifest + validity canary at scale · `072` **SWE-bench** A/A floor · `042`–`045` routing + honest pricing | A pinned SWE-bench manifest with published exclusions; its own discordance rates | The mission's instrument. Hybrid arms become admissible and cost-honest |
| **10** | **M4-b Publication** — ⬜ *(unfunded)* | `073` paired lift run · `074` SEALED publication (`measurement.md` §6 ×7) · `015b` OpenHands arm · `075` read-only TUI | **Lift ≥ +10 pts with CI, absolute alongside, cost per resolved task** | The claim that sells and the claim that survives a model swap — both defensible |
| *post* | M5 — ⬜ *deferred by decision* | `evolution/` · meta-loop · self-redesign (ADR-0006/0014/0017) | Topology/role mutations proposed by machine, admitted by statistics + human | The harness improves its own loop within a grant that cannot widen |

---

## Sprint 1 — Foundations and the Enforcement Migration ✅

**What it was.** The layer everything else stands on: nine pure Pydantic domain models with
zero I/O, nine wire-serializable port `Protocol`s, the TCB dispatch choke point, and the
manifest-driven repo cache that unblocked B1.

**Why the order mattered.** `TASK-000` was mandated as the **first PR** — moving the
`.importlinter` and CI `TCB_PATHS` constants from `src/sagiha/` to `src/aether/` *in the same
change as the first `src/aether/` file*. [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
names the trap explicitly: land the migration one commit late and the contract selects zero
modules, forbids nothing, and reports green. That trap recurs — Sprint 5's ADR-0018 inherits
it verbatim.

**How it shapes everything after.** `WorkflowStep[In, Out]`'s socket types (`TASK-004`) are why
`validator.check_socket_compatibility` can verify a graph **statically, from an injected socket
map, without importing node classes**. That indirection is what makes topologies data rather
than code. And I3's wire-serializability — every method `async`, no `Path`, no live object — is
the property [`proposal_abstraction_and_harness_composition.md`](../fixes/proposal_abstraction_and_harness_composition.md)
§5 identifies as making a Rust or Go sidecar a `composition.py` line change rather than a
rewrite. It was nearly free on day one and would have been impossible to retrofit.

---

## Sprint 2 — Real Adapters and the Walking Skeleton ✅

**What it was.** The first end-to-end run. `retrieve → generate → apply → evaluate` executing
from a schema-validated topology, through real adapters, with every effect passing
`kernel/dispatch.py`.

**The two pieces that carry the most future weight:**

- **`ResourceGovernor`'s reserve/commit/release triple** (`TASK-034`). The dispatcher refuses
  any effect without a live lease, which makes after-the-fact accounting *structurally
  unrepresentable* rather than merely discouraged. That property is why Sprint 8's Best-of-N
  fan-out can carve N child leases from one parent reservation and have cancellation be
  correct — and it is why the Kimi-style background-task pattern was
  [evaluated and refused](../fixes/proposal_competitors_execution_mechanics_evaluation.md): a
  process outliving its lease reports actuals after `release()`.
- **The event bus with two drop policies** (`TASK-022`). `"never"` for the trajectory store and
  the measurement harvester, `"drop_oldest"` for display. *Losing a rendering frame is
  acceptable, losing a step is not.* Sprint 10's TUI and `TASK-063`'s live log telemetry both
  ride that split — and both must ride the lossy side, or replay stops being deterministic.

**The `--force` flag that does not exist.** The validator refuses any topology failing a static
check, full stop. Five checks, each with a malformed fixture proving it can fail. Every later
schema extension inherits that bar.

---

## Sprint 3 — The Repair Edge and the Instrument ✅ *(floor deferred)*

**What it was.** `vision.md` §2 calls the repair edge *"the single largest lever on score in the
entire system"*, and this sprint shipped it — statically unrolled to `max_iterations`, so the
graph stays acyclic **by construction** rather than by a runtime termination argument.

**Three constraints that are worth re-reading before touching the loop:**

1. A `GateStatus.NONE` **never** routes into repair. An instrument failure is not a repair
   candidate; repairing against one teaches the loop to fix *our* bugs instead of the task's,
   and every iteration it burned would look like ordinary work.
2. Each iteration reserves its **own** budget; exhausting it ends the loop, not the run.
3. Test output enters context tail-biased through `measurement/evaluator.py::tail_biased` — the
   same truncation the gate reported under, so the prompt and the gate can never disagree about
   what the failure was.

**Also landed:** the containerized evaluator with a green B3 canary (the `.pth` leak was the one
instrument defect that *produced numbers*), the pinned 84-task manifest with bidirectional
validity screening, and the statistics engine whose derived-N simulation reproduces ADR-0003's
published table in all twelve cells.

**What did not land: the floor run itself.** Deferred by decision — the arms cost real spend.
That deferral is what Sprint 4 pays.

---

## Sprint 3.5 — Inner-Loop Context Lift ✅ *(the cautionary one)*

**What it was.** An unplanned sprint that raised the win rate on local models: a system-message
layer, the swappable `EditFormat` seam, the node registry keyed by *kind* (which is what makes
two `generate` nodes legal in one topology), repair re-reading the worktree, and the
architect/reflector nodes.

**Every one of those mechanisms is real and stays.** The registry-by-kind change alone is what
lets Sprint 5 map four node kinds onto one `ModelNode` class.

**What it also did.** It optimised the inner loop on an instrument whose validity guards were
not extended in the same change. Two reproducible consequences:

- `grep -rn "tests_unmodified" src/aether/` → **nothing**. I7 has no enforcement in this tree.
- `scripts/run_local_check.py` injects the full text of `run_tests.py` into the prompt, so the
  harness measures **assertion-fitting**, not bug-fixing.

A live trajectory shows it plainly: on `internal__clamp_low-046` the model emitted `return b`,
satisfied `assert f(6, 9) == 9`, and the gate had no capability that could object.

**The lesson, now a standing house rule:** *a mechanism that raises the win rate must extend the
validity guards in the same change.* Sprint 3.5 is also the only sprint that shipped without a
plan document, which is exactly how the debt went unrecorded until an audit found it.

---

## Sprint 4 — Instrument Restoration and the Floor 📋

> Plan: [`sprint-04.md`](./sprints/sprint-04.md) · Developer prompt: [`sprint-04-dev-prompt.md`](./sprints/sprint-04-dev-prompt.md)

**The goal.** Pay Sprint 3.5's debt, get CI green at step one, and **take the A/A variance
floor** — the run Sprint 3 scoped and deferred.

**Tasks.** `TASK-049` (I7 `tests_unmodified` + delete the `.py`-token inferrer) · `TASK-049b`
(demote test-source injection to a named ablation flag) · CI and doc honesty · `TASK-050/051/052`
(mechanical decoupling) · `TASK-062` (non-interactive subprocess hardening) · **the floor run**.

**The cascade nobody would guess.** `TASK-049` needs a manifest field that does not exist —
the schema records `test_command_hash` but nothing identifying test *files*. Adding
`test_paths` means a **new manifest hash**, and `families/aa_floor_smoke_01.yaml` pins
`manifest_hash: sha256:7c2c2467…`, so **the gate family must be re-registered before any arm
runs**. Miss it and the floor dies at the gatekeeper.

**Why every task here blocks the floor.** Each is a way the measurement lies:

| Task | If skipped |
| :--- | :--- |
| `049` | The generator can edit its own judge; every resolve rate is unfalsifiable |
| `049b` | We measure whether a model can satisfy an assertion it was shown |
| `062` | A hung tool call → timeout → `NONE` → **excluded from the denominator**. N shrinks *non-randomly*: repositories that prompt get systematically dropped, invisibly |

**What it unlocks.** p₀₁/p₁₀ discordance sizes every future admission run. Per-task wall-clock
sizes M2-abl — currently the only unsized item in `roadmap.md`. Until this lands,
[ADR-0002](../decisions/0002-no-number-before-the-floor.md) means the project publishes no
capability number at all.

**Read a wide floor correctly:** it is a measurement, not a failure. It changes N. And an A/A
run producing a *significant* result is a **bug report about the harness** — two identical
configurations disagreeing systematically means something is not identical.

---

## Sprint 5 — The Capability Layer 📋

> Plan: [`sprint-05.md`](./sprints/sprint-05.md) · Design: [`proposal_abstraction_and_harness_composition.md`](../fixes/proposal_abstraction_and_harness_composition.md)

**The goal.** Insert the missing layer between *topology (data)* and *dispatch facade*. Today a
node is the only unit of reuse, and a node is a 60–150 line class that inlines five concerns at
once: context gathering, span labelling, prompt assembly, model invocation, and payload
plumbing.

```
  TOPOLOGY (data)   ── YAML, composition of nodes ── unchanged
  NODE (thin)       ── ~20 lines: wire capabilities ── NEW SHAPE
  CAPABILITY (code) ── ContextSource · PromptAssembler · Inference · OutputParser ── NEW
  DISPATCH FACADE   ── the choke point ── unchanged
```

**What a role becomes.** `ARCHITECT`, `EDITOR`, `REPAIRER` and `REFLECTOR` stop being classes
and become **data**: a source list, a parser, a role string.

```python
REPAIRER = RoleSpec(
    role=EDITOR_SYSTEM_ROLE,
    sources=(InstructionsSource(), PlanSource(), CurrentFileSource(),
             PreviousAttemptSource(), GateOutputSource(tail=3000)),
    parser=EditFormatParser("whole_file_codeblock"),
)
```

**The architect and the editor differ by their source list and their parser, and by nothing
else.** ~350 lines across three files become ~90 lines of node plus ~40 of role declaration.

**Four structural decisions that are easy to get wrong:**

| Decision | Why |
| :--- | :--- |
| **Node *kinds* stay distinct** | `NODE_SOCKETS` is keyed by `kind` and the validator resolves sockets by kind alone. `kind: model` + `params.role` would collapse architect/generate/repair into one socket pair, and theirs differ. One `ModelNode` class, four factories, zero validator change |
| **Nodes stay in `workflow/nodes/`** | `WorkflowStep` lives in `workflow/step.py`; a node under `agency/` importing it is an upward import |
| **`EffectDispatch` is a structural Protocol defined where consumed** | Exactly the `SandboxRunner` precedent — *"Not a port; a structural collaborator."* Structural typing means neither module imports the other. No new port, no ADR |
| **ADR-0018 lands with the first `agency/` file** | Sprint 1's trap again: a contract selecting zero modules passes green |

**Provenance stops being ad hoc.** A `ContextSource` returns `ContextBlock`s, and **a block's
label is a property of its source, declared once** — replacing ten hand-built `TaintSpan(...)`
call sites across three files. That is how repository content and test tracebacks both came to
be labelled `AGENT`, and it makes `TASK-048`'s ask a side effect of the refactor.

**What it unlocks.** `TreeSitterIndexer` — a conformance-passing adapter reachable by *nothing*
today — gets a seam. `ToolLoop` becomes usable by any role, so a planner can finally `ls` the
repo. `RunConfig` makes `sha256(config)` the instrument tuple and lets the engine **refuse a
HOLDOUT run while the floor is empty**. And `agency/context/` finally exists, which is what M2
is blocked on.

---

## Sprint 6 — Memoization and Targeted Retrieval ⬜ *projection*

**The goal.** Make ablations cheap to run, and teach the harness which files to open.

**`TASK-032` memoization** keys node execution on `sha256(node_kind, impl_version, canonical
payload)` and must invalidate **exactly** the descendants of a changed node — over-eager
invalidation defeats the purpose, under-eager silently reuses stale results *inside a benchmark
run*. Paired with `TASK-006`'s cassettes (100 turns under 50 ms, no API call, byte-deterministic
replay), this is what makes Sprint 7 affordable rather than aspirational.

**`TASK-064` localization is the sleeper.** `RetrieveStep` reads the files a node's YAML
*names*. `Task` carries no file list. The only discovery mechanism globs every `.py` under a
task directory — fine for 84 synthetic tasks, and on django or sympy it returns the whole
repository, after which `max_bytes` truncates **alphabetically**. `STATUS.md` says SWE-bench is
blocked on per-instance images; that is true and incomplete. **With every image built, the
harness still has no way to choose which files to open.**

Four `ContextSource` implementations, no new architecture: lexical (identifiers and tracebacks
from the issue → grep), symbol (`TreeSitterIndexer`), test-path (failing test's imports), and
git history (`log -S<identifier>`). Deterministic and seeded, because a retrieval set that
varies run to run makes reproducibility unsatisfiable.

**It is also the biggest token win.** Exploring a repo by having the model issue `grep`/`ls`
costs a round trip per step and re-enters every result into context. A deterministic
pre-model step costs **zero inference tokens** and produces a smaller prompt — the one place
where best score and fewest tokens point the same way.

`TASK-068` closes a related gap: `ArchitectStep` is read-only because it *happens* not to call
`dispatch.write`. Under [ADR-0017](../decisions/0017-subagent-capability-attenuation.md) a
`RoleSpec` declares its `effect_class` set and gets an attenuated facade at construction — so
`ARCHITECT` is `{read, model}` **by type**, denied at the choke point rather than trusted.

---

## Sprint 7 — The Ablations ⬜ *projection, genuinely unsized*

**The goal.** Find out which of our own ideas actually work.

Four arms, repair first because it is the largest expected effect: **repair-on vs repair-off**,
generated context vs a hand-authored brief of equal token budget, the Architect/Editor dual-model
seam, and compaction. Each runs at derived N on the HOLDOUT split under Holm–Bonferroni across a
**pre-declared** family.

**The rule that makes this sprint honest:** a mechanism that does not clear the floor is
**deleted, not left dormant**. `TASK-025`'s own note — *"a disabled code path nobody measures is
debt, not optionality"* — and [ADR-0010](../decisions/0010-context-prefix-layers.md) says the
same for the context layer. This sprint can legitimately end with the codebase *smaller*.

**Why it cannot be sized.** Wall-clock is `derived_N × tasks × arms × per-task time`. Two of
those three multiplicands are outputs of Sprint 4. Naming a duration now would be the
estimate-as-commitment ADR-0009 forbids.

**What lands alongside:** `TASK-056` (the five-layer assembler) carries the I10 gate — **harness-side
byte-identical-prefix stability over a fixed replay**, deliberately not a provider hit rate,
since OpenAI-compatible endpoints cache implicitly and the local endpoint may report nothing.
`TASK-024` compaction is scoped to L5 only; the assembler exposes no API to touch L1–L4, so
that guarantee is type-level rather than enforced by care.

---

## Sprint 8 — Branching, Fan-Out and Selection ⬜ *projection*

**The goal.** Parallel candidates as real graph structure, and the selector that makes them
worth paying for.

**`TASK-035`** adds conditional edges (`on_pass` / `on_fail` / `on_instrument_error`, the last
routing only to a terminal flag node) and declared Best-of-N fan-out. Every fan-out site needs a
declared join — **unjoined fan-out leaks worktrees and leases** — and N candidates carve N child
leases from one parent reservation, which is where Sprint 2's refund-to-parent semantics finally
earn their keep.

**`TASK-067` is the one that converts cost into score.** `workflow_schema.yaml` already declares
`rank_by` with I9 written into it — *rankers ORDER candidates and may never ADMIT one* — and
there is no ranker. Best-of-N without one is an N× cost multiplier that takes the first-pass
candidate. The proposed selector runs the repository's **visible** test suite against each
candidate and ranks by pass count: zero inference tokens, because it is execution rather than
generation.

**The trap, and it is subtle:** if the visible suite includes the gate's tests, the ranker
becomes a shadow evaluator and the harness selects on the answer. The manifest must record the
visible/hidden partition per task, and a task where they cannot be separated is **excluded with
a published reason**. The gate stays the sole admitter — I9 is currently enforced by nothing
(`grep "def rank\|def admit"` → empty), so the type-level separation is built here, with its
first user.

**`TASK-059` and `TASK-060` complete the composition story.** Strategies turn the executor from
a switch statement over loop kinds into a dispatcher, so the escalating rescue cascade becomes
expressible:

```yaml
repair:
  strategy: cascade
  max_iterations: 3
  per_iteration:
    - { model: "qwen2.5-coder:7b" }      # free
    - { model: "qwen2.5-coder:7b" }      # free
    - { model: "deepseek/deepseek-v4" }  # paid rescue — only ~20% of tasks reach here
```

Fragments give the data layer a composition operator, so `apply → evaluate → repair×k` is
written once and `use:`d everywhere instead of copy-pasted across seven files. **Expansion
happens before validation**, so all five static checks run on the fully expanded graph and a
fragment cannot smuggle a node past the judge. Both are TCB or TCB-adjacent and need human
review.

---

## Sprint 9 — Benchmark Delivery ⬜ *(unfunded today)*

**The goal.** Point the whole machine at the actual target.

**This phase currently has no milestone, no gate and no task** — see
[`coverage_audit.md`](./coverage_audit.md) G1. `milestones.md` ends at M3, and the gate-coverage
map checks *milestone gate → task*, so a mission that is not a milestone is invisible to the
check. That is the D15 defect class one level up.

**`TASK-071` — the SWE-bench manifest.** `TASK-014`'s tooling is generic and already built;
what is missing is running it at scale. Every task enters only if **the gold patch passes and
the empty patch fails on our instrument**, and every exclusion is published with a typed reason.
Expect a real exclusion list — roughly 30% of public Pro tasks were estimated broken in a
mid-2026 audit — so this is triage at scale, not clean-room logic.

**`TASK-072` — a second A/A floor, on that manifest.** Sprint 4's floor runs against 84
**synthetic** tasks. It is correct and necessary and **it is not the SWE-bench floor**: its
discordance rates do not transfer to a different suite with different repositories, different
test runners and different flakiness. Every SWE-bench admission needs N derived from SWE-bench's
own p₀₁/p₁₀.

**`TASK-042`–`045` — routing, and honest money.** The committed
`hybrid_architect_editor_v1.yaml` cannot run: `params.base_url` is dropped by the architect
factory, and one provider is built for the whole run. Worse, a fix for that alone leaves pricing
keyed to the *run's* base URL, so the arm would run, work, and report **$0.00 for real DeepSeek
charges** — passing ADR-0003's cost non-inferiority check *vacuously*. `TASK-043` is what makes
"the architect node costs at most $0.05" a fact rather than a comment.

---

## Sprint 10 — Publication ⬜ *(unfunded today)*

**The goal.** The two numbers `vision.md` §1 commits to, both defensible.

**`TASK-073` — the paired lift run.** Lift is only as defensible as the arm it is measured
against, and *"a bare model call"* admits a family of baselines — a weak one manufactures the
lift. So the baseline is pre-registered: one completion, official SWE-bench inference template
with the **template hash recorded**, no execution feedback, no retrieval beyond
benchmark-provided context, temperature and seed pinned, **identical model fingerprint** to the
harness arm.

**`TASK-074` — publication on SEALED**, satisfying all seven of `measurement.md` §6: blockers
closed, floor published, family declared *before any arm ran*, N derived for ≥0.80 power, the
effect clearing the floor under Holm–Bonferroni, cost per resolved task non-inferior within the
declared margin, lift reported alongside the absolute, and the run naming its full instrument
tuple.

**`TASK-015b` — the OpenHands arm.** The mission is to beat other harnesses, and
[`spec.md` §9](../spec.md#9-standing-rules) forbids citing their published numbers as evidence.
**Until this runs through our evaluator, the competitive claim is unsubstantiable by
construction** — same model, same manifest, same judge is the only apples-to-apples comparison
available in this space.

**`TASK-075` — a read-only TUI**, and the reason it is here rather than earlier: `spec.md` §8 is
titled *Clients*, §3 declares `tui/`, `vision.md`'s diagram shows three of them, and the backlog
has **zero client tasks**. Read-only keeps it out of the authority question entirely — a client
with no privileged access is §8's own requirement — and it is what makes `TASK-058`'s
"forms generate from `model_json_schema()`" and `TASK-063`'s live telemetry demonstrable rather
than asserted.

---

## Post-M4 — Evolution and the Meta-Loop ⬜ *deferred by decision*

Four ratified ADRs describe machinery with no task:
[ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md) (the meta-loop's mutable
surface), [ADR-0014](../decisions/0014-workflow-topology-is-data.md) (whose *stated rationale*
is that without topology-as-data the only path to self-redesign runs through arbitrary code
modification), [ADR-0017](../decisions/0017-subagent-capability-attenuation.md), and
`spec.md` §3's `evolution/` package. `.importlinter` already names `aether.evolution` as a
forbidden importer — a contract target that does not exist, and therefore currently vacuous.

**What Sprints 5–8 buy it** is the missing rungs of the autonomy ladder:

```
  rung 4  ┃ new capability implementation      ┃ CODE   ┃ human PR, TCB review
  rung 3  ┃ new role (source list + parser)    ┃ DATA   ┃ Sprint 5   ← new
  rung 2  ┃ new topology (node composition)    ┃ DATA   ┃ exists (ADR-0014)
  rung 1  ┃ new prompt / retrieval params      ┃ DATA   ┃ exists (ADR-0006)
  rung 0  ┃ new arm (routing + manifest + seed)┃ DATA   ┃ Sprint 9   ← new
```

**The safety property that must hold across all of it:** rungs 0–3 are data, and **data cannot
widen capability**. A role file *names* a `ContextSource` by registered id; it cannot define
one. A topology *names* a strategy; it cannot define one. The registries are frozen at
composition (I6). That is what keeps the meta-loop's grant small enough to be safe.

---

## How to read this plan

- **Sprints 1–5 are real.** 1–3.5 shipped; 4 and 5 have written plans and developer prompts.
- **Sprints 6–10 are ordering and content, not dates.** The dependency edges binding them live
  in [`roadmap.md`](./roadmap.md), which is `normative`. This file is `rationale` and binds
  nothing.
- **Two phases are unfunded** (9 and 10) and one is deliberately deferred (M5). See
  [`coverage_audit.md`](./coverage_audit.md) for the full gap list and the tasks that would
  close it.
- **The gate is the schedule.** A phase ends when its exit gates pass in CI, not when its
  tripwire elapses. A tripwire exceeded by >50% triggers a scope review — **gates are never
  skipped or lowered** ([ADR-0009](../decisions/0009-gates-are-the-schedule.md)).
