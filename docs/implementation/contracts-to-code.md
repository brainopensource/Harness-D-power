---
status: normative
updated: 2026-07-29
---

# **Contracts to Code**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

The first commit under `src/` is not a feature. It is the contracts, moved out of markdown and into
type-checked Python. This file is the mechanical recipe for that move, and the policy that keeps it
from silently reversing.

## **Why this is the first commit**

Ports and schemas defined in prose cannot be checked. Two revisions of this tree produced two
disagreeing copies of every contract, and the copy retrieval surfaced was the wrong one. That failure
mode does not have a documentation fix — it has a compiler fix.

A `Protocol` is code. In `src/` it is type-checked, refactorable, LSP-navigable, and conformance-
testable; the same text in a `.md` file is a suggestion with good formatting.

## **The invariant**

> **Once a symbol exists in `src/`, its markdown definition is deleted — not synced.**

Syncing is what produced the drift. There is exactly one definition of each contract, and after this
migration it lives in Python. The markdown keeps the *rules and rationale*: why `Workspace` has no
`get_path()`, why `Grant` never crosses a signature, why hard gates are separate from soft scores.

`AGENTS.md` carries the short form: *a `Protocol` or `BaseModel` in a `.md` file is a bug.*

## **Module Mapping**

Source of truth for this migration: [Domain Schemas](../03-contracts-and-models/domain-schemas.md)
and [Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md).

| Markdown section | Target module |
| :--- | :--- |
| Identity & Time | `domain/identity.py` — `utc_now`, `StepId` |
| Tools | `domain/content.py` — `ContentBlock` union, `Message`, `ModelRequest`, `ToolCall`, `ToolResult`, `EffectClass` |
| Trajectory | `domain/trajectory.py` — `TrajectoryStep`, `StepScored`, `StreamEvent` union, `TokenUsage` |
| Trajectory → `Event` | `domain/events.py` — `Event` base **and every event type in the catalog** |
| Work & Evaluation | `domain/work.py` — `TaskSpec`, `AcceptanceCriterion`, `CriterionResult`, `GateReport`, `Edit`, `EditRequest`, `EditResult`, `HunkResult`, `CostSummary`, `SubagentReport` |
| Memory | `domain/memory.py` — `Provenance`, `MemoryRecord`, `RecallQuery`, `Recall` |
| Retrieval & Graph | `domain/graph.py` — `RetrievalHit`, `SymbolRef`, `GraphEdge`, `CoChange`, `DiagnosticItem` |
| Toolchain | `domain/toolchain.py` — `ToolchainInfo`, `TestReport`, `CoverageReport` |
| Control | `domain/control.py` — `Grant`, `Decision`, `RunContext`, `TaskStatus` |
| Port Index (all sections) | `ports/*.py` — one module per functional group, mirroring the index headings |

`domain/` imports nothing from `ports/`. `ports/` imports only `domain/`. Neither imports an adapter.
This is the bottom of the `import-linter` layer graph and it is checked in CI.

## **Required at the same commit**

These are not follow-ups. A contract without them is prose in a `.py` file.

1. **pyright strict passes** on `src/sagiha/domain/` and `src/sagiha/ports/` with zero suppressions.
   A suppression here is the drift arriving through a different door.

2. **`tests/contracts/test_port_shape.py`** — the meta-conformance suite that checks the boundary
   rules mechanically rather than by review:

   ```python
   def test_no_untyped_dict_crosses_a_port(): ...  # rule 1, with the documented exemptions
   def test_every_port_method_is_async(): ...  # remoteability
   def test_all_port_payloads_are_serializable(): ...  # remoteability — see below
   def test_no_grant_in_any_public_signature(): ...  # the CAR invariant
   def test_all_datetimes_are_aware(): ...  # rule 3
   ```

   `test_all_port_payloads_are_serializable` walks every `Protocol` in `ports/`, resolves the
   annotations, and rejects any parameter or return type that is not a Pydantic model, a primitive, or
   a union of those — no `Path`, file handle, callable, generator, or live object. This is the rule
   from [Remoteable Ports](../02-architecture/remoteable-ports.md), and enforcing it on day 1 is what
   keeps a future Rust or Go sidecar an adapter rather than a refactor.

3. **The event catalog becomes generated.**
   [`04-workflows-and-loops/event-catalog.md`](../04-workflows-and-loops/event-catalog.md) is
   hand-written until `domain/events.py` exists, then generated from it by a script run in CI. A
   hand-maintained registry of ~30 events drifts within a month; a generated one cannot.

4. **The markdown deletions land in the same commit** as the Python. Splitting them across two commits
   re-creates the dual source of truth for however long the gap lasts.

## **Order**

1. `domain/` — no dependencies, mechanical transcription.
2. `ports/` — depends only on `domain/`.
3. `tests/contracts/test_port_shape.py` — fails loudly if 1 or 2 cut a corner.
4. Delete the superseded markdown blocks; leave the rules and rationale.
5. Generate the event catalog; wire the generator into CI.

Steps 1–5 are one pull request. It contains no adapters, no kernel, and no behavior — which is what
makes it reviewable in a sitting and correct by inspection.
