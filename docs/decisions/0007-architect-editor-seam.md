---
status: normative
updated: 2026-08-05
---
# ADR-0007: The Architect/Editor Seam Is Built and Ships Off

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: F7

## Context

One proposal wanted a two-model split enabled from Sprint 1: a planning model producing a
conceptual plan with no write tools, and a cheaper editing model producing surgical
search/replace blocks. The other wanted the seam built but shipped disabled behind an
ablation.

The gap was narrower than the fork implied — the first proposal had already suggested a
config switch between single-model and dual-model operation.

The mechanism is plausible and the evidence is mixed. It roughly **doubles per-task cost**.
The archive binds model roles to tiers and requires the scoring role to differ from the
execution role, but **does not endorse splitting the editor** — a related finding, not a
dispositive one.

## Decision

- **Build the seam.** `agency/architect.py` and `agency/editor.py` are decoupled, with the
  boundary between plan and edit explicit.
- **Ship it off.** Enablement is bound to config, defaulting to single-model.
- **Enable only on an M2 ablation** showing a resolve-rate gain whose CI excludes the noise
  floor, at an acceptable cost delta.

## Consequences

- The seam costs little to build and is expensive to retrofit, so building it now is the
  cheap half of the decision.
- Shipping it off means the first capability numbers are not confounded by an unmeasured
  two-model interaction.
- The ablation is cheap because the seam exists: flipping config is one arm.

## Reversal Conditions

**The ablation, in either direction.** If the split clears the noise floor at acceptable
cost, it becomes the default. If it does not, the seam is deleted rather than left dormant —
a disabled code path that nobody measures is debt, not optionality.
