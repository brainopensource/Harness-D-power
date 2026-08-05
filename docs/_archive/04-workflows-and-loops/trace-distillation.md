---
status: historical
updated: 2026-07-31
---
# **Trace Distillation**

Distillation exports typed, replayable trajectories into SFT/DPO training datasets (Tier B in [RHI outer loop](./rhi-outer-loop.md)).

## **Interface**

CLI command: `sagiha export --format sft|dpo`. Reads from `TrajectoryStore` using step/message schemas from `src/sagiha/domain/trajectory.py`.

## **Eligibility Criteria**

A trajectory is eligible for export **iff** all four conditions are met:

| Criterion | Requirement & Rationale |
| :--- | :--- |
| **`admitted`** | Gate evaluation passed. |
| **Replay-verified** | Trajectory reproduces accurately. |
| **$\neg$`tainted`** | Untrusted content was never ingested (prevents prompt injection persistence; see [T7](../02-architecture/security-and-threat-model.md)). |
| **Within-budget** | Run completed without budget cap truncation. |

## **DPO Preference Pairs**

DPO preference pairs are constructed from **Best-of-N siblings on identical prefixes** (`v2-S4`): identical task and context prefix, paired between one admitted candidate and one rejected candidate.

## **Dependencies**

Requires full assistant `Message` persistence on `TrajectoryStep` (`v2-S2` / PR-2.5) to capture text-only turns alongside tool calls and results.

*Lands in `v2-S4`.*
