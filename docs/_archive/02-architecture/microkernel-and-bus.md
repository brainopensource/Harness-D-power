---
status: historical
updated: 2026-07-29
---
# **Native Async Microkernel & Event Bus**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Overview**

The core engine is a Python 3.13+ `AsyncStateMachine` microkernel owning the single dispatch choke point between intent and effect.

## **Core Features**

* **Framework Agnostic**: External frameworks (e.g. LangGraph) are supported strictly as optional adapters behind the `Orchestrator` port.
* **Event-Stream Orchestration**: Non-blocking async event bus using **OTel GenAI semantic conventions**.
* **Single Trace Source**: `EventBus` feeds both `TrajectoryStore` (audit/replay) and OTel telemetry independently.

## **Determinism & Replay Safety**

The microkernel guarantees **record/replay determinism** by recording model/tool responses into cassettes. CI uses a cassette `ModelProvider` adapter for zero-cost replay execution.

Tools declare an `EffectClass` to govern replay behavior:

| Class | Replay Behavior |
| :---- | :---- |
| `PURE` | Safe to re-execute. |
| `IDEMPOTENT` | Safe to re-run under policy. |
| `DESTRUCTIVE` | **Never** re-executed; always served from recorded observations. |

## **Checkpointing & Trajectory Identity**

* **Worktree Checkpoints**: Every step creates a git commit inside the worktree, unifying checkpointing, rollback, diffing, and audit.
* **DAG Trajectory Identity**: Steps use `(run_id, branch_id, seq, parent)` tuples to support System 2 parallel candidate exploration. See [Domain Schemas](../03-contracts-and-models/domain-schemas.md).
