---
status: rationale
updated: 2026-08-07
---

# Proposal: Abstraction, Capability Composition, and the Reusable Harness Core

**Status: proposal. Nothing here is decided.** A proposal becomes a decision only through an
ADR with a reversal condition ([`spec.md` §9](../spec.md#9-standing-rules)). This document
describes a target architecture and the mechanical path to it; it commits to no schedule and
publishes no number.

**Scope.** How to restructure `src/aether/` so that (a) capability logic is written once and
reused across nodes, (b) DAGs compose out of smaller DAGs rather than being copy-pasted, (c)
every behaviour is reachable from config so a GUI/CLI/TUI can drive it, and (d) any single
component can be replaced by a Rust or Go sidecar without a caller changing.

**Method.** Every claim about the current code is a line-level read or an executed command;
the appendix lists them. Where the current design is *correct and should not change*, this
document says so — the goal is to remove duplication, not to relitigate settled decisions.

---

## 0. Executive summary

The foundation is sound. The lattice holds (9/9 import-linter contracts), the choke point is
real, the socket types are real, and ADR-0014's "topologies are data" is genuinely implemented
— `engine.py`'s `build_step_registry()` is a working swap point. **Nothing in this proposal
requires undoing any of it.**

What is missing is one layer. Today the system has two levels of abstraction:

```
  TOPOLOGY (data)  ─────────────────────────────────────────  YAML, swappable
  ────────────────────────────────────────────────────────
  NODE (code)      ─────────────────────────────────────────  a monolithic class
  ────────────────────────────────────────────────────────
  DISPATCH FACADE  ─────────────────────────────────────────  read/write/shell/model/evaluate
```

A node is the *only* unit of reuse, and a node is a 60–150 line class that inlines everything:
prompt assembly, span labelling, model invocation, output parsing, and payload plumbing. When
`ArchitectStep` and `RepairStep` both need "call a model and collect the text", both write it.
When `RetrieveStep` and `RepairStep` both need "read these files into a prompt block", both
write it — differently, with different error semantics.

The proposal is a third level between node and facade: **capabilities**.

```
  TOPOLOGY (data)   ────────────────────────────────────────  YAML — composition of nodes
  ────────────────────────────────────────────────────────
  NODE (thin)       ────────────────────────────────────────  ~20 lines: wire capabilities
  ────────────────────────────────────────────────────────
  CAPABILITY (code) ────────────────────────────────────────  Retrieval · Prompting · Inference
  ────────────────────────────────────────────────────────    Parsing · Mutation · Judging
  DISPATCH FACADE   ────────────────────────────────────────  unchanged, still the choke point
```

A capability is a small, pure-ish, independently testable, independently *swappable* object.
`ArchitectStep` becomes "Retrieval + Prompting + Inference + StructuredParse". `GenerateStep`
becomes "Prompting + Inference + EditFormatParse". They share three of four parts, and the
sharing is by construction rather than by discipline.

### Verified findings that motivate this

| # | Finding | Evidence | Consequence |
| :--- | :--- | :--- | :--- |
| **A1** | `workflow/nodes/*` transitively imports `httpx` and three concrete adapters | Executed: importing `aether.workflow.nodes.retrieve` pulls in `aether.adapters.model_provider.openai_compatible`, `adapters.tools.builtin`, `adapters.workspace.git_cli` | The effect-payload types (`ReadArgs`, `WriteArgs`, `ShellArgs`, `ApplyPatchArgs`) live in `composition.py` beside the concrete adapter closures. A node cannot be unit-tested, or ported, without the whole adapter stack |
| **A2** | `_worktree_path` has **four independent copies**, one inside the TCB | `measurement/evaluator.py:71`, `adapters/tools/builtin.py:53`, `adapters/indexer/tree_sitter.py:24`, `adapters/workspace/git_cli.py:39` (4-arg variant) | Worktree layout is an invariant expressed four times. A change to it silently desynchronises the judge from the tools |
| **A3** | The model-call-and-collect-text idiom is written 4 times | `architect.py:88-89`, `architect.py:142-143`, `repair.py:180-182`, `generate.py:146-151` | Every one reserves `BudgetDims(prompt_tokens=self._max_tokens)` — and `max_tokens` is a *completion* ceiling. One bug, four sites |
| **A4** | `TaintSpan(...)` is hand-constructed 10 times across 3 node files | `grep -c "TaintSpan(" src/aether/workflow/nodes/*.py` → architect 5, generate 3, repair 2 | Provenance labelling is a policy decision made ad hoc at 10 call sites. This is exactly how `Provenance.AGENT` came to be applied to repository content and test tracebacks alike |
| **A5** | "Read entry files into a prompt block" is implemented twice with different semantics | `retrieve.py:67-93` (byte budget, publishes `missing`) vs `repair.py:122-132` (no budget, swallows to `(error: X)`) | The repair turn can blow the context window on a file the retrieve turn would have truncated |
| **A6** | Prompt layering is string concatenation inside nodes | `architect.py:92-96`, `architect.py:145-152` both do `f"{instructions}\n\n## Header\n{text}"` | [ADR-0010](../decisions/0010-context-prefix-layers.md)'s L1–L5 cannot be enforced, measured, or cached, because there is no object that holds the layers |
| **A7** | Four payload types re-declare the same envelope | `RetrievedContext`, `GeneratedPatch`, `AppliedPatch`, `EvaluatedCandidate` each carry `task` + `worktree`; three carry `iteration`; three carry `patch_text`/`raw_output` | Every new node writes envelope plumbing, and every field addition is a four-file change |
| **A8** | `engine.py` holds 7 near-identical factory closures | `engine.py:82-134` | Registering a node kind is a code change in the assembly root — the one file ADR-0014 wanted to stop editing |

None of these is a bug that produces a wrong answer today. **All of them are the tax that
gets paid on every future node**, and the roadmap adds a lot of nodes.

---

## 1. Abstraction — how it is, and how it should be

### 1.1 What is already right, and stays

Four abstractions in the current tree are correct and this proposal builds on them rather than
replacing them:

1. **`WorkflowStep[In, Out]` with declared socket types** (`workflow/step.py:26-40`). Typed
   sockets are what let `validator.check_socket_compatibility` verify a graph statically, from
   an *injected* socket map, without importing node classes. That indirection is load-bearing
   and stays.
2. **`StepFactory = Callable[[Mapping[str, Any]], WorkflowStep]`** (`step.py:51`). Registration
   by *kind*, not by node id, is what makes two `generate` nodes legal in one topology. This is
   the correct shape; the problem is only that the factories are hand-written.
3. **`EditFormat` as a Protocol with `instructions()` beside `parse()`** (`edit_format.py:66-78`).
   This is the single best abstraction in the codebase and it is the template for everything
   below: *the thing that asks and the thing that reads the answer are one object, so they
   cannot disagree.* Every capability proposed here follows this rule.
4. **`DispatchFacade`** (`dispatch_facade.py`). Steps hold no adapter handles; every effect is
   one of five verbs through the choke point. This does not change.

### 1.2 What is missing: the capability layer

A node currently answers five questions at once, inline:

```python
# generate.py — one class, five concerns interleaved
def _build_spans(...)      # 1. what context, labelled how          (Prompting + Provenance)
def _system_message(...)   # 2. what contract is stated             (Prompting)
async def run(...):
    events = await self._dispatch.model(request, BudgetDims(...))   # 3. inference + budgeting
    for event in events: ...                                        # 4. stream reduction
    return GeneratedPatch(task=..., worktree=..., raw_output=...)   # 5. envelope plumbing
```

`RepairStep.run()` answers the same five, differently. `ArchitectStep.run()` answers the same
five, differently again. Three implementations of one shape is the definition of the thing to
factor out.

**Proposed: six capability protocols**, all in `agency/` (the package `spec.md` §3 declares and
that does not yet exist), each a `Protocol` with a registry, exactly mirroring `EditFormat`:

| Capability | Question it answers | Current home | First implementations |
| :--- | :--- | :--- | :--- |
| `ContextSource` | *What goes in the prompt?* | inlined in `retrieve.py` + `repair.py` | `EntryFileSource`, `SymbolSource` (wraps the existing `Indexer`), `DiffSource`, `GateOutputSource` |
| `PromptAssembler` | *How are layers ordered and labelled?* | string concat in 4 places | `LayeredAssembler` (ADR-0010 L1–L5, this is [TASK-031](../agile/backlog.md)) |
| `Inference` | *How is the model called and reduced?* | 4 copies | `SingleTurn`, `ToolLoop` (the `MAX_ROUNDS` loop from `generate.py:139-196`) |
| `OutputParser` | *How is the reply read?* | `EditFormat` (already correct) + ad-hoc `TextDelta` joins | `EditFormat` implementations, `PlanParser`, `PassthroughText` |
| `WorkspaceMutation` | *How does an edit reach the worktree?* | `apply.py:75-97` | `PatchApply`, `WholeFileWrite` |
| `Verdict` | *How is a candidate judged?* | `evaluate.py` (correct — TCB, do not touch) | `RealEvaluator` only. **Deliberately not extensible** |

`Verdict` is listed for completeness and is explicitly **closed**. I7 depends on there being
exactly one judge; a pluggable verdict capability would be the single most dangerous thing this
proposal could add. It is named here so that the asymmetry is a recorded decision rather than
an oversight.

### 1.3 What a node becomes

```python
# agency/nodes/model_node.py — one class, replacing three
class ModelNode(WorkflowStep[Any, Any]):
    """Any node whose work is: gather context, assemble a prompt, call a model,
    parse the reply. Architect, generate, repair and reflector are all this
    node with different capabilities bound at composition."""

    def __init__(
        self,
        *,
        node_kind: str,
        input_type: type[Frozen],
        output_type: type[Frozen],
        sources: tuple[ContextSource, ...],
        assembler: PromptAssembler,
        inference: Inference,
        parser: OutputParser,
        role: str,
    ) -> None: ...

    async def run(self, ctx: StepContext, payload: Any) -> Any:
        blocks = [b for s in self._sources for b in await s.gather(ctx, payload)]
        request = self._assembler.assemble(role=self._role, blocks=blocks,
                                           contract=self._parser.instructions())
        reply = await self._inference.invoke(ctx, request)
        return self._parser.parse(reply).into(payload)
```

Then the four model-calling nodes are **data**, not classes:

```python
# agency/roles.py — the role catalog. Each entry is one dict, not one file.
ARCHITECT = RoleSpec(
    role=ARCHITECT_SYSTEM_ROLE,
    sources=(EntryFileSource(), InstructionsSource()),
    parser=PlanParser(),          # writes to a `plan` field, not into `instructions`
)
EDITOR = RoleSpec(
    role=EDITOR_SYSTEM_ROLE,
    sources=(InstructionsSource(), PlanSource(), EntryFileSource()),
    parser=EditFormatParser("whole_file_codeblock"),
)
REPAIRER = RoleSpec(
    role=EDITOR_SYSTEM_ROLE,
    sources=(InstructionsSource(), PlanSource(), CurrentFileSource(),
             PreviousAttemptSource(), GateOutputSource(tail=3000)),
    parser=EditFormatParser("whole_file_codeblock"),
)
REFLECTOR = RoleSpec(
    role=REFLECTOR_SYSTEM_ROLE,
    sources=(GateOutputSource(tail=2000), PreviousAttemptSource()),
    parser=LessonParser(),
)
```

This is the answer to requirement §8 in the brief. **The architect and the executor differ by
their source list and their parser, and by nothing else.** `RepairStep` is `EDITOR` plus two
extra sources. The 156 lines of `architect.py` and the 192 of `repair.py` become ~15 lines of
declaration each, and the shared 80% is one tested implementation.

### 1.4 Provenance stops being ad hoc

A `ContextSource` returns `ContextBlock`s, and **a block's provenance label is a property of
its source, declared once**:

```python
class ContextBlock(Frozen):
    layer: Layer                 # L1..L5 — ADR-0010
    label: Provenance            # set by the source, never by the node
    heading: str
    text: str
    source_id: str

class GateOutputSource:
    layer = Layer.L5
    label = Provenance.AGENT     # test output is agent-derived, stated once
```

This removes finding A4 and makes finding A6 structurally impossible: a node can no longer
concatenate model output into an `OPERATOR`-labelled instruction string, because it never
touches strings — it passes blocks to an assembler that emits one `TaintSpan` per block with
the block's own label. That is the mechanism [TASK-048](./proposal_workflows_hybrids_improvements.md)
asks for, obtained as a side effect of the refactor rather than as a separate task.

---

## 2. Loop engineering: inner, outer, and meta

The three loops are not three code paths. **They are the same executor at three scopes**, and
keeping that true is what makes the meta-process cheap later.

```
   META LOOP        propose topology / role / prompt variant → measure → admit or delete
   (offline)        unit of work: a TOPOLOGY HASH
        │           authority: ADR-0006 mutable surface + ADR-0014 ancestry block
        │           ─────────────────────────────────────────────────────────────
        ▼
   OUTER LOOP       run a manifest × arms → paired outcomes → statistics → gate family
   (measurement/)   unit of work: a RUN over N TASKS
        │           already exists: runner.py, statistics.py, families/
        │           ─────────────────────────────────────────────────────────────
        ▼
   INNER LOOP       retrieve → plan → edit → apply → judge →(fail,k)→ repair
   (workflow/)      unit of work: ONE TASK
                    already exists: executor.py static unroll
```

### 2.1 The inner loop: what it is and what it lacks

`executor.py` implements two things: a linear walk (`_topological_order`, line 96) and a static
repair unroll (`_run_repair_unroll`, line 213). Both are correct. Two structural limits:

- **`_topological_order` walks a single chain.** `edge_map = {e["from"]: e["to"]}` is a 1:1
  map — a node with two outgoing edges silently loses one. This is honest for M1a but it means
  branching is not "a missing feature", it is a different traversal.
- **`via_nodes` resolves to one step instance per node id** (`executor.py:156-159`), so every
  unrolled iteration shares configuration. Per-iteration escalation (local repair ×2, then a
  frontier repair) is not expressible.

**Proposal: promote the loop constructs to first-class, data-declared `Strategy` objects.**

```python
# workflow/strategies.py
class ExecutionStrategy(Protocol):
    """How the executor advances through a region of the graph.
    Registered by name; a topology names one. TCB — same status as the executor."""
    async def advance(self, ctx: ExecCtx, region: Region, payload: Any) -> Any: ...

LinearStrategy        # today's _topological_order
BoundedRepeatStrategy # today's _run_repair_unroll, generalised: any chain, any predicate
BestOfNStrategy       # TASK-035 — N children of one parent lease, declared join
CascadeStrategy       # BoundedRepeat with a per-iteration override table
```

This is the same move ADR-0014 made for topologies, applied to control flow: **the executor
stops being a switch statement over loop kinds and becomes a strategy dispatcher.** TASK-035
(conditional branching, M3) then adds a strategy rather than rewriting `execute()`, and the
hybrid rescue cascade from
[`proposal_workflows_hybrids_improvements.md`](./proposal_workflows_hybrids_improvements.md) §5
becomes expressible without a schema change:

```yaml
repair:
  strategy: cascade
  max_iterations: 3
  per_iteration:
    - { model: "qwen2.5-coder:7b" }        # free
    - { model: "qwen2.5-coder:7b" }        # free
    - { model: "deepseek/deepseek-v4" }    # paid rescue, only 20% of tasks reach here
```

**Constraint that does not move:** the graph stays acyclic and every bound stays static. A
strategy may not introduce a runtime-unbounded loop; `check_bounded_iteration` extends to
validate each strategy's own bound. `validator.py` and `executor.py` are TCB
([`spec.md` §6](../spec.md#6-trusted-computing-base)), so this needs human review and cannot be
a meta-loop auto-commit ([ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)).

### 2.2 The outer loop: it exists, and it is under-abstracted

`measurement/runner.py` (304 lines) already implements `HarnessUnderTest` with a bare-model arm
(TASK-015). The outer loop's missing piece is not code, it is that **an arm is not yet a
declarative object**. An arm today is a function; it should be the same kind of hash-pinned data
a topology is:

```yaml
# measurement/arms/hybrid_planner_v1.yaml
arm_id: hybrid_planner_v1
harness: aether
topology: sha256:...          # hash, never filename — ADR-0014's own rule
routes:                        # per-role endpoint binding (TASK-042)
  architect: openrouter/deepseek-v4-flash
  "*":       local/qwen2.5-coder-7b
manifest: sha256:7c2c2467...
split: dev
seed: 42
```

An ablation family then names arm hashes, and "run the ablation" is a pure data operation. This
also closes a real gap: `measurement.md` §6 requires a published run to name "manifest hash,
split, model fingerprint, topology hash, container digests, lockfile hash, seed" — today that
tuple is assembled by hand in a script. As an arm file it is one hash.

### 2.3 The meta loop: what this refactor buys it

The meta-loop's whole difficulty is [ADR-0014](../decisions/0014-workflow-topology-is-data.md)'s
own framing: *the only mechanical path from here to self-redesign runs through arbitrary code
modification, and the intermediate rung is missing.* ADR-0014 supplied one rung (topology as
data). This proposal supplies the two rungs above and below it:

```
  rung 4  ┃ new capability implementation      ┃ CODE   ┃ human PR, TCB review
  rung 3  ┃ new role (source list + parser)    ┃ DATA   ┃ meta-loop, ancestry-tracked   ← new
  rung 2  ┃ new topology (node composition)    ┃ DATA   ┃ meta-loop (ADR-0014)          ← exists
  rung 1  ┃ new prompt / retrieval params      ┃ DATA   ┃ meta-loop (ADR-0006)          ← exists
  rung 0  ┃ new arm (routing + manifest + seed)┃ DATA   ┃ meta-loop, admission-gated    ← new
```

Rung 3 is the valuable one and it does not exist today: "try the architect with symbol
retrieval instead of whole-file retrieval" is currently a Python edit. As a role file it is a
data mutation the meta-loop can propose, the validator can check, and the statistics engine can
admit or reject — with the schema's existing `ancestry` block (`workflow_schema.yaml`, already
written for exactly this) recording `parent_hash` and `admitted_by_family`.

**The safety property that must hold:** rungs 0–3 are data, and data cannot widen capability.
A role file names a `ContextSource` by registered id; it cannot define one. A topology names a
strategy; it cannot define one. The registries are frozen at composition (I6). This is what
keeps the meta-loop's grant small.

---

## 3. Config-driven + hexagonal, and what the frontend gets

### 3.1 The property that already exists and should be protected

`engine.run()` is a single async function returning a typed `RunResult`, and every client is a
consumer of one event stream with no privileged access. **A GUI is therefore not an
architectural question — it is a consumer.** The work is not "build a GUI seam"; the seam is
`engine.py` + `kernel/bus.py`. The work is making the *inputs* as declarative as the outputs
already are.

### 3.2 The asymmetry to fix

| Direction | Today |
| :--- | :--- |
| Engine → client | **Typed, complete.** `domain/events.py`, 8 events, catalog drift-checked, bus with per-consumer backpressure policy |
| Client → engine | **Untyped, partial.** `engine.run()` takes 15 loose keyword arguments (`repo_path`, `model_base_url`, `usd_micros_ceiling`, `entry_files`, …); several behaviours are reachable *only* from `scripts/run_local_check.py` and not from the engine at all |

A frontend cannot offer a control that the engine's signature does not expose, and a 15-argument
signature is not introspectable — a GUI cannot render a form for it, and a config file cannot
round-trip it.

**Proposal: one frozen `RunConfig` domain model**, replacing the keyword arguments.

```python
# domain/config.py — pure, frozen, JSON round-trippable like every other domain model
class RunConfig(Frozen):
    topology: TopologyRef          # hash or path
    manifest: ManifestRef
    split: Literal["dev", "holdout", "sealed"]
    routes: tuple[ModelRoute, ...] # per-role endpoint + credentials-by-env-name
    budget: BudgetDims             # the run ceiling
    sandbox: SandboxConfig
    seed: int
    ablation: AblationFlags        # named arms, e.g. inject_test_source: bool = False
```

Three things fall out of this immediately, at no extra cost:

1. **The GUI form is generated, not written.** `RunConfig.model_json_schema()` is a complete,
   typed description of every knob. A React form, a `--help` output, and a TUI settings panel
   are three renderers of one schema. Nothing has to be kept in sync by hand.
2. **A run becomes reproducible by construction.** `measurement.md` §6's required instrument
   tuple is `sha256(RunConfig)`. Today it is assembled by hand and can silently omit a field.
3. **Ablation arms stop being ad hoc.** The test-source injection currently hard-coded in
   `scripts/run_local_check.py:47-56` becomes `ablation.inject_test_source`, defaulting to
   `False`, and any run that sets it says so in its own config hash. That is the difference
   between a contaminated instrument and a *named arm* — see
   [`proposal_workflows_hybrids_improvements.md`](./proposal_workflows_hybrids_improvements.md) §3.

### 3.3 What this unlocks for cost and results

Because routing, budget and topology are all in one frozen config, the frontend can offer
operations that are currently code changes:

- **"Run this task cheaply"** → swap `routes` to all-local, keep the topology. One field.
- **"Rescue the 12 tasks that failed"** → new `RunConfig` with a frontier route on the repair
  role and a manifest subset. No code.
- **"What did this cost?"** → `RunResult.usage` already reads from the governor's ledger rather
  than being estimated afterwards. With node-scoped pricing (TASK-043) the per-role breakdown
  is already in the trajectory store; the GUI reads it from events.
- **"Show me why it failed"** → the trajectory store is append-only and byte-deterministic on
  replay. A GUI trajectory viewer is a bus consumer with zero engine changes.

**The honest caveat:** none of this makes a run *valid*. A GUI that makes it easy to launch
arms makes it equally easy to launch arms before the floor exists, which
[ADR-0002](../decisions/0002-no-number-before-the-floor.md) forbids with no reversal condition.
`RunConfig` should carry `split`, and the harness should refuse `holdout`/`sealed` while
`docs/rationale/benchmarks/noise-floor.md` holds no number — enforcement in the engine, not a
warning in the UI.

---

## 4. Codebase, patterns, and how capabilities are actually invoked

### 4.1 The folder tree: current vs. proposed

`spec.md` §3 already declares the target tree, including `agency/` with a `context/`
subpackage. **`agency/` does not exist.** That is not cosmetic — it is why prompt logic lives
in `workflow/nodes/` and gets duplicated. `sprint-03.md` and `STATUS.md` both record the reason:
`.importlinter`'s `aether-layers` puts `aether.agency` and `aether.workflow` at the same level
as *independent siblings*, so a `WorkflowStep` importing from `agency/` breaks a 9-for-9
contract. Splitting it is a lattice change and needs an ADR.

**That ADR is the unblocking move for this entire proposal**, and the change is small:

```diff
  layers =
      aether.engine
-     (aether.agency) | aether.workflow
+     aether.workflow
+     aether.agency
      aether.measurement
      aether.kernel
```

`workflow/` (the executor, validator, strategies — TCB) sits *above* `agency/` (capabilities,
roles, prompts — mutable). This is the correct direction: the TCB executor drives mutable
capabilities, and `agency/` still cannot reach `workflow/`, `measurement/` or the evaluator. The
independent-siblings arrangement was chosen when `agency/` was empty; it has no defender now.

Proposed tree, with only the deltas marked:

```
src/aether/
├── domain/
│   ├── config.py            NEW  RunConfig, ModelRoute, AblationFlags  (§3.2)
│   ├── context.py           NEW  ContextBlock, Layer                    (§1.4)
│   └── effects.py           NEW  ReadArgs/WriteArgs/ShellArgs/ApplyPatchArgs
│                                 ← MOVED from composition.py — fixes finding A1
├── ports/                   unchanged — 9 protocols, frozen per minor version
├── kernel/                  unchanged — TCB
├── agency/                  NEW PACKAGE — everything mutable and reusable
│   ├── capabilities/
│   │   ├── sources.py            ContextSource impls        (EntryFile, Symbol, GateOutput, …)
│   │   ├── assembler.py          PromptAssembler — TASK-031's L1–L5, one home
│   │   ├── inference.py          Inference impls            (SingleTurn, ToolLoop)
│   │   ├── parsers.py            OutputParser impls         (Plan, Lesson, Passthrough)
│   │   └── mutation.py           WorkspaceMutation impls    (PatchApply, WholeFileWrite)
│   ├── roles.py                  RoleSpec catalog — ARCHITECT / EDITOR / REPAIRER / REFLECTOR
│   └── registry.py               name → capability, frozen at composition (I6)
├── workflow/
│   ├── step.py              unchanged
│   ├── validator.py         + per-strategy bound checks         (TCB)
│   ├── executor.py          − loop bodies, + strategy dispatch  (TCB)
│   ├── strategies.py        NEW  Linear / BoundedRepeat / BestOfN / Cascade   (TCB)
│   ├── edit_format.py       unchanged — already the right shape
│   └── nodes/
│       ├── model_node.py    NEW  replaces architect.py, generate.py, repair.py
│       ├── apply.py         thinned — delegates to WorkspaceMutation
│       ├── retrieve.py      thinned — delegates to ContextSource
│       └── evaluate.py      unchanged — TCB path, deliberately not generalised
├── measurement/
│   ├── arms/                NEW  declarative arm files                (§2.2)
│   └── …                    otherwise unchanged
├── adapters/
│   ├── model_provider/routing.py   NEW  TASK-042 — the composite the port docstring promises
│   └── …
├── engine.py                takes ONE RunConfig
└── composition.py           wiring only; no payload types
```

### 4.2 Fixing A1 concretely

`composition.py:36-62` defines `ReadArgs`, `WriteArgs`, `ApplyPatchArgs`, `ShellArgs` — pure
frozen models with no I/O — in the same module that imports `OpenAICompatibleProvider`,
`BuiltinToolRegistry` and `GitCliWorkspace` at module scope. Every node imports them from there
(`retrieve.py:22`, `apply.py:15`, `generate.py:26`, `repair.py:36`). Result, executed and
confirmed: importing one node loads `httpx` and three adapters.

The fix is a file move, not a redesign: these are domain payloads, they belong in
`domain/effects.py`, and `composition.py` imports them like everyone else. This is worth doing
early and independently — it is mechanical, it is testable (`import aether.workflow.nodes.retrieve`
must not import `httpx`), and it is a precondition for any Rust/Go extraction (§5).

### 4.3 How each capability is invoked, today and proposed

| Capability | Today | Proposed |
| :--- | :--- | :--- |
| **Tools / skills** | `BuiltinToolRegistry` catalog frozen at composition; the tool loop is `MAX_ROUNDS = 4` inlined in `generate.py:139-196`; tools are off unless `params.tools: true` | The loop becomes `ToolLoop(Inference)`, usable by *any* role. Today only `generate` can use tools — an architect that wants to `ls` the repo cannot, which is precisely the brief's example |
| **Context** | `RetrieveStep` reads `params.entry_files`; `RepairStep` re-reads them separately (A5) | One `EntryFileSource`, one byte-budget policy, one `missing` semantics, used by every role |
| **Memory** | None. `ReflectorStep` writes a lesson into `task.instructions` and it dies with the run | `LessonStore` as a `ContextSource` + a bus consumer. Cross-task memory is a *mechanism* and does not promote without an ablation ([`spec.md` §7](../spec.md#7-measurement)) |
| **Prompt engineering** | `SYSTEM_ROLE` constants in 3 files; layering by f-string | `RoleSpec.role` + `LayeredAssembler`. Prompts become data → rung 1 of the meta-loop ladder |
| **Caching** | `ModelMessage.cache_breakpoint` exists; nothing sets it, and `openai_compatible.py:40` records that it is *deliberately* not emitted (OpenAI-compatible endpoints cache implicitly). The harness-side half — stable layer ordering — is what is missing | The assembler owns breakpoints (≤4, I10) because it owns the layers. This is TASK-031, whose gated metric is **harness-side prefix stability**, not a provider hit rate — and it is unbuildable until the assembler exists |
| **Indexing / search** | `TreeSitterIndexer` is a real adapter, passes conformance, and **is wired into no node and no topology** | `SymbolSource` wraps it. A role opts in by naming it. This is a working capability currently reachable by nothing |
| **Web search** | Absent | A `ToolSpec` in a second `ToolRegistry` adapter, outputs labelled `UNTRUSTED_EXTERNAL` at construction like every tool (ADR-0015/0016). **No new port** |
| **Verdict** | `RealEvaluator`, TCB, single implementation | Unchanged and deliberately closed (§1.2) |

The row that should provoke a reaction is **Indexing**: a conformance-passing tree-sitter
indexer exists and no code path can reach it. That is a built capability delivering zero value
because there is no seam to plug it into. `ContextSource` is that seam.

---

## 5. Swapping technologies — and what Rust or Go would actually take

### 5.1 The property that makes this possible is already paid for

`spec.md` §4's port rules — every method `async`, no `Path`, no file handle, no callable, no
generator, no live object, no `dict[str, Any]`, all datetimes tz-aware — are exactly the
constraints that make a boundary **relocatable out of process**. `EffectRequest.descriptor` and
`EffectOutcome.result_json` are already JSON strings crossing the choke point. This was
described as "nearly free on day one, impossible to retrofit" and that assessment holds: the
system is *already* wire-compatible with an out-of-process implementation, and nobody has had
to do anything special to keep it that way.

### 5.2 The three-step extraction, per component

The pattern is identical for any component, and requires no caller change at any step:

```
  STEP 1  in-process Python adapter                     ← today
          composition.py binds `read` → GitCliWorkspace.read

  STEP 2  in-process Python adapter behind a JSON codec ← already true
          the descriptor is JSON; the result is JSON

  STEP 3  out-of-process sidecar
          composition.py binds `read` → SidecarClient("unix:///run/aether-ws.sock")
          the sidecar speaks the same JSON; it is written in Rust or Go
```

Only `composition.py` changes. Not the node, not the executor, not the topology, not the port.

### 5.3 Which components are actually worth extracting, and on what evidence

[ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md) is explicit: compiled
sidecars arrive **per component on a measured trigger, never speculatively**, and `TASK-021`
already published the F1 timers with hardware and method recorded. `STATUS.md` records the
result: **RT-3 not crossed; RT-1/RT-2 need a 1M-LOC corpus and are left open, not claimed.**

So the honest ranking is by *plausible* trigger, and none of these is a decision:

| Component | Why it is the plausible first sidecar | Trigger that would justify it |
| :--- | :--- | :--- |
| `Indexer` | Pure CPU, no state, tree-sitter has first-class Rust bindings, and the port is already `build`/`search`/`outline` over frozen payloads | RT-1/RT-2 crossed on a 1M-LOC corpus (ADR-0001's own open item) |
| `EditFormat` parsing | Pure function `str → ParsedEdit`, zero I/O, called on every turn of every task | Parse cost visible against inference cost — implausible today, stated for completeness |
| `Workspace` | Git-over-subprocess; a Go sidecar with `go-git` removes process spawn per operation | Worktree creation crossing RT-3 under Best-of-N fan-out (M3) |
| `Evaluator` | **Do not.** TCB residency (`measurement/`, never `adapters/`) is what makes `tcb-isolation` select it | None. Moving it out of process moves it out of the contract |

**The prerequisite for all of it is finding A1.** A component cannot be extracted while its
payload types live in the module that imports its concrete peers. `domain/effects.py` (§4.2)
is not a nicety here; it is the enabling change.

### 5.4 The protocol question, answered conservatively

There is no need to adopt gRPC, Cap'n Proto or any IDL. The wire format is already decided by
I2/I3: **JSON over the descriptor field**, with Pydantic models as the schema of record and
`model_json_schema()` as the exportable contract. A Rust sidecar generates its structs from that
schema; a conformance suite already exists (`tests/conformance/`) and is parametrized over
adapters — a sidecar becomes *one more adapter parameter in the existing suite*, which is the
strongest possible guarantee that it behaves identically. That is TASK-005's meta-test earning
its keep on a use case it was not written for.

---

## 6. Making the codebase elegant, DRY and hard to bloat

### 6.1 Concrete DRY moves, in order of ratio

| Move | Removes | Replaces with |
| :--- | :--- | :--- |
| `ModelNode` + `RoleSpec` (§1.3) | ~350 lines across `architect.py`, `generate.py`, `repair.py` | ~90 lines of node + ~40 of role data |
| `domain/effects.py` (§4.2) | The node→adapter import edge (A1) | A file move |
| One `worktree_path` in `domain/workspace.py` | 4 copies (A2), one in the TCB | A method on `WorktreeRef` |
| `Envelope` mixin for payloads (A7) | `task`/`worktree`/`iteration` re-declared 4× | One base model the four payloads extend |
| Registry-driven `build_step_registry` (A8) | 7 hand-written closures in `engine.py` | A dict comprehension over the role catalog |
| `ContextSource` (A5) | Two divergent file-reading loops | One, with one byte-budget policy |

### 6.2 Patterns to adopt — and, more importantly, ones to refuse

**Adopt:**

- **Protocol + registry + `get_x(name)`**, exactly as `edit_format.py:222-237` already does,
  including `UnknownEditFormat` raising **at construction, not at first use**. Every registry in
  this proposal follows that template verbatim. That "fail at load" property is why
  `UnregisteredNodeKind` (`executor.py:124-131`) is right: *a benchmark that fails on iteration
  three of task forty because a kind was never registered has already burned the run.*
- **Composition over inheritance for capabilities.** `ModelNode` has no subclasses; behaviour
  varies by injected capability. A `SubclassArchitectStep` would rebuild the duplication.
- **Frozen data everywhere**, already universal via `Frozen`. Keep it.

**Refuse:**

- **A DI container.** `composition.py`'s docstring says "there is no DI container and no runtime
  registration", and `spec.md` §3 says "explicit wiring; no DI container". A container would
  make I6 (catalog frozen at composition) unverifiable and reintroduce runtime registration
  through the back door. Explicit constructor injection is the pattern; a 200-line composition
  root that reads top-to-bottom is a feature.
- **A plugin system that loads capabilities from disk at runtime.** This directly contradicts I6
  and would hand the meta-loop rung 4 (arbitrary code) while pretending it is rung 3 (data).
- **Making `Verdict` pluggable.** §1.2.
- **Generalising the executor beyond acyclic + statically bounded.** ADR-0013's phasing is a
  safety property, not a limitation to route around.

### 6.3 Enforcement, so this does not decay

Abstractions rot unless a gate holds them. Each proposed structure gets one, following
`measurement.md` §5 — *every gate ships with a test proving it can fail*:

| Property | Gate |
| :--- | :--- |
| Nodes stay adapter-free | `test_node_imports_are_pure`: importing `workflow.nodes.*` must not import `httpx` or `aether.adapters` |
| Capabilities are registered, never constructed inline | import-linter contract: `workflow.nodes` may not import `agency.capabilities.*` concretes, only `agency.registry` |
| Roles stay data | `test_role_catalog_is_serialisable`: every `RoleSpec` round-trips through JSON |
| No new duplication | The `RoleSpec` catalog is the only place a system prompt string may appear — grep gate |
| Config is complete | `test_run_config_covers_engine`: `engine.run()` takes exactly one `RunConfig` parameter |
| Layers stay ordered | TASK-031's prefix-stability floor, which becomes measurable once the assembler exists |

---

## 7. Harness capabilities: what this buys at the code level

The brief states the thesis precisely — *"read code and prompt → send to LLM → process output
→ act"* does not solve hard tasks. The industry evidence and this project's own
`vision.md` §1 agree: a frontier model called once resolves 20–40%; the same model in a good
harness resolves substantially more, and **that delta is the entire product.**

The delta comes from capabilities the model does not have alone. Here is where each one stands
in this codebase and what the capability layer changes:

| Harness capability | What it does that a bare model cannot | Status | Unblocked by |
| :--- | :--- | :--- | :--- |
| **Ground truth feedback** | Runs the real tests and returns a real verdict | ✅ Built, containerized, canary-green | — |
| **Bounded repair** | Turns one failure into another attempt with the failure in context | ✅ Built (`vision.md`: *"the single largest lever on score"*) | — |
| **Isolation** | Parallel candidates cannot corrupt each other | ✅ Built (worktree per candidate) | — |
| **Budget enforcement** | Refuses effects the run cannot fund | ⚠️ Partial — node budgets reserved and released without commit | TASK-045 |
| **Targeted retrieval** | Shows the model the *right* 200 lines instead of the whole repo | ⚠️ Indexer built, **reachable by nothing** | `ContextSource` |
| **Decomposition** | Splits a hard task into a plan and an execution | ⚠️ `ArchitectStep` exists; plan is concatenated into an OPERATOR string; zero tests | `RoleSpec` + `PlanParser` |
| **Long-horizon context** | Survives a task longer than the window | ❌ No assembler, no compactor | TASK-031 → TASK-024 |
| **Prefix caching** | Same work, a fraction of the cost | ❌ `cache_breakpoint` field exists, never set | TASK-031 |
| **Multi-candidate search** | Try 5, keep the one that passes | ❌ M3 | TASK-035 |
| **Cross-task memory** | Learns a repo's conventions once | ❌ Reflector output dies with the run | `LessonStore` (post-floor, ablation-gated) |
| **Per-role model routing** | Frontier reasoning where it pays, local volume elsewhere | ❌ Single global `base_url` | TASK-042 |

Read the ⚠️/❌ column as a list: **most of the harness's leverage is not built yet, and three of
the unbuilt items are blocked on the same missing object — the prompt assembler — which cannot
exist while prompt logic is duplicated inside three node classes.** That is the load-bearing
argument for doing this refactor before M2 rather than after: TASK-031, TASK-024 and TASK-033
all land in `agency/context/`, a package that does not exist and that the current lattice
forbids nodes from importing.

The failure mode the brief describes — the simple DAG that cannot solve the problem — has a
specific shape in this codebase, and the user's own `internal__clamp_low-046` trajectory is it:
the model emitted `return b`, satisfied `assert f(6, 9) == 9`, and the harness had no capability
that could object. Not because the loop was too short, but because the instrument handed it the
assertion. **Capabilities do not fix that; the instrument work does** (see
[`proposal_workflows_hybrids_improvements.md`](./proposal_workflows_hybrids_improvements.md) §3).
Both are needed, and the instrument comes first.

---

## 8. Compound DAGs: subgraph reuse without copy-paste

### 8.1 The problem, stated concretely

The seven files in `workflows/` share structure by having the same lines typed repeatedly.
`linear_repair_v1`, `linear_repair_wholefile_v1`, `linear_repair_autofiles_v1`,
`linear_repair_small_model_v1` and `decomposed_planning_v1` all contain the same
`apply → evaluate` pair, the same repair block shape, and the same budget dimensions with
different constants. Adding a node kind means editing five files. A schema change means editing
seven.

This is the same defect ADR-0014 diagnosed one level up: composition was code, so a variant was
a PR. Here, composition is data but **has no composition operator**, so a variant is a
copy-paste.

### 8.2 Proposed: `fragment` — a named, reusable subgraph

One additive schema change (`schema_version: 1.1.0`, additive-only per `spec.md` §4's port
versioning rule):

```yaml
# workflows/fragments/edit_and_judge.yaml
fragment_id: edit_and_judge
description: "The universal tail: turn a reply into files, judge it, repair k times."
inputs:  { patch: GeneratedPatch }
outputs: { verdict: EvaluatedCandidate }
nodes:
  - { id: apply,    kind: apply,    budget: { wall_clock_ms: 30000 } }
  - { id: evaluate, kind: evaluate, budget: { wall_clock_ms: 900000, concurrency_slots: 1 } }
  - { id: repair,   kind: model,    params: { role: repairer }, budget: { ... } }
edges:
  - { from: apply, to: evaluate }
repair:
  strategy: bounded_repeat
  from_node: evaluate
  via_nodes: [repair, apply]
  back_to: evaluate
  max_iterations: 3
  budget_per_iteration: { ... }
```

Then every topology is a short composition:

```yaml
# workflows/decomposed_planning_v2.yaml
topology_id: decomposed_planning_v2
nodes:
  - { id: retrieve,  kind: retrieve,  params: { sources: [entry_files] }, budget: { ... } }
  - { id: architect, kind: model,     params: { role: architect },        budget: { ... } }
  - { id: editor,    kind: model,     params: { role: editor },           budget: { ... } }
  - { id: tail,      use: edit_and_judge }        # ← the fragment
edges:
  - { from: retrieve,  to: architect }
  - { from: architect, to: editor }
  - { from: editor,    to: tail }
```

This directly answers the brief's example. The architect *is* mostly reusable: it lists,
reads, injects a role prompt, and produces structured output. Under this design it shares
`retrieve` with every other topology, shares `ModelNode` with every other model call, and
differs only in `role: architect` and its parser. The executor is unchanged.

### 8.3 The three rules that make fragments safe

Inlining a fragment is a **pure textual expansion performed before validation**, not a runtime
indirection. That single decision preserves every existing guarantee:

1. **Expand, then validate.** `load_topology()` inlines fragments and namespaces their node ids
   (`tail.apply`, `tail.evaluate`) before `validate_topology()` sees anything. All five static
   checks — socket compatibility, evaluator termination, bounded iteration, declared fan-out,
   budget annotation — run on the expanded graph and need **no modification**. A fragment
   cannot smuggle a node past the judge, because by validation time there are no fragments.
2. **Fragments are hash-pinned, like topologies.** `use: edit_and_judge` resolves to a
   content hash recorded in the expanded artifact. ADR-0014's rule — *every cross-reference is
   by hash, never by filename* — applies unchanged, so a run's topology hash still fully
   determines its graph.
3. **Fragments declare socket types.** `inputs`/`outputs` let the socket check verify a
   fragment's *use site* the same way it verifies an edge. A fragment with an unsatisfiable
   input fails at load.

The one thing to watch: fragments are a TCB-adjacent change, because the expander runs before
the validator. It needs its own malformed fixtures — a fragment with a cyclic self-reference, a
fragment whose expansion routes around `evaluate`, a fragment with a node-id collision. That is
TASK-020's own exit criterion (*every static check has a fixture proving it can fail*) inherited
by a new mechanism, and it is the reason this is proposed as a numbered task rather than a
refactor.

---

## 9. Migration: five phases, none of which breaks a gate

Sequenced so each phase is independently valuable, independently revertible, and leaves CI
green. **Phase 0 is not part of this proposal** — it is the instrument work, and it comes first
because a refactor measured on a contaminated instrument teaches nothing.

| Phase | Content | Risk | Reversible by |
| :--- | :--- | :--- | :--- |
| **0** *(prerequisite)* | Instrument restoration + the A/A floor. Not this document | — | — |
| **1 — Mechanical** | `domain/effects.py` move (A1) · one `worktree_path` (A2) · `Envelope` base model (A7) | **Very low.** No behaviour change; the import test is new and would fail today | `git revert` |
| **2 — Lattice** | ADR: `workflow` above `agency`. Create `agency/`, move prompt constants and span construction in | **Low.** One `.importlinter` edit + file moves. Contracts stay 9/9 | ADR reversal condition |
| **3 — Capabilities** | `ContextSource`, `Inference`, `OutputParser`, `PromptAssembler` + registries. `ModelNode` + `RoleSpec` replace three node classes | **Medium.** Real behaviour surface. Mitigated by: existing topologies must produce byte-identical prompts, asserted by a golden-prompt test before and after | Keep old node classes one release, delete after the equivalence test passes |
| **4 — Config** | `RunConfig`; `engine.run(config)`; ablation flags become named | **Low-medium.** Mostly signature work; `scripts/` are the only callers | — |
| **5 — Composition** | `strategies.py`; fragments (`schema_version: 1.1.0`); arm files | **Medium-high.** TCB — validator and executor. Human review mandatory, no meta-loop authority | Schema is additive; 1.0.0 topologies keep validating |

**Phases 1 and 2 can start immediately** and are worth doing regardless of whether phases 3–5
are ever ratified: they are pure deletion of duplication and one lattice correction that
`spec.md` §3 already specifies. Phases 3–5 should follow the floor, because their whole
justification is making ablations cheap to define, and an ablation before the floor is a number
that gets discarded.

---

## 10. New backlog tasks

Written in [`backlog.md`](../agile/backlog.md) form so they can be lifted in if ratified.
Complexity uses the backlog's 0–5 scale.

| Task | Title | Cx | Depends on | Exit criterion (short) |
| :--- | :--- | :---: | :--- | :--- |
| **TASK-050** | Effect payloads to `domain/effects.py` | **1** | — | `import aether.workflow.nodes.retrieve` does not import `httpx`; negative test proves the check can fail |
| **TASK-051** | Single `worktree_path` on `WorktreeRef` | **1** | — | Four copies deleted; the TCB evaluator and the tool registry provably agree |
| **TASK-052** | `Envelope` base for node payloads | **2** | TASK-050 | Four payload types share one base; socket types unchanged |
| **TASK-053** | ADR + lattice change: `workflow` above `agency` | **3** | — | `lint-imports` stays 9/9 with `agency` populated; ADR carries a reversal condition |
| **TASK-054** | `ContextSource` protocol + 5 implementations | **3** | TASK-053 | `retrieve` and `repair` share one file-reading path; `SymbolSource` makes `TreeSitterIndexer` reachable for the first time |
| **TASK-055** | `Inference` + `OutputParser` protocols | **3** | TASK-053 | The 4 duplicated model-call sites become one; `ToolLoop` usable by any role |
| **TASK-056** | `PromptAssembler` (**this is TASK-031**, relocated) | **4** | TASK-054/055 | L1–L5 order enforced; ≤4 breakpoints; harness-side prefix-stability floor in CI |
| **TASK-057** | `ModelNode` + `RoleSpec` catalog | **3** | TASK-054/055/056 | `architect.py`, `generate.py`, `repair.py` deleted; golden-prompt equivalence test green |
| **TASK-058** | `RunConfig` domain model | **2** | TASK-050 | `engine.run()` takes one parameter; `sha256(RunConfig)` is the instrument tuple; `holdout`/`sealed` refused while the floor is empty |
| **TASK-059** | `ExecutionStrategy` seam | **4** | TASK-057 | **TCB.** Executor dispatches strategies; each strategy's bound has a malformed fixture proving the check can fail |
| **TASK-060** | Topology fragments (`schema_version: 1.1.0`) | **4** | TASK-059 | **TCB-adjacent.** Expansion precedes validation; three malformed fixtures (cycle, judge-bypass, id collision) |
| **TASK-061** | Declarative arm files | **2** | TASK-058 | An ablation family names arm hashes; a run's instrument tuple is one hash |

TASK-056 is TASK-031 with a different home, not an additional task. Listing it separately would
double-count the work.

---

## 11. What this proposal does not claim

- **No lift is claimed.** This is a structural refactor. It changes what is cheap to *try*, not
  what resolves. Any capability it unblocks still needs its own ablation clearing the floor
  ([`spec.md` §7](../spec.md#7-measurement)), and if one does not clear, it is deleted rather
  than left dormant ([TASK-025](../agile/backlog.md)'s rule).
- **No performance claim.** §5's Rust/Go ranking is by *plausible trigger*, not by measurement.
  RT-1/RT-2 are open in `performance_timers.md` and stay open. ADR-0001 forbids a speculative
  sidecar and this proposal does not request one.
- **No security claim.** The capability layer changes where provenance labels are *assigned*,
  not what the policy does with them. I11's enforcement gap — `DefaultPolicyEngine`'s predicate
  is correct but nothing on the model path produces untrusted spans — is unaffected and is
  TASK-030b's.
- **This is not a rewrite.** Every phase is additive or a file move. The domain models, the
  ports, the kernel, the evaluator, the statistics engine and the container are untouched.
- **TASK-059 and TASK-060 touch the TCB**, and are proposed with that flagged, not smuggled.

## 12. Reversal conditions

- **On the capability layer**: if after two sprints of use no role has been defined by
  composing existing capabilities — i.e. every new node still needs a new capability
  implementation — the layer is unearned indirection and `ModelNode` collapses back into
  per-role classes.
- **On fragments (TASK-060)**: if fewer than three topologies share a fragment six months after
  it lands, the expander is deleted and topologies stay flat. A composition operator with one
  user is worse than copy-paste, because it hides the graph.
- **On strategies (TASK-059)**: if TASK-035 lands cleanly as a strategy but no second strategy
  is ever added beyond the four proposed, the seam is fine but should not grow further —
  strategies are TCB and each one is an audit surface.
- **On `RunConfig`**: no reversal condition. A typed engine input is a precondition for every
  client surface in `spec.md` §8 and for `measurement.md` §6's instrument tuple.

---

## Appendix: verification commands

Every finding above came from one of these, run on `rewrite_v310-phase-0` at 2026-08-07.

```bash
# A1 — nodes transitively import httpx and three concrete adapters
uv run python -c "
import sys; before=set(sys.modules)
import aether.workflow.nodes.retrieve
after=set(sys.modules)-before
print('httpx:', any(m.startswith('httpx') for m in after))
print('adapters:', sorted(m for m in after if 'adapters' in m))"

# A2 — four copies of worktree path construction, one inside the TCB
grep -rn "def _worktree_path" src/aether/

# A3 — the model-call-and-collect idiom, and the max_tokens reservation bug
grep -rn "TextDelta)" src/aether/workflow/
grep -rn "BudgetDims(prompt_tokens=self._max_tokens)" src/aether/workflow/

# A4 — hand-constructed spans per node file
grep -c "TaintSpan(" src/aether/workflow/nodes/*.py

# A5 — two independent file-reading implementations
sed -n '67,93p'   src/aether/workflow/nodes/retrieve.py
sed -n '122,132p' src/aether/workflow/nodes/repair.py

# A6 — prompt layering as string concatenation
sed -n '90,96p'   src/aether/workflow/nodes/architect.py
sed -n '144,153p' src/aether/workflow/nodes/architect.py

# A7 — the repeated envelope
grep -rn "    worktree: WorktreeRef" src/aether/workflow/nodes/

# A8 — seven hand-written factory closures in the assembly root
sed -n '82,134p' src/aether/engine.py

# capability reachability: the indexer is wired into nothing
grep -rn "TreeSitterIndexer\|Indexer" src/aether/engine.py workflows/ ; echo "exit=$?"

# cache breakpoints are declared and never set
grep -rn "cache_breakpoint" src/aether/

# the lattice as it stands (contracts are 9/9 today and must stay so)
uv run lint-imports
```
