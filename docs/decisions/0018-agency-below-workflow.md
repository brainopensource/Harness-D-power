---
status: normative
updated: 2026-08-07
---
# ADR-0018: `agency/` Sits Below `workflow/`, Not Beside It

**Status**: Accepted · **Date**: 2026-08-08 · **Ratified by**: `TASK-053`, Sprint 5
**Fork**: raised by the abstraction audit

## Context

[`spec.md` §3](../spec.md#3-structure) has declared `src/aether/agency/` with a `context/`
subpackage since M0, and names its contents: the assembler, the compactor, the token counter,
the taint gate. **The package does not exist.**

The reason is recorded in two places already. `workflow/nodes/repair.py`'s module docstring and
[`sprint-03.md`](../agile/sprints/sprint-03.md) both state it: `.importlinter`'s `aether-layers`
contract places `aether.agency` and `aether.workflow` at the **same level, as independent
siblings**, so a `WorkflowStep` in `workflow/nodes/` importing prompt logic from `agency/` would
break a contract that is currently 9-for-9. `TASK-023` therefore left `agency/repair.py` unbuilt
and inlined the prompt into the node, and `STATUS.md` records that as a deviation rather than
papering over it.

Three consequences have accumulated since:

1. **Prompt logic has no home, so it is duplicated.** The model-call idiom appears four times;
   `TaintSpan(...)` is hand-constructed ten times across three node files; "read these files into
   a prompt block" is implemented twice with different error semantics and different byte
   budgets.
2. **Provenance labelling became an ad-hoc decision at ten call sites.** Repository file slices
   and test tracebacks are both labelled `Provenance.AGENT` because each site decided
   independently.
3. **Three funded M2/M3 tasks target a directory that cannot exist.** `TASK-031` (five-layer
   assembler), `TASK-024` (compaction) and `TASK-033` (cache sequencing) all name
   `src/aether/agency/context/` as their target file. M2 cannot start.

The sibling arrangement was a reasonable default when `agency/` was empty and nothing depended on
its position. It has no defender now: it is the sole mechanical reason the duplication exists.

## Decision

**`aether.agency` moves from an independent sibling of `aether.workflow` to the layer directly
beneath it.**

```diff
  layers =
      aether.engine
-     (aether.agency) | aether.workflow
+     aether.workflow
+     aether.agency
      aether.measurement
      aether.kernel
      aether.adapters
      aether.ports
      aether.domain
```

The resulting lattice:

```
engine  >  workflow  >  agency  >  measurement  >  kernel  >  adapters  >  ports  >  domain
```

**`workflow/` holds the TCB execution machinery** — the executor, the validator, the topology
schema, and (later) the strategies. **`agency/` holds the mutable capability layer** — context
sources, the prompt assembler, inference, parsers, roles. The TCB drives mutable capabilities;
that is the correct direction and it is the direction the system already runs in, unwritten.

### What does not change

- **`agency/` cannot import `workflow/`, `measurement/`, or the evaluator.** Layer order forbids
  the first: `agency` sits below `workflow`. It does **not** forbid the second — the proposed
  lattice puts `agency` *above* `measurement`, so layer order alone *permits* `agency →
  measurement`, the ordinary direction for a downward edge. **A dedicated forbidden-import
  contract, `aether-agency-cannot-reach-the-judge`, is what closes that gap**, added in the same
  change as the lattice edit. An earlier draft of this ADR claimed `aether-tcb-isolation` already
  named `aether.agency` as a forbidden importer of `measurement.evaluator`; verified false —
  that contract's `forbidden_modules` list names `aether.agency` as a forbidden *importee* of the
  TCB kernel/measurement modules, not a forbidden *importer* of them, which is the opposite
  direction. Nothing enforced the sentence this ADR was making until the new contract landed.
  *The thing that judges still cannot be reached from the thing being judged* — I7 is untouched,
  and this ADR would be rejected if it were not — but the claim is now backed by a contract this
  ADR names, not by a misreading of an existing one.
- **`kernel/` and `measurement/` still cannot import `agency/`.** Unchanged.
- **`evolution/` still imports no higher than `ports/` and is imported by nothing** (ADR-0006).
- **The dispatch choke point is unchanged.** `agency/` capabilities receive a `DispatchFacade`
  like every node does; they hold no adapter handles.

### What this ADR does not authorise

It does not widen the meta-loop's mutable surface. [ADR-0006](./0006-tcb-boundary-and-meta-loop-authority.md)
governs that, and `agency/` being importable does not make it auto-committable. Capability
*implementations* are code and remain human-PR-only; role *declarations* are data and are
governed by ADR-0006 and [ADR-0014](./0014-workflow-topology-is-data.md) as before.

## Consequences

**Positive.**

- The three funded M2/M3 tasks acquire a legal target directory.
- Prompt assembly, provenance labelling and retrieval each get exactly one implementation, and
  each becomes independently testable and independently ablatable.
- `spec.md` §3 and the enforced lattice agree for the first time. Today the spec describes a
  package the contracts forbid, which is a documented drift, not a design.

**Negative, and accepted.**

- `workflow/` gains a downward dependency on `agency/`, so a change in a capability protocol can
  break a node. That is the ordinary cost of a layer, and it is the direction that keeps the TCB
  on top.
- One more layer in a lattice that is already eight deep. Mitigated by the fact that this layer
  was always specified — it is being filled, not invented.

**Neutral, corrected.** An earlier draft said contract count stays at 9. Verified false at
ratification: Sprint 4's forensic audit (finding F11) had already added a tenth contract,
`aether-workflow-tcb-isolation`, naming the workflow validator and executor as TCB — this ADR
predates that and never accounted for it. **This ADR's own lattice edit adds an eleventh**,
`aether-agency-cannot-reach-the-judge` (see "What does not change" above). Contract count goes
from 10 to 11, and this document is now the second place that undercounted it — the check that
would have caught the first undercount is `tests/aether/agency/test_lattice.py
::test_lint_imports_is_green_on_the_real_tree`, which asserts the literal string `"Contracts: 11
kept, 0 broken."` rather than trusting prose in an ADR to stay current.

## Enforcement

- `lint-imports` must be **11/11 with `agency/` populated**. A contract that selects zero modules
  forbids nothing and passes green, so the check that matters is that the change lands **in the
  same commit as the first real `agency/` file** — the same trap ADR-0006 names for the TCB path
  migration, and the reason `TASK-000` was sequenced as the first PR of Sprint 1.
- `tests/unit/test_path_constant_drift.py` continues to assert no contract selects zero modules.
- A negative test: an import from `agency/` to `workflow/` must make `lint-imports` fail.

## Reversal conditions

- **If `agency/` still holds fewer than three capability implementations two sprints after this
  lands**, the layer is unearned and the contents fold back into `workflow/`, accepting the
  duplication as the cheaper option.
- **If any contract in `.importlinter` has to be weakened to make this work**, the change is
  reverted. The lattice is the enforcement mechanism for I1, I5, I7 and I8; a lattice edit that
  costs a guarantee is not a refactor, it is a regression.
- **If a future task requires `agency/` to import `workflow/`**, that is evidence the split is
  in the wrong place, and the correct response is a new ADR relocating the boundary — not an
  `ignore_imports` entry.

## References

- [`spec.md` §3](../spec.md#3-structure) — the declared tree, unbuilt since M0
- [ADR-0006](./0006-tcb-boundary-and-meta-loop-authority.md) — TCB boundary and the vacuous-migration trap
- [ADR-0010](./0010-context-prefix-layers.md) — what `agency/context/` is for
- [ADR-0014](./0014-workflow-topology-is-data.md) — topologies are data; roles extend the same principle
- [`capability_layer.md`](../architecture/capability_layer.md) — the design this unblocks, and the audit findings (A1–A8) that raised it
