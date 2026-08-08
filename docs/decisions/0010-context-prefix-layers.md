---
status: normative
updated: 2026-08-05
---
# ADR-0010: Five Prefix Layers; the Generated Repo Layer Is Ablated Early at M2

**Status**: Accepted (provisional) · **Date**: 2026-08-05 · **Fork**: F10

## Context

Both proposals wanted a stable, cache-friendly prompt prefix, and both wanted a generated
repository-context layer inside it — one as a five-layer prefix, one as three fixed cache
markers with an AST skeleton map as marker three. Both targeted a >92% cache hit rate.

**Neither had evidence that the repository-context layer helps.** And the one piece of
literature either cited on the question measured this category as *negative-value when
generated*: repository context files did not generally improve success rate, increased
inference cost by >20%, and LLM-generated files **reduced** success by ~3% while
human-written ones improved it by ~4%.

One proposal cited that paper to argue against generic auto-dumps while simultaneously
pinning a machine-generated repo skeleton into its cache. The other has the same exposure.
**The split matters more than the average: generated context is the negative-value half.**

## Decision

**The five layers, in fixed order.** An invariant (I10) gated over a structure defined nowhere
is not enforceable, so the layers are enumerated here and the assembler implements exactly this:

| Layer | Contents | Mutates |
| :--- | :--- | :--- |
| **L1** | System prompt · policy text · standing instructions | Never within a run |
| **L2** | Tool schemas | Never within a run (catalog frozen at composition, I6) |
| **L3** | **Repo brief** — the generated repository-context layer | Never within a run · **this is the ablated layer** |
| **L4** | Task statement | Never within a run |
| **L5** | Dialogue · trajectory · tool output | **Every turn** |

- **At most four `cache_control` breakpoints**, one per L1–L4 boundary. Only L5 moves, so the
  prefix through L4 is byte-stable across a run by construction.
- **Compaction operates on L5 only.** A compaction that would rewrite L1–L4 is a bug by type —
  the assembler exposes no API for it.
- The prompt cache is architecture, not optimization: fixed layer order, explicit breakpoints,
  and a gated CI metric over a fixed replay.
- **The gated metric is harness-side prefix stability** — byte-identical-prefix rate — not a
  provider-reported hit rate. `cache_control` is provider-specific and the B2 local endpoint may
  expose no cache semantics at all, which would leave the I10 floor unmeasurable on the
  reference instrument. Provider hit rate is secondary where available.
- **The generated repository-context layer (L3) ships enabled and is ablated at M2**, measured
  against a hand-authored brief of equal token budget. It is ablated *early*, but the **repair
  ablation goes first** ([ADR-0013](./0013-workflow-dag-phased.md) rev. 2) — it is the larger
  expected effect.
- This layout is the reserved content of the canonical **"context prefix layout"** diagram slot.

## Consequences

- The >92% hit-rate figure is **a target to calibrate against our own replay**, not a figure
  taken from a reference. The first measurement may move it.
- Best-of-N fan-out must be cache-sequenced. Naive fan-out over a shared prefix is a large
  cost multiple, and that is the workload the prefix design exists for.
- If the layer loses its ablation, this design collapses to something very close to the
  three-marker alternative — the gap between the two proposals was one measurement wide.

## Reversal Conditions

**The M2 ablation.** If the generated layer does not clear the noise floor against a
hand-authored brief of equal token budget, **it is deleted, not demoted**.

If it shows *negative* value, that is a finding worth publishing rather than a defect to
hide — it would replicate a published result on our own instruments.
