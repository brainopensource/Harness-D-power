---
status: rationale
updated: 2026-08-07
---

# Architecture — Index

**How the system works.** Ten documents, indexed by the question you arrived with. Read the row,
not the folder.

*What is **true** is [`spec.md`](../spec.md). What was **decided** and what reverses it is
[`decisions/`](../decisions/README.md). What is **built** is [`STATUS.md`](../STATUS.md). When one
of these disagrees with `src/aether/`, **the document is the bug**.*

---

## By question

| You are asking | Read | Status |
| :--- | :--- | :--- |
| **How do I write code here?** What patterns, what's forbidden, what's the DoD? | [`coding_guidelines.md`](coding_guidelines.md) | Binding practice |
| What are the port shapes, the skeletons, the pseudocode? | [`core_skeletons_and_protocols.md`](./core_skeletons_and_protocols.md) | Superseded by code where they differ |
| What fields does a schema have, how is a validator wired? | [`schemas_and_contracts.md`](./schemas_and_contracts.md) | Reference |
| What does the system look like end to end? | [`architecture_diagrams.md`](./architecture_diagrams.md) | **Shows the target — parts unbuilt** |
| Runtime, dependencies, sandbox, cost model | [`tech_stack_and_infra.md`](tech_stack_and_infra.md) | Reference |
| **How does a node get built from reusable parts?** `ModelNode`, roles, strategies, fragments, sidecars | [`capability_layer.md`](./capability_layer.md) | Design of record — **M1b** |
| **What is a task, and how do we know it succeeded?** | [`task_types_and_verdicts.md`](./task_types_and_verdicts.md) | Design of record — **M5** |
| **How does the system know things?** Retrieval, indices, graph, short/long-term memory | [`knowledge_and_memory.md`](./knowledge_and_memory.md) | Design of record — **M5** |
| **How does someone extend it without forking?** | [`extension_contract.md`](./extension_contract.md) | Design of record — **M5** |
| **How does it improve itself, and what may it never touch?** | [`self_improvement.md`](./self_improvement.md) | Design of record — **M6** |

## By horizon

The three horizons are [ADR-0019](../decisions/0019-three-horizons-harness-framework-metaloop.md);
the order is not reversible.

```
  H1 HARNESS (M0–M4) ─── built + in flight
     coding_guidelines · core_skeletons_and_protocols · schemas_and_contracts
     tech_stack_and_infra · architecture_diagrams
     capability_layer  ← M1b, the refactor M2 is blocked on

  H2 FRAMEWORK (M5) ──── designed, not built
     task_types_and_verdicts   what a task is, and which judge applies
     knowledge_and_memory      retrieval, graph, the two memories
     extension_contract        third parties, and why data cannot widen capability

  H3 META-LOOP (M6) ──── designed, not built
     self_improvement          propose → screen → admit-or-delete
```

## The three ideas everything else hangs off

**Capability is composed, never copied.** A node is thin; behaviour comes from injected
capabilities — sources, assembler, inference, parser. `ARCHITECT` and `EDITOR` differ by their
source list and their parser and by nothing else. See `capability_layer.md` §3.

**The judge is never reachable from the judged.** I7, restated for non-test verdicts by
[ADR-0020](../decisions/0020-verdict-capability-and-judge-integrity.md): the judge's own
specification — rubric text, model fingerprint, prompt — is TCB data pinned by hash. And a
verdict with `admits: False` may rank but never promote. See `task_types_and_verdicts.md` §3.

**Data cannot widen capability.** Roles, topologies and parameters *name* registered ids; they
cannot define one, and registries are frozen at composition (I6). This is simultaneously the
extension contract's security argument and the meta-loop's authority boundary — the same line
from two sides. See `extension_contract.md` §1.

## Reading order for a new contributor

1. [`coding_guidelines.md`](coding_guidelines.md) — before your first PR
2. [`capability_layer.md`](./capability_layer.md) §1–3 — how a node is built
3. The document your task names; the sprint dev prompt tells you which
