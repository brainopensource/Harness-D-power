---
status: rationale
updated: 2026-08-07
---

# Proposal: Hybrid Workflow Topologies — Per-Node Model Routing, Honest Hybrid Economics, and the Ablation That Admits Them

**Status: proposal. Nothing here is decided.** A proposal becomes a decision only through
an ADR with a reversal condition ([`spec.md` §9](../spec.md#9-standing-rules)). Every cost
figure below is a **projection at list price**, not a measurement, and is marked as such.

This document supersedes an earlier sketch of the hybrid idea (`proposal_workflows_S3-5_meta.md`,
since deleted — its cost claims did not survive the code read below). It differs in one respect: before proposing the topologies, it
reports **what a line-level read of the tree says about whether they can run at all.** The
answer is that the hybrid topology already sitting in `workflows/` cannot, for six separate
reasons, and five of them are invisible at runtime — they degrade to a wrong number rather
than an error.

---

## 1. The thesis, and why it is a topology question

[ADR-0014](../decisions/0014-workflow-topology-is-data.md) says topologies are data. The
consequence nobody has cashed in yet: **which model runs which node is a property of the
graph, not of the run.** A plan is 50 output tokens of hard reasoning; an edit is 2,000 output
tokens of easy transcription. Paying frontier rates for the second to get the first is the
single largest avoidable cost in the system, and the seam that fixes it —
[ADR-0007](../decisions/0007-architect-editor-seam.md)'s Architect/Editor split — already
exists as `ArchitectStep`.

The hybrid family this proposes:

```
                    WHAT A HYBRID TOPOLOGY BUYS

  role          node        model class         tokens/call    why this class
  ────────────  ──────────  ──────────────────  ─────────────  ───────────────────
  planner       architect   frontier (paid)     ~150 in/50 out reasoning density
  editor        generate    local (free)        ~3k in/1k out  transcription volume
  rescue        repair(k=3) frontier (paid)     ~800 in/300 out only on 2× local fail
  reflector     reflector   local (free)        ~500 in/100 out lesson extraction

  Design target: ≥80% of tasks never reach a paid node.
```

**This is not a new mechanism.** It is a routing parameter over nodes that already exist. That
matters for [`spec.md` §7](../spec.md#7-measurement): it is one ablation arm, not a milestone.

---

## 2. Blocking findings — `hybrid_architect_editor_v1.yaml` cannot run today

The file landed in commit `23cd1b4` ("added inner loops, repais, arhitect, docs and tests"),
validates against the schema, and is named in no document. It declares:

```yaml
- { id: architect, kind: architect,
    params: { model: "deepseek/deepseek-chat",
              base_url: "https://openrouter.ai/api/v1",
              max_tokens: 512 },
    budget: { usd_micros: 50000, prompt_tokens: 10000, completion_tokens: 512 } }
```

Six defects, each verified against the tree:

| # | Defect | Evidence | Failure mode |
| :--- | :--- | :--- | :--- |
| **H1** | `params.base_url` is silently dropped | `engine.py:112-117` — the `architect` factory reads `model` and `max_tokens` only. `engine.py:178` builds **one** `OpenAICompatibleProvider` for the whole run | `deepseek/deepseek-chat` is POSTed to `127.0.0.1:11434`. Ollama 404s → `WorkflowExecutionError` → `run_local_check.py:143` maps it to `GateStatus.NONE`. **The hybrid arm reports instrument errors, not results** |
| **H2** | Pricing is keyed to the *run's* base URL, not the node's | `pricing.py:71-73` short-circuits on `is_free_endpoint(base_url)`; `composition.py:124` passes the single run-level `model_base_url` | Once H1 is fixed, every paid call still prices at `PRICES["local"]` = **$0.00**. A hybrid run would report zero spend for real DeepSeek charges |
| **H3** | The model named is not on the rate card | `pricing.py:40-52` carries `deepseek/deepseek-v4-flash`; the topology says `deepseek/deepseek-chat` | Falls to `UNKNOWN_PRICE` ($10/$30 per Mtok) — correct-by-design, but only if H2 does not beat it to the answer first |
| **H4** | Per-node `usd_micros` is decorative | `executor.py:174` reserves the node budget; `executor.py:194` releases it with **no commit** — the comment says so: *"M1a: node-level gate only; effect actuals commit inside dispatch()"* | A node may spend arbitrarily more than its declared budget. Hybrid economics rest entirely on "the architect node costs at most $0.05," and nothing enforces that |
| **H5** | Reserve-time cost estimates carry `usd_micros=0` | `generate.py:146`, `repair.py:180`, `architect.py:88` all reserve `BudgetDims(prompt_tokens=max_tokens)`. `priced()` fills the dollar figure only at commit (`composition.py:120-124`) | The run ceiling is checked at reserve against zero. An overrun is detected on the *next* reserve — after-the-fact accounting in the one dimension [`spec.md` §5](../spec.md#5-execution) exists to make unrepresentable |
| **H6** | `reflector` is unreachable | `grep -rn reflector workflows/ tests/` → nothing. `ReflectorStep` is registered at `engine.py:119-124` and used by no topology and no test | The reflection half of the hybrid loop does not exist as a running thing |

A seventh constraint is not a defect but bounds the design: **there are no conditional edges.**
`_topological_order` (`executor.py:96`) walks a single linear chain, and `when: on_pass |
on_fail` is [TASK-035](../agile/backlog.md), scheduled for M3. The escalating cascade in
the escalating cascade is **not expressible in a valid topology today**.

**H1 and H2 compose into the worst case in the set.** H1 makes the hybrid arm fail as an
instrument error; a plausible fix for H1 alone leaves H2 standing, and then the arm runs, works,
and reports **$0.00 spend**. Cost per resolved task is a mandatory admission column
([ADR-0003](../decisions/0003-statistical-admission-protocol.md) rev. 2). An arm that reports
zero cost does not fail the non-inferiority check — it passes it vacuously, which is the same
defect class as a contract that selects no files.

---

## 3. Prerequisites from outside this proposal

Two audit findings must land before any hybrid arm is *measured*, because they affect the
instrument rather than the topology. Building the routing below can proceed in parallel;
running an ablation over it cannot.

1. **I7 has no enforcement in `src/aether/`.** `grep -rn "tests_unmodified" src/aether/`
   returns nothing, while [`spec.md` §2](../spec.md#2-invariants) names it as I7's mechanism.
   The unlabelled-fence inferrer at `edit_format.py:198-202` selects the first `.py` token in
   the model's prose, and writes there — reproducibly including `run_tests.py`. `ApplyStep`
   (`apply.py:88`) and `DispatchFacade.write` (`dispatch_facade.py:65`, no `justifying_spans`,
   no `widens_capability`) both pass it through.
2. **`run_local_check.py:47-56` injects the full text of `run_tests.py` into the prompt.**
   That measures assertion-fitting, not bug-fixing — `internal__clamp_low-046` emitting
   `return b` to satisfy `assert f(6, 9) == 9` is the mode in action. It also breaks
   [`measurement.md` §4.1](../measurement.md#41-the-baseline-is-part-of-the-instrument)'s
   pre-registered baseline ("no retrieval beyond benchmark-provided context").

A hybrid ablation run over that instrument produces a number that has to be discarded, which
is the exact sequence [ADR-0002](../decisions/0002-no-number-before-the-floor.md) is a
post-mortem of.

---

## 4. Proposed work, in dependency order

Written in [`backlog.md`](../agile/backlog.md) form so these can be lifted into it if ratified.
Complexity uses the backlog's 0–5 scale.

### TASK-042: `RoutingModelProvider` — per-node endpoint and credential routing · **3 · Medium**

* **Description**: A `ModelProvider` composite that selects a concrete provider per
  `ModelRequest.model`, so one run can reach a local endpoint and a paid endpoint from
  different nodes. The name is already in the tree as an unbuilt promise —
  `openai_compatible.py:79-80` says *"One adapter per OpenAI-compatible endpoint (a
  `RoutingModelProvider` composite handles multi-model roles, ADR-0007)"*.
* **Target files**: `src/aether/adapters/model_provider/routing.py`, `engine.py`,
  `composition.py`
* **Normative specs**: [ADR-0005](../decisions/0005-eight-ports-adapter-first.md) (second
  adapter of an existing port, not a new port), [ADR-0007](../decisions/0007-architect-editor-seam.md),
  [`spec.md` §2 (I6)](../spec.md#2-invariants)
* **Exit criteria**: Passes the existing `ModelProvider` conformance suite unmodified. Routes
  are **frozen at composition** (I6) — a topology naming an unrouted endpoint raises at load,
  not at the node's turn, matching `UnregisteredNodeKind`'s precedent (`executor.py:130-136`).
  API keys are resolved from the environment at composition and **never appear in a topology
  file**. A negative test proves an unknown route raises.

### TASK-043: Node-scoped pricing · **2 · Easy**

* **Description**: Price a call against the endpoint that served it, not against the run's
  default. `priced()` already takes `base_url`; the caller passes the wrong one.
* **Target files**: `src/aether/measurement/pricing.py`, `src/aether/composition.py`
* **Normative specs**: [ADR-0003 rev. 2](../decisions/0003-statistical-admission-protocol.md) §4
  (cost per resolved task is a mandatory column)
* **Exit criteria**: A run mixing a localhost node and a paid node reports **non-zero**
  `usd_micros`, and the local node contributes zero. **Negative test required**: a paid call
  mispriced as local must make the test fail — this is the H2 defect, and a gate that cannot
  fail is not a gate ([`measurement.md` §5](../measurement.md#5-gate-design)).
* **Also**: add `deepseek/deepseek-chat` to `PRICES` from the provider's rate card, or delete
  it from every topology. `UNKNOWN_PRICE` is the correct fallback and should not be load-bearing.

### TASK-044: Reserve the dollar estimate, not zero · **2 · Easy**

* **Description**: Nodes reserve `priced(model, BudgetDims(prompt_tokens=…, completion_tokens=…))`
  so `usd_micros` is non-zero **before** the call, and the run ceiling refuses the effect rather
  than noticing it afterwards.
* **Target files**: `src/aether/workflow/nodes/{generate,repair,architect}.py`
* **Normative specs**: [`spec.md` §5](../spec.md#5-execution) (reserve before execution)
* **Exit criteria**: A run seeded below the cost of its first call is denied **at that call**,
  not at the second. Fixes a second latent bug in the same line: `max_tokens` is a *completion*
  ceiling currently reserved as `prompt_tokens`, so a 30k-token prompt reserves 1,024.

### TASK-045: Enforce the per-node budget · **3 · Medium**

* **Description**: Make the topology's per-node `budget` a real cap. Today `_run_node` reserves
  and releases without committing (`executor.py:174`, `executor.py:194`), so the declared figure
  constrains nothing. Effect leases taken inside the node should be **children of the node lease**
  — the parent/child refund semantics already exist (`reserve(..., parent=...)`, and
  [TASK-034](../agile/backlog.md)'s "a child lease's release refunds the parent, not the global
  pool").
* **Target files**: `src/aether/workflow/executor.py`, `src/aether/workflow/dispatch_facade.py`
* **Normative specs**: [`spec.md` §5](../spec.md#5-execution), [ADR-0014](../decisions/0014-workflow-topology-is-data.md)
* **Exit criteria**: A node whose effects exceed its declared budget is **denied at the choke
  point**, and the denial names the node. A topology can bound its own paid node without
  bounding the run. **This is what makes "the architect node costs at most $0.05" a fact
  rather than a comment**, and every projection in §6 depends on it.
* **Note**: This touches `workflow/executor.py`, which [`spec.md` §6](../spec.md#6-trusted-computing-base)
  declares TCB. It needs human review and cannot be a meta-loop auto-commit
  ([ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)).

### TASK-046: Wire `reflector`, or delete it · **1 · Very Easy**

* **Description**: `ReflectorStep` is registered and unreachable. Either a shipped topology uses
  it with a test, or it comes out.
* **Normative specs**: [TASK-025](../agile/backlog.md)'s own rule — *"a disabled code path
  nobody measures is debt, not optionality"*
* **Exit criteria**: One of: a topology exercising `reflector` end-to-end with a test, or the
  node and its `NODE_SOCKETS` entry deleted. **Not both, and not neither.**

### TASK-047: Tests for `ArchitectStep` and `ReflectorStep` · **2 · Easy**

* **Description**: Sprint 3.5's two new nodes ship with zero tests —
  `grep -rn "ArchitectStep\|ReflectorStep" tests/` returns nothing. Commit `23cd1b4`'s message
  claims "docs and tests"; its 17-file diff contains **no test file**. Worth stating plainly
  because the claim is in the permanent record and the code is not.
* **Exit criteria**: Socket-type conformance, budget reservation, and prompt assembly covered.
  Specifically: **a test that the architect's plan reaches the generate node's prompt**, which
  is the entire mechanism and is currently unasserted.

### TASK-048: Provenance for planner output · **3 · Medium** *(design first)*

* **Description**: `ArchitectStep` concatenates model output into `payload.instructions`
  (`architect.py:92-96`); `ReflectorStep` does the same into `task.instructions`
  (`architect.py:145-152`). The next node labels `instructions` as `Provenance.OPERATOR`
  (`generate.py:97`). Planner output derived from repository files and test tracebacks
  therefore acquires operator provenance in two hops.
* **Normative specs**: [`spec.md` §5](../spec.md#5-execution),
  [ADR-0015](../decisions/0015-taintgate-provenance-model.md), [`spec.md` §2 (I11)](../spec.md#2-invariants)
* **Why it is design-first**: labelling repository content `untrusted-external` as
  [`spec.md` §5](../spec.md#5-execution) requires would make `DefaultPolicyEngine`
  (`policy.py:18`) fail closed on **every** shell tool call, since `dispatch_facade.py:87`
  marks shell effects `widens_capability=True` and `generate.py:187` justifies them with the
  file spans. The current `Provenance.AGENT` labelling is what keeps the tool loop working.
  That is a defensible sequencing choice pending [TASK-030a](../agile/backlog.md)'s escalation
  taxonomy — but it is **not currently recorded** in `STATUS.md`'s deviations section, and it
  should be, because I11 presently reads as enforced.
* **Minimum for this proposal**: hybrid topologies must not *widen* the gap. A planner span
  should carry its own label rather than being merged into an `OPERATOR`-labelled string.

---

## 5. The proposed topology family

Each entry names the tasks it is blocked on. **None of these should be run as a measured arm
before §3's prerequisites land.**

| Topology | Shape | Purpose | Blocked on |
| :--- | :--- | :--- | :--- |
| `hybrid_architect_editor_v1` *(exists, non-functional)* | frontier `architect` → local `generate/repair` | Buy reasoning density at the one node that needs it | TASK-042, 043, 044, 045 |
| `hybrid_rescue_v1` | local `generate` → local `repair` ×2 → **frontier** `repair` on iteration 3 | Pay only for tasks local models cannot close | TASK-042/043/045 **+ per-iteration model override in the `repair` block** |
| `decomposed_planning_v2` | `retrieve → architect → generate → apply → evaluate → reflector` | The topology `implemented_sprint_3.5_complete_report.md` §3.6 *describes*; the shipped v1 has no reflector node or edge | TASK-046, 047 |
| `cascade_repair_v1` | conditional escalation on `on_fail` | The full cascade from the S3-5 proposal | **TASK-035 (M3)** — not expressible today |

**The rescue topology needs one schema change**, and it is the only schema change proposed
here: `repair.via_nodes` currently resolves to a single step instance shared by every unrolled
iteration (`executor.py:156-159` builds one step per *node id*). Escalating on iteration 3
means the repair block must accept a per-iteration model override. That is a topology-schema
edit, so it is TCB (`spec.md` §6) and needs its own validator check and malformed fixture —
`TASK-020`'s exit criterion is that every static check has a fixture proving it can fail, and
a new field inherits that bar.

---

## 6. Projected economics — and why they are projections

**No hybrid arm has ever been run.** The table below is arithmetic over
`pricing.py`'s rate card, not a measurement, and per
[`spec.md` §9](../spec.md#9-standing-rules) it may bound a design and motivate an ablation —
nothing more.

Assumptions, stated so they can be falsified: 80% of tasks resolve without reaching a paid
node; a plan is ~150 prompt / ~50 completion tokens; a rescue turn is ~800 / ~300; rates are
`deepseek/deepseek-v4-flash` at 270,000 / 1,100,000 µUSD per Mtok.

| Arm | Paid calls per 100 tasks | Projected spend / 100 tasks | Note |
| :--- | :---: | :---: | :--- |
| All-local (`decomposed_planning_v1`) | 0 | **$0.0000** | Measured as $0.00 today — but see H2: it would report $0.00 either way |
| `hybrid_architect_editor_v1` | 100 planner | **$0.0095** | One plan per task |
| `hybrid_rescue_v1` | ~20 rescue | **$0.0109** | Rescue only, no planner |
| Both | 100 + ~20 | **$0.0204** | |
| All-frontier (every node) | ~400 | **~$1.32** | The arm hybrids exist to avoid |

The projected ratio — roughly **65× cheaper than all-frontier at the same node count** — is the
hypothesis. Whether it holds depends on the 80% local-resolve assumption, which is exactly the
quantity no valid measurement exists for yet. **If the local resolve rate is 40% rather than
80%, the rescue arm's cost triples and the case weakens sharply.** That sensitivity is the
reason this is an ablation and not a decision.

---

## 7. How these get admitted without repeating the last breach

[ADR-0002](../decisions/0002-no-number-before-the-floor.md) has **no reversal condition**. The
Sprint 3.5 report published a resolve-rate table before the floor, and
[`STATUS.md`](../STATUS.md) says in the same tree on the same date that the floor is not taken
and benchmark results are none. This proposal is bound by the same rule, so the sequence is:

1. **DEV-split smoke only** until `docs/benchmarks/results/noise-floor.md` holds a real
   number. `run_local_check.py:180` already prints the correct disclaimer —
   *"Not a benchmark: N is tiny, no family declared, nothing published"* — and it should be
   honoured by whatever reports the results, not just by the script that emits them.
2. **Declare the family before any arm runs.** A committed YAML under
   `measurement/families/`, merged first; `statistics.py` refuses corrected p-values for an
   undeclared family. Proposed hypotheses: *hybrid-planner vs all-local*, *hybrid-rescue vs
   all-local*, *both vs all-local*.
3. **Derive N for ≥0.80 power** at the declared minimal effect, using the floor's discordance
   estimate. Not a fixed 50 — [`measurement.md` §3](../measurement.md#3-the-aa-variance-floor)
   shows N=50 detects a true +10-point lift in 12–32% of cases.
4. **Report cost per resolved task per arm** — which requires TASK-043, or the column is
   `$0.0000` for every arm and the non-inferiority check passes vacuously.
5. **A hybrid topology that does not clear the floor is deleted, not left dormant** —
   [TASK-025](../agile/backlog.md)'s rule, applied to topologies.

---

## 8. What this proposal does not claim

- **No lift is claimed.** No hybrid arm has run. The §6 table is arithmetic.
- **No capability claim** is made for `decomposed_planning_v1`'s 2/2 or `linear_repair_autofiles_v1`'s
  0/2. N=2, no family, and the instrument injects the test assertions (§3.2). Those runs
  establish that the wiring executes, which is worth knowing and is not a resolve rate.
- **No security claim** attaches to per-node routing. Routing changes which endpoint sees a
  prompt; the perimeter is still the sandbox ([ADR-0008](../decisions/0008-shell-ast-classifies.md)).
  Note the corollary: hybrid topologies send repository contents to a **third-party endpoint**,
  which all-local topologies do not. That is a new data-egress surface and deserves its own
  line in whatever config governs it.
- **TASK-045 touches the TCB.** It is proposed with that flagged, not smuggled.

---

## 9. Reversal conditions

- **On the hybrid thesis**: if the planner arm's lift CI includes zero at admission N *and*
  cost per resolved task is inferior beyond the declared margin, delete the hybrid topologies
  and keep `ArchitectStep` only if its all-local ablation ([TASK-025](../agile/backlog.md),
  M2 Gate 4) clears independently.
- **On per-node routing (TASK-042)**: if no admitted topology uses more than one endpoint six
  months after it lands, the composite is unearned indirection and comes out.
- **On the cascade**: if [TASK-035](../agile/backlog.md) slips past M3, `hybrid_rescue_v1`'s
  static-unroll approximation stands or the cascade is dropped — it does not become a reason
  to add conditional edges outside ADR-0013's phasing.

---

## 10. Immediate, no-decision-required items

These need no ADR; they are corrections to things that already claim to be true.

| Item | Action |
| :--- | :--- |
| `hybrid_architect_editor_v1.yaml` is committed (`23cd1b4`) and undocumented | Add a header comment naming TASK-042/043/045 as its blockers, **or** delete it. An unrunnable topology in `workflows/` will be run by someone |
| `implemented_sprint_3.5_complete_report.md` §3.6 describes a reflector edge that does not exist | Correct the sentence or ship TASK-046 |
| ~~Nine files fail the declared `status:` taxonomy~~ | **Resolved 2026-08-07.** `docs/workflows/` was consolidated into `docs/architecture_diagrams.md`, the invalid `status: proposal` file was deleted, and `docs_budget.py` now gates on its bare invocation. Exits 0 |
| `deepseek/deepseek-chat` is unpriced | Add to `PRICES` from the rate card, or stop naming it |

---

## Appendix: verification commands

Every claim above came from one of these, run on `rewrite_v310-phase-0` at 2026-08-07.

```bash
# H1 — one provider, base_url never read from params
grep -n "OpenAICompatibleProvider\|params.get" src/aether/engine.py
grep -rn "RoutingModelProvider" src/aether/     # only a docstring promise

# H2/H3 — pricing keyed to the run's base_url; rate card contents
sed -n '66,76p' src/aether/measurement/pricing.py

# H4 — node budget reserved and released, never committed
sed -n '170,196p' src/aether/workflow/executor.py

# H6 — reflector referenced by no topology and no test
grep -rn "reflector" workflows/ tests/

# no conditional edges
sed -n '96,124p' src/aether/workflow/executor.py

# every shipped topology validates (they do — that is the point)
python -c "import sys;sys.path.insert(0,'src');
from pathlib import Path
from aether.workflow.validator import load_topology, validate_topology
from aether.engine import NODE_SOCKETS
[validate_topology(load_topology(p.read_text()), NODE_SOCKETS) for p in Path('workflows').glob('*.yaml')]"
```
