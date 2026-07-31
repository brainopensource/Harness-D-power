---
status: normative
updated: 2026-07-31
---
# **Trace Distillation**

Every run already writes a complete, typed, replayable trajectory. Distillation is the exporter
that turns those trajectories into training data — the Tier B activity in the
[RHI outer loop](./rhi-outer-loop.md).

## Interface

`sagiha export --format sft|dpo`. The exporter reads the `TrajectoryStore`; it defines no schema of
its own. Step and message shapes live in `src/sagiha/domain/trajectory.py`.

## Eligibility — all four, no exceptions

A trajectory is exportable **iff**:

| Criterion | Why |
| :--- | :--- |
| **`admitted`** | The gates passed. Post-`v2-S1` this means something; before it, nothing |
| **replay-verified** | The trajectory reproduces. An unverifiable trace is not evidence of anything |
| **¬`tainted`** | The run never ingested untrusted content (see [T7](../02-architecture/security-and-threat-model.md)). Training on attacker-influenced trajectories is a persistence mechanism for prompt injection — the one failure mode that survives the run that caused it |
| **within-budget** | The run did not hit its cap. A truncated run is not a demonstration of success |

The taint criterion is the one most likely to be dropped under dataset-size pressure. It is the
one least safe to drop.

## DPO pairs

Preference pairs come from **Best-of-N siblings on identical prefixes** (`v2-S4`): same task, same
context up to the divergence point, one admitted candidate and one rejected. Shared prefixes are
what make the pair a clean signal about the decision rather than about the setup — which is why
this waits for BoN rather than pairing across unrelated runs.

## Dependency

Requires the full assistant `Message` on `TrajectoryStep` — today steps persist only `tool_calls`
and `tool_results`, dropping text-only turns. That gap is fixed in `v2-S2` (PR-2.5) for resume and
replay correctness; the exporter is its second consumer, which is why it is done once, there.

*Lands `v2-S4`.*
