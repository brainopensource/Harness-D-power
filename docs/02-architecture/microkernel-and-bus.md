---
status: normative
updated: 2026-07-29
---
# **Native Async Microkernel & Event Bus**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Overview**
The orchestration engine is a lightweight `AsyncStateMachine` event-bus microkernel in Python >=3.13. It owns the single dispatch choke point between intent and effect.

## **Key Design Features**

* **Zero Framework Lock-in**: decoupled from external agent frameworks; LangGraph and similar are supported strictly as optional adapters behind the `Orchestrator` port.
* **Event-Stream Orchestration**: non-blocking async event bus with step checkpointing and OpenTelemetry instrumentation, following the **OTel GenAI semantic conventions** so ecosystem tooling works without bespoke adapters.
* **One Source of Truth for Traces**: The EventBus is the single source of truth. Both the TrajectoryStore and the OTel exporter subscribe to it independently. Neither is derived from the other — deriving a durable audit log from a sampled telemetry pipeline would corrupt it.

## **Determinism**

LLM calls are not reproducible even at temperature zero, and model versions drift underneath a running system. What the kernel guarantees is **record/replay determinism**:

* Every model call and tool result is recorded.
* Replay serves recorded observations rather than re-executing.
* A recorded trajectory therefore replays identically, forever, with no API calls.

This is what makes the orchestrator unit-testable at Day 0. The cassette adapter implements the same `ModelProvider` Protocol as the live client, so the entire kernel can be exercised in CI at zero cost — the cheapest testability win available in the whole design.

## **Effect Classification and Replay Safety**

Time-travel debugging over an agent that touched a filesystem is only sound if replay knows what it may repeat. Every tool declares an `EffectClass`:

| Class | Replay behavior |
| :---- | :---- |
| `PURE` | Safe to re-execute |
| `IDEMPOTENT` | Re-execution converges; may re-run under policy |
| `DESTRUCTIVE` | **Never** re-executed; always served from the recorded observation |

Without this, replaying a trajectory containing `git push` or `rm -rf` would perform it again.

## **Checkpointing**

Checkpoints are **git commits inside the worktree**, one per step. This single choice unifies checkpoint, rollback, and audit at negligible cost, gives every intermediate state a diffable identity, and makes bisecting an agent's reasoning trivial. Combined with cassette replay, it yields full reconstruction of any past run.

## **Trajectory Identity Is a DAG**

Steps are identified by `(run_id, branch_id, seq, parent)`, not a monotonic integer. System 2 explores parallel candidates, and per-step scoring requires ancestry; a linear counter cannot represent the branching structure it is meant to score. See [Domain Schemas](../03-contracts-and-models/domain-schemas.md).
