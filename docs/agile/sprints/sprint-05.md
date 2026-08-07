---
status: rationale
updated: 2026-08-07
---

# Sprint 05 Plan — The Capability Layer

* **Goal**: Create `agency/`, extract the capability protocols, collapse three duplicated node classes into one `ModelNode` plus a role catalog, and give the engine a single typed input.
* **Target Milestone**: [M1b](../roadmap.md#phase-matrix--dependencies)
* **Tripwire Window**: 8 Business Days
* **Entry condition**: Sprint 4 Tasks 1–4 closed. **Task 5 (the floor) need not have completed** — this sprint produces no number and may run alongside it.
* **Source**: [`capability_layer.md`](../../development/capability_layer.md)

> **This sprint adds no capability and claims no lift.** It changes what is *cheap to try*. Every mechanism it unblocks still has to clear the floor on its own ablation ([`spec.md` §7](../../spec.md#7-measurement)), and one that does not clear is deleted rather than left dormant.

**Why it is sequenced before M2.** Three M2/M3 tasks — `TASK-031`/`TASK-056` (five-layer assembler), `TASK-024` (compaction), `TASK-033` (cache sequencing) — all target `src/aether/agency/context/`. That package does not exist, and the current `.importlinter` lattice makes `aether.agency` an *independent sibling* of `aether.workflow`, so a `WorkflowStep` cannot import from it at all. M2 cannot start until Task 1 lands.

---

## Sprint Backlog Items

### Task 1: ADR-0018 + the Lattice Change (`TASK-053`)
* **Target Seam**: `.importlinter`, `docs/decisions/0018-agency-below-workflow.md`, `docs/spec.md` §3
* **Specification Pointer**: [`spec.md` §3](../../spec.md#3-structure), [ADR-0006](../../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
* **Acceptance Criteria**:
  1. `aether.agency` moves from an independent sibling of `aether.workflow` to the layer **beneath** it. `workflow/` (TCB executor, validator, strategies) drives mutable capabilities in `agency/`.
  2. **`lint-imports` stays 9/9 with `agency` populated.** A contract that selects zero modules forbids nothing and passes green — `tests/unit/test_path_constant_drift.py` enforces that and must keep doing so.
  3. The TCB direction is **unchanged**: `agency/` still cannot import `workflow/`, `measurement/`, or the evaluator. The thing that judges still cannot be reached from the thing being judged.
  4. The ADR carries a reversal condition.
* **Why it matters**: `spec.md` §3 has declared `agency/` since M0. The sibling arrangement was chosen when the package was empty and has no defender now — it is the sole reason prompt logic lives in `workflow/nodes/` and gets duplicated there.

### Task 2: `ContextSource` (`TASK-054`)
* **Target Seam**: `src/aether/agency/capabilities/sources.py`, `src/aether/agency/registry.py`
* **Specification Pointer**: [ADR-0010](../../decisions/0010-context-prefix-layers.md), [ADR-0015](../../decisions/0015-taintgate-provenance-model.md)
* **Acceptance Criteria**:
  1. One protocol, one registry, `get_source(name)` raising **at construction** — `edit_format.py`'s template verbatim, including `UnknownEditFormat`'s precedent that a topology naming an unimplemented thing fails at load, not at the moment the first answer arrives.
  2. `EntryFileSource`, `CurrentFileSource`, `GateOutputSource`, `PreviousAttemptSource`, `SymbolSource`. One byte-budget policy and one `missing` semantics, replacing the two divergent loops in `retrieve.py:67-93` and `repair.py:122-132`.
  3. **A block's `Provenance` label is a property of its source, declared once.** It is currently a decision made ad hoc at 10 `TaintSpan(...)` call sites across three files, which is how repository content and test tracebacks both came to be labelled `AGENT`.
  4. `SymbolSource` wraps `TreeSitterIndexer` — a conformance-passing adapter that is today reachable from no node and no topology.

### Task 3: `Inference` + `OutputParser` (`TASK-055`)
* **Target Seam**: `src/aether/agency/capabilities/{inference,parsers}.py`
* **Acceptance Criteria**:
  1. The model-call-and-collect idiom exists once, not four times (`architect.py:88`, `architect.py:142`, `repair.py:180`, `generate.py:146`).
  2. Reservation uses `completion_tokens` for a completion ceiling. All four sites currently reserve `max_tokens` in the `prompt_tokens` dimension — one bug, four copies.
  3. `ToolLoop` (today's `MAX_ROUNDS` loop, reachable only from `generate`) is usable by **any** role. A planner that wants to list the repo currently cannot.
  4. `EditFormat` is left alone. It already has the right shape and is the template the rest of this follows.

### Task 4: `PromptAssembler` — the Five Layers (`TASK-056`, was `TASK-031`)
* **Target Seam**: `src/aether/agency/context/assembler.py`
* **Specification Pointer**: [ADR-0010](../../decisions/0010-context-prefix-layers.md), [`spec.md` §2 (I10)](../../spec.md#2-invariants)
* **Acceptance Criteria**: unchanged from `TASK-031`.
  1. Layer order L1 system/policy · L2 tool schemas · L3 repo brief · L4 task · L5 dialogue, append-only within a run.
  2. At most four cache breakpoints.
  3. **CI floor on harness-side byte-identical-prefix stability over a fixed recorded replay** — deliberately *not* a provider-reported hit rate. `cache_control` semantics diverge between providers, `openai_compatible.py:40` records that breakpoints are not emitted there at all, and the local endpoint may expose no cache metric. A gate keyed to a provider metric would be unmeasurable on the reference instrument.
* **Note**: this is `TASK-031` with a home, not an extra task. Prompt layering is currently `f"{instructions}\n\n## Header\n{text}"` inside `architect.py`, so there is no object that holds the layers and nothing to enforce order over.

### Task 5: `ModelNode` + `RoleSpec` (`TASK-057`)
* **Target Seam**: `src/aether/workflow/nodes/model_node.py`, `src/aether/agency/roles.py`
  *(the node stays in `workflow/` — `WorkflowStep` lives in `workflow/step.py`, so a node under `agency/` would be an upward import; see [`capability_layer.md`](../../development/capability_layer.md) §3.1)*
* **Specification Pointer**: [ADR-0007](../../decisions/0007-architect-editor-seam.md), [ADR-0014](../../decisions/0014-workflow-topology-is-data.md)
* **Acceptance Criteria**:
  1. `ARCHITECT`, `EDITOR`, `REPAIRER`, `REFLECTOR` are **data**: a source list, a parser, a role string. Defining a new role adds no class.
  2. **Golden-prompt equivalence test**: every shipped topology produces byte-identical prompts before and after. This is the gate, not unit coverage — the risk in this task is silent prompt drift.
  3. `workflow/nodes/{architect,generate,repair}.py` are deleted once the equivalence test passes. They stay one release, not indefinitely.
  4. Absorbs `TASK-047` and `TASK-046`: the architect and reflector get their first tests, **including a test that the architect's plan reaches the generate node's prompt** — the entire mechanism, currently unasserted — and `reflector` either gets a topology or comes out.

### Task 6: `RunConfig` (`TASK-058`)
* **Target Seam**: `src/aether/domain/config.py`, `src/aether/engine.py`
* **Specification Pointer**: [`spec.md` §8](../../spec.md#8-clients), [`measurement.md` §6](../../measurement.md#6-what-a-claim-needs-before-it-is-published)
* **Acceptance Criteria**:
  1. `engine.run(config: RunConfig)` — one frozen parameter replacing 15 keyword arguments.
  2. `sha256(RunConfig)` **is** `measurement.md` §6's required instrument tuple, replacing hand-assembly in scripts.
  3. CLI, TUI and a future GUI generate their forms from `model_json_schema()`. One schema, three renderers, nothing kept in sync by hand.
  4. **The engine refuses `split: holdout | sealed` while `noise-floor.md` holds no number.** Enforcement in the engine, not a warning in a client — a config layer that makes runs easy to launch makes premature runs equally easy.

---

## Exit Gates

| Gate | Closed by | How it is verified |
| :--- | :--- | :--- |
| `agency/` exists and the lattice holds | Task 1 | `lint-imports` 9/9 with `agency` populated; no contract selects zero modules |
| Retrieval is one path, provenance declared once | Task 2 | `TreeSitterIndexer` reachable from a topology; grep gate — `TaintSpan(` appears in `agency/capabilities/`, nowhere in `workflow/nodes/` |
| One inference implementation | Task 3 | `grep -c "TextDelta)" src/aether/` returns 1 |
| Five layers enforced and measured | Task 4 | Prefix-stability floor in CI over a fixed replay |
| Roles are data | Task 5 | Golden-prompt equivalence green; three node files deleted; `RoleSpec` round-trips through JSON |
| One typed engine input | Task 6 | `test_run_config_covers_engine`; a `holdout` run is refused with the floor empty |

## Explicitly deferred to M2/M3

`TASK-059` (`ExecutionStrategy`) and `TASK-060` (topology fragments) are **TCB and TCB-adjacent** and are not in this sprint. They are the natural next step and they need `TASK-035`'s branching work alongside them; sizing them before the floor reports wall-clock would be the estimate-as-commitment [ADR-0009](../../decisions/0009-gates-are-the-schedule.md) forbids.

`TASK-061` (declarative arm files) follows `TASK-058` and lands with the first real ablation, not before.
