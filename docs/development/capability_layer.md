---
status: rationale
updated: 2026-08-07
---

# Capability Layer — Design of Record

**This is the design M1b implements** (`TASK-050`–`058`, [`sprint-05.md`](../agile/sprints/sprint-05.md)).
Ratified by [ADR-0018](../decisions/0018-agency-below-workflow.md). It is a reference, not a
proposal — where it and the code disagree once M1b lands, **the code wins and this file is a bug**.

Downstream detail lives elsewhere and is not repeated here: port shapes in
[`core_skeletons_and_protocols.md`](./core_skeletons_and_protocols.md), schema fields in
[`schemas_and_contracts.md`](./schemas_and_contracts.md), task exit criteria in
[`backlog.md`](../agile/backlog.md).

---

## 1. Why the layer exists

Today the system has two levels of abstraction, and a node is the only unit of reuse:

```
  TOPOLOGY (data)  ──────────────────────────────────  YAML, swappable
  NODE (code)      ──────────────────────────────────  a 60–150 line class
  DISPATCH FACADE  ──────────────────────────────────  read/write/shell/model/evaluate
```

A node answers five questions at once, inline: what context, labelled how; what contract is
stated; how the model is called and budgeted; how the stream is reduced; and envelope plumbing.
`GenerateStep`, `RepairStep` and `ArchitectStep` each answer all five, differently.

### The measured cost of that

Each of these was verified by execution or a line-level read at 2026-08-07. They are the reason
the layer is worth building; every one disappears as a side effect of it.

| # | Finding | Evidence | Closed by |
| :--- | :--- | :--- | :--- |
| **A1** | `workflow/nodes/*` transitively imports `httpx` and three concrete adapters | `import aether.workflow.nodes.retrieve` pulls in `openai_compatible`, `tools.builtin`, `workspace.git_cli` — the effect payload types live in `composition.py` beside the adapter closures | `TASK-050` |
| **A2** | `_worktree_path` has **four copies**, one inside the TCB | `measurement/evaluator.py:71`, `adapters/tools/builtin.py:53`, `adapters/indexer/tree_sitter.py:24`, `adapters/workspace/git_cli.py:39` | `TASK-051` |
| **A3** | The model-call-and-collect idiom is written 4× | `architect.py:88,142`, `repair.py:180`, `generate.py:146` — every one reserves `BudgetDims(prompt_tokens=max_tokens)`, and `max_tokens` is a *completion* ceiling. One bug, four sites | `TASK-055` |
| **A4** | `TaintSpan(...)` hand-constructed 10× across 3 files | architect 5, generate 3, repair 2 | `TASK-054` |
| **A5** | "Read entry files into a prompt block" implemented twice, differently | `retrieve.py:67-93` (byte budget, publishes `missing`) vs `repair.py:122-132` (no budget, swallows errors) | `TASK-054` |
| **A6** | Prompt layering is string concatenation inside nodes | `architect.py:92-96,145-152` — so ADR-0010's L1–L5 cannot be enforced, measured or cached | `TASK-056` |
| **A7** | Four payload types re-declare the same envelope | `task` + `worktree` ×4; `iteration` ×3 | `TASK-052` |
| **A8** | `engine.py` holds 7 near-identical factory closures | `engine.py:82-134` — registering a kind edits the assembly root, the one file ADR-0014 wanted to stop editing | `TASK-057` |

**A4 is the one with teeth.** Provenance labelling became an ad-hoc decision at ten call sites,
which is exactly how repository file slices and test tracebacks both came to be labelled
`Provenance.AGENT`.

---

## 2. The target shape

```
  TOPOLOGY (data)   ─────────────────────────  YAML — composition of nodes
  NODE (thin)       ─────────────────────────  ~20 lines: wire capabilities
  CAPABILITY (code) ─────────────────────────  Sources · Assembler · Inference · Parsers
  DISPATCH FACADE   ─────────────────────────  unchanged, still the choke point (I5)
```

### 2.1 What does not change

Four existing abstractions are correct and this design builds on them:

1. **`WorkflowStep[In, Out]` with declared socket types** (`workflow/step.py`). Typed sockets are
   what let `validator.check_socket_compatibility` verify a graph statically from an *injected*
   socket map, without importing node classes. Load-bearing; stays.
2. **`StepFactory` registration by *kind*, not node id** (`step.py:51`). What makes two `generate`
   nodes legal in one topology.
3. **`EditFormat` as a Protocol with `instructions()` beside `parse()`** (`edit_format.py:66-78`).
   The best abstraction in the codebase and the template for every capability below: *the thing
   that asks and the thing that reads the answer are one object, so they cannot disagree.*
4. **`DispatchFacade`** — steps hold no adapter handles; every effect is one of five verbs.

### 2.2 The six capability protocols

Each is a `Protocol` with a registry and a `get_x(name)` that raises **at construction**, mirroring
`edit_format.py` exactly.

| Capability | Question it answers | First implementations |
| :--- | :--- | :--- |
| `ContextSource` | *What goes in the prompt?* | `EntryFileSource`, `CurrentFileSource`, `GateOutputSource`, `PreviousAttemptSource`, `SymbolSource` (wraps the existing `Indexer`) |
| `PromptAssembler` | *How are layers ordered and labelled?* | `LayeredAssembler` — ADR-0010 L1–L5 (`TASK-056`) |
| `Inference` | *How is the model called and reduced?* | `SingleTurn`, `ToolLoop` |
| `OutputParser` | *How is the reply read?* | `EditFormat` impls, `PlanParser`, `LessonParser`, `PassthroughText` |
| `WorkspaceMutation` | *How does an edit reach the worktree?* | `PatchApply`, `WholeFileWrite` |
| `Verdict` | *How is a candidate judged?* | `RealEvaluator` only — **deliberately closed** |

> **`Verdict` is closed on purpose.** I7 depends on there being exactly one judge. A pluggable
> verdict capability would be the single most dangerous thing this design could add. It is named
> so the asymmetry is a recorded decision rather than an oversight.

---

## 3. `ModelNode` — one class, four roles

```python
# workflow/nodes/model_node.py
class ModelNode(WorkflowStep[Any, Any]):
    """Any node whose work is: gather context, assemble a prompt, call a model,
    parse the reply. Architect, generate, repair and reflector are all this node
    with different capabilities bound at composition."""

    def __init__(
        self, *, node_kind: str,
        input_type: type[Frozen], output_type: type[Frozen],
        sources: tuple[ContextSource, ...], assembler: PromptAssembler,
        inference: Inference, parser: OutputParser, role: str,
    ) -> None: ...

    async def run(self, ctx: StepContext, payload: Any) -> Any:
        blocks  = [b for s in self._sources for b in await s.gather(ctx, payload)]
        request = self._assembler.assemble(role=self._role, blocks=blocks,
                                           contract=self._parser.instructions())
        reply   = await self._inference.invoke(ctx, request)
        return self._parser.parse(reply).into(payload)
```

Roles become **data**:

```python
# agency/roles.py
ARCHITECT = RoleSpec(role=ARCHITECT_SYSTEM_ROLE,
                     sources=(InstructionsSource(), EntryFileSource()),
                     parser=PlanParser())                      # → a `plan` field, not `instructions`
EDITOR    = RoleSpec(role=EDITOR_SYSTEM_ROLE,
                     sources=(InstructionsSource(), PlanSource(), EntryFileSource()),
                     parser=EditFormatParser("whole_file_codeblock"))
REPAIRER  = RoleSpec(role=EDITOR_SYSTEM_ROLE,
                     sources=(InstructionsSource(), PlanSource(), CurrentFileSource(),
                              PreviousAttemptSource(), GateOutputSource(tail=3000)),
                     parser=EditFormatParser("whole_file_codeblock"))
REFLECTOR = RoleSpec(role=REFLECTOR_SYSTEM_ROLE,
                     sources=(GateOutputSource(tail=2000), PreviousAttemptSource()),
                     parser=LessonParser())
```

**The architect and the editor differ by their source list and their parser, and by nothing
else.** `REPAIRER` is `EDITOR` plus two sources. ~350 lines across three files become ~90 lines
of node plus ~40 of role data.

### 3.1 Four structural constraints — get these wrong and the refactor fails

| Constraint | Why |
| :--- | :--- |
| **Node *kinds* stay distinct** (`architect`, `generate`, `repair`, `reflector`) | `NODE_SOCKETS` is keyed by `kind` and the validator resolves sockets by kind alone. `kind: model` + `params.role` collapses three different socket pairs into one. **One class, four factories** — zero validator change, zero topology change |
| **Nodes stay in `workflow/nodes/`** | `WorkflowStep` lives in `workflow/step.py`. A node under `agency/` importing it is an *upward* import and breaks `aether-layers` |
| **`EffectDispatch` is a structural Protocol declared where consumed** | `agency/` sits below `workflow/`, so it cannot import `DispatchFacade`. Precedent: `SandboxRunner` in `measurement/evaluator.py:60` — *"Not a port; a structural collaborator."* Structural typing means neither module imports the other. **No new port, no ADR** |
| **`edit_format.py` moves to `agency/capabilities/`** | Pure module (imports only `domain.ids.Frozen`), consumed by both `ApplyStep` (workflow ✅ downward) and the new parsers (agency) |

### 3.2 Provenance stops being ad hoc

```python
class ContextBlock(Frozen):
    layer: Layer            # L1..L5 — ADR-0010
    label: Provenance       # set by the SOURCE, never by the node
    heading: str
    text: str
    source_id: str

class GateOutputSource:
    layer = Layer.L5
    label = Provenance.AGENT     # test output is agent-derived — stated once, here
```

This closes A4 and makes A6 **structurally impossible**: a node can no longer concatenate model
output into an `OPERATOR`-labelled instruction string, because it never touches strings. It
passes blocks to an assembler that emits one `TaintSpan` per block carrying the block's own
label. `TASK-048`'s ask arrives as a side effect.

---

## 4. The lattice after ADR-0018

```
engine  >  workflow  >  agency  >  measurement  >  kernel  >  adapters  >  ports  >  domain
```

```
src/aether/
├── domain/
│   ├── effects.py       ReadArgs/WriteArgs/ShellArgs/ApplyPatchArgs  ← moved from composition.py (A1)
│   ├── context.py       ContextBlock, Layer
│   ├── envelope.py      the shared node-payload base (A7)
│   └── config.py        RunConfig, ModelRoute, AblationFlags
├── agency/                                    ← NEW, mutable capability layer
│   ├── capabilities/    sources · assembler · inference · parsers · mutation · edit_format
│   ├── context/         assembler.py (TASK-056) · compactor.py (TASK-024)
│   ├── roles.py         the RoleSpec catalog
│   └── registry.py      name → capability, frozen at composition (I6)
├── workflow/            step · validator · executor · strategies · nodes/  (TCB)
├── measurement/ · kernel/ · adapters/ · ports/                              (unchanged)
├── engine.py            takes ONE RunConfig
└── composition.py       wiring only; no payload types
```

`agency/` still cannot import `workflow/`, `measurement/` or the evaluator — the TCB direction is
unchanged, and that is the condition ADR-0018 would be rejected on if it failed.

---

## 5. Composition constructs (M3, `TASK-059`/`TASK-060`)

### 5.1 `ExecutionStrategy` — loop constructs as data

`executor.py` hard-codes two traversals: `_topological_order` (line 96 — a 1:1 `edge_map` that
silently drops a second outgoing edge) and `_run_repair_unroll` (line 213).

```python
# workflow/strategies.py — TCB, same status as the executor
class ExecutionStrategy(Protocol):
    async def advance(self, ctx: ExecCtx, region: Region, payload: Any) -> Any: ...

LinearStrategy        # today's _topological_order
BoundedRepeatStrategy # today's _run_repair_unroll, generalised
BestOfNStrategy       # TASK-035 — N children of one parent lease, declared join
CascadeStrategy       # BoundedRepeat with a per-iteration override table
```

The escalating rescue cascade then needs no schema change:

```yaml
repair:
  strategy: cascade
  max_iterations: 3
  per_iteration:
    - { model: "qwen2.5-coder:7b" }      # free
    - { model: "qwen2.5-coder:7b" }      # free
    - { model: "deepseek/deepseek-v4" }  # paid rescue — only ~20% of tasks reach here
```

**The constraint that does not move:** the graph stays acyclic and every bound stays *static*. A
strategy may not introduce a runtime-unbounded loop; `check_bounded_iteration` extends to validate
each strategy's own bound.

### 5.2 Topology fragments — subgraph reuse

Seven files in `workflows/` repeat the same `apply → evaluate` pair and repair-block shape. One
additive schema change (`schema_version: 1.1.0`):

```yaml
# workflows/fragments/edit_and_judge.yaml
fragment_id: edit_and_judge
inputs:  { patch: GeneratedPatch }
outputs: { verdict: EvaluatedCandidate }
nodes:  [ apply, evaluate, repair ]
repair: { strategy: bounded_repeat, from_node: evaluate,
          via_nodes: [repair, apply], back_to: evaluate, max_iterations: 3 }
```

```yaml
# any topology
- { id: tail, use: edit_and_judge }
```

**Three rules make it safe:**

1. **Expand, then validate.** `load_topology()` inlines fragments and namespaces their node ids
   (`tail.apply`) *before* `validate_topology()` runs. All five static checks operate on the
   expanded graph and need **no modification** — a fragment cannot smuggle a node past the judge,
   because by validation time there are no fragments.
2. **Fragments are hash-pinned**, like topologies. ADR-0014: *every cross-reference is by hash,
   never by filename.*
3. **Fragments declare socket types** so the socket check can verify a use site.

Fragments are TCB-adjacent (the expander runs before the validator) and need their own malformed
fixtures: cyclic self-reference, judge-bypass, node-id collision.

---

## 6. Out-of-process extraction (ADR-0001)

`spec.md` §4's port rules — every method `async`, no `Path`/handle/callable/generator/live object
— are exactly what makes a boundary relocatable. `EffectRequest.descriptor` and
`EffectOutcome.result_json` are already JSON.

```
STEP 1  in-process Python adapter                      ← today
STEP 2  in-process adapter behind a JSON codec         ← already true
STEP 3  out-of-process sidecar
        composition.py binds `read` → SidecarClient("unix:///run/aether-ws.sock")
```

**Only `composition.py` changes.** Not the node, not the executor, not the topology, not the port.

| Component | Trigger that would justify a sidecar |
| :--- | :--- |
| `Indexer` (Rust) | RT-1/RT-2 crossed on a 1M-LOC corpus — ADR-0001's own open item |
| `Workspace` (Go) | Worktree creation crossing RT-3 under Best-of-N fan-out |
| `SandboxRunner` (Go) | Container orchestration only |
| **`Evaluator`** | **Never.** TCB residency in `measurement/` is what makes `tcb-isolation` *select* it. Moving the judge out of process moves it out of the contract |

Wire format is decided by I2/I3: **JSON, with Pydantic models as the schema of record**. A sidecar
becomes one more adapter parameter in the existing conformance suite — no IDL, no gRPC.

```json
{ "jsonrpc": "2.0", "method": "indexer.search_symbols", "id": 1,
  "params": { "worktree_path": "repo/src", "query": "def parse_diff", "max_results": 5 } }

{ "jsonrpc": "2.0", "method": "sandbox.run", "id": 2,
  "params": { "container_spec": { "image_digest": "sha256:…", "network": "none",
                                  "read_only_root": true },
              "test_command": "pytest tests/unit/test_core.py" } }
```

**The prerequisite for all of it is A1.** A component cannot be extracted while its payload types
live in the module that imports its concrete peers.

---

## 7. `RunConfig` — one typed engine input

```python
# domain/config.py
class RunConfig(Frozen):
    topology: TopologyRef          # hash or path
    manifest: ManifestRef
    split: Literal["dev", "holdout", "sealed"]
    routes: tuple[ModelRoute, ...] # per-role endpoint; credentials by env NAME, never value
    budget: BudgetDims
    sandbox: SandboxConfig
    seed: int
    ablation: AblationFlags
    mode: Literal["benchmark", "interactive"]
```

Three consequences at no extra cost:

1. **`sha256(RunConfig)` is `measurement.md` §6's instrument tuple**, replacing hand-assembly that
   can silently omit a field.
2. **Client forms generate from `model_json_schema()`** — a React form, a `--help`, and a TUI
   panel are three renderers of one schema.
3. **Ablations become named arms.** Test-source injection is `ablation.inject_test_source`,
   default `False`, and any run using it says so in its own config hash.

**The engine refuses `split: holdout | sealed` while `noise-floor.md` holds no number.**
Enforcement in the engine, not a warning in a client — a config layer that makes runs easy to
launch makes premature runs equally easy.

### 7.1 The two modes have opposite requirements

| | `benchmark` | `interactive` |
| :--- | :--- | :--- |
| An `ASK_*` policy decision | **Fails closed** — a human in the loop is a human in the measurement | Prompts the operator |
| Wall clock | Bounded by the lease | May block |
| Retrieval | Deterministic, seeded | May accept operator hints |
| Cross-task memory | Off, or split-scoped | On |

---

## 8. Reversal conditions

- **The capability layer**: if after two sprints no role has been defined by composing *existing*
  capabilities — i.e. every new node still needs a new capability implementation — the layer is
  unearned indirection and `ModelNode` collapses back into per-role classes.
- **Fragments**: if fewer than three topologies share a fragment six months after it lands, the
  expander is deleted. A composition operator with one user is worse than copy-paste, because it
  hides the graph.
- **Strategies**: if `TASK-035` lands cleanly as a strategy but no second strategy is ever added,
  the seam is fine but must not grow — strategies are TCB and each one is an audit surface.
- **`RunConfig`**: none. A typed engine input is a precondition for every client surface in
  `spec.md` §8 and for `measurement.md` §6's instrument tuple.
