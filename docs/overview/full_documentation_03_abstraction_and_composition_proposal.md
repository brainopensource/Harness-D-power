# AETHER Full Documentation — Part 3: Harness Abstraction, Capability Composition & Reusable Core

> **Original Source Documents:** [`docs/fixes/proposal_abstraction_and_harness_composition.md`](../fixes/proposal_abstraction_and_harness_composition.md), [`docs/fixes/proposal_architectural_abstraction_and_harness_engineering_gem.md`](../fixes/proposal_architectural_abstraction_and_harness_engineering_gem.md), [`docs/fixes/implemented_sprint_3.5_complete_report.md`](../fixes/implemented_sprint_3.5_complete_report.md).  
> **Purpose:** A complete, condensed reference specification of AETHER's capability abstraction model, generic `ModelNode` architecture, declarative `RoleSpec` catalog, `RunConfig` domain model, and Topology Fragments.

---

## 1. Executive Summary & Problem Diagnosis

Previous node implementations (`ArchitectStep`, `GenerateStep`, `RepairStep`) were monolithic 60–150 line Python classes that inlined prompt assembly, span labeling, model calls, stream reduction, output parsing, and payload plumbing. 

### Verified Code Defects Solved by This Architecture
1. **A1 (Transitive Adapter Imports)**: `workflow/nodes/*` imported concrete adapters and `httpx`. Effect payloads (`ReadArgs`, `WriteArgs`, `ShellArgs`) were moved to `src/aether/domain/effects.py`.
2. **A2 (`_worktree_path` Duplication)**: Duplicated in 4 separate files (including inside the TCB `evaluator.py`). Refactored into a single method on `WorktreeRef`.
3. **A3 (Completion Ceiling Distortion)**: `architect.py`, `generate.py`, and `repair.py` reserved prompt token budgets using `self._max_tokens` (a completion limit). Fixed by separating prompt reservation from completion limits.
4. **A4 (Ad-hoc Provenance Labeling)**: `TaintSpan(...)` was hand-constructed at 10 call sites. Replaced by `ContextBlock` where provenance is set automatically by the source.
5. **A5 (Divergent File Reading Loops)**: `retrieve.py` used a byte budget; `repair.py` swallowed errors. Replaced by unified `EntryFileSource`.
6. **A6 (String-Concatenated Prompting)**: Replaced by `LayeredAssembler` enforcing L1–L5 prompt layers ([ADR-0010](../decisions/0010-context-prefix-layers.md)).

---

## 2. The 6 Core Capability Protocols (`src/aether/agency/capabilities/`)

Instead of writing custom node classes for every task, AETHER breaks node execution into **6 reusable capability protocols**:

```
+-----------------------------------------------------------------------------------+
|                        SIX CORE CAPABILITY PROTOCOLS                              |
+-----------------------------------------------------------------------------------+
| 1. ContextSource      --> What context goes in the prompt?                       |
|                           (EntryFileSource, SymbolSource, GateOutputSource)       |
| 2. PromptAssembler    --> How are L1–L5 layers ordered and cache-pinned?          |
|                           (LayeredAssembler with <= 4 cache_breakpoint pins)     |
| 3. Inference          --> How is the LLM invoked and reduced?                     |
|                           (SingleTurn, ToolLoop)                                 |
| 4. OutputParser       --> How is the LLM output parsed?                           |
|                           (EditFormatParser, PlanParser, PassthroughTextParser)  |
| 5. WorkspaceMutation  --> How are edits applied to the worktree?                 |
|                           (PatchApply, WholeFileWrite)                           |
| 6. Verdict            --> How is candidate code evaluated? (CLOSED TCB)           |
|                           (RealEvaluator - deliberately not pluggable - I7)      |
+-----------------------------------------------------------------------------------+
```

---

## 3. Generic `ModelNode` & Declarative `RoleSpec` Catalog

Redundant model-calling node classes (`ArchitectStep`, `GenerateStep`, `RepairStep`, `ReflectorStep`) are merged into a single **20-line `ModelNode` class** parameterized by declarative `RoleSpec` data definitions:

```python
# agency/roles.py — Data Catalog
ARCHITECT = RoleSpec(
    role="architect",
    sources=(EntryFileSource(), InstructionsSource()),
    parser=PlanParser(),
)

EDITOR = RoleSpec(
    role="editor",
    sources=(InstructionsSource(), PlanSource(), EntryFileSource()),
    parser=EditFormatParser("whole_file_codeblock"),
)

REPAIRER = RoleSpec(
    role="repairer",
    sources=(InstructionsSource(), PlanSource(), EntryFileSource(), GateOutputSource(tail=3000)),
    parser=EditFormatParser("whole_file_codeblock"),
)

REFLECTOR = RoleSpec(
    role="reflector",
    sources=(GateOutputSource(tail=2000), PreviousAttemptSource()),
    parser=LessonParser(),
)
```

---

## 4. `RunConfig` Domain Model & Schema Autogeneration

Loose keyword parameters in `engine.py` are replaced by a single, frozen, JSON-serializable **`RunConfig` domain model**:

```python
class RunConfig(Frozen):
    topology: TopologyRef          # Hash or path
    manifest: ManifestRef          # Benchmark manifest
    split: Literal["dev", "holdout", "sealed"]
    routes: tuple[ModelRoute, ...] # Endpoint credentials & model routing per role
    budget: BudgetDims             # Maximum USD and token ceiling
    sandbox: SandboxConfig
    seed: int
    ablation: AblationFlags
```

* **Autogenerated UI Forms**: `RunConfig.model_json_schema()` autogenerates React forms, CLI `--help` flags, and Ink TUI panels automatically.
* **Deterministic Runs**: Every run is identified and reproduced via `sha256(RunConfig)`.

---

## 5. Topology Fragments (`fragment_id`)

Sub-DAG workflows (such as `edit_and_judge` or `retrieve_and_plan`) are defined once as reusable **Topology Fragments** and referenced in higher-level topologies via `use: fragment_id`:

```yaml
# workflows/fragments/edit_and_judge.yaml
fragment_id: edit_and_judge
inputs:  { patch: GeneratedPatch }
outputs: { verdict: EvaluatedCandidate }
nodes:
  - { id: apply,    kind: apply,    budget: { wall_clock_ms: 30000 } }
  - { id: evaluate, kind: evaluate, budget: { wall_clock_ms: 900000 } }
  - { id: repair,   kind: model,    params: { role: repairer } }
edges:
  - { from: apply, to: evaluate }
repair:
  strategy: bounded_repeat
  max_iterations: 3
```

Topologies include fragments natively:
```yaml
# workflows/decomposed_planning_v2.yaml
topology_id: decomposed_planning_v2
nodes:
  - { id: retrieve,  kind: retrieve }
  - { id: architect, kind: model, params: { role: architect } }
  - { id: editor,    kind: model, params: { role: editor } }
  - { id: tail,      use: edit_and_judge }  # Fragment expanded before static validation
```

---

## 6. Out-of-Process Compiled Sidecars (Rust / Go)

Because all wire ports in `src/aether/ports/` adhere to **Invariant I3 (Wire Serializability)**:
1. Payloads use JSON-RPC descriptor strings over unix domain sockets (`unix:///run/aether.sock`).
2. Heavy CPU operations (e.g. `TreeSitterIndexer` in Rust or `PodmanSandbox` in Go) can move out-of-process without changing callers, topologies, or TCB dispatch logic.
3. The port implementation in `composition.py` is simply swapped to `SidecarClient("unix:///run/aether.sock")`.
