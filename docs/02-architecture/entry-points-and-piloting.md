---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Entry Points & Multi-Channel Piloting**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **One Core, Many Cockpits**

All SAGIHA invocation channels map to a single headless async signature:

```python
async def execute(
    task: TaskSpec,
    context: RunContext,
) -> AsyncIterator[Event]: ...
```

Adding a cockpit channel requires **zero core changes**. Non-coding workloads set a distinct [execution profile](./execution-profiles.md) inside `TaskSpec`.

```
  CLI / TUI ─┐
  IDE (MCP) ─┤
  Bot pilot ─┼─→ TaskSpec ─→ Orchestrator.execute() ─→ Event stream ─→ Client
  CI / cron ─┤
  A2A peer ──┘
```

## **Channels**

1. **CLI / TUI**: Built with `typer` and `rich`. Operates as an `Observer` on the [EventBus](./event-bus-and-hooks.md).
   ```bash
   sagiha run "fix test" --cassette .sagiha/cassettes/default.json
   sagiha replay <run-id> --verify --cassette .sagiha/cassettes/default.json
   ```
2. **Headless / CI**: Non-TTY execution. Exit codes reflect `GateReport`. Used by benchmark runs and the [RHI outer loop](../04-workflows-and-loops/rhi-outer-loop.md).
3. **Remote Pilot (Bots)**: Out-of-repo gateway service translating chat messages into `TaskSpec` submissions and streaming events via A2A/SSE. Chat inputs are treated as `untrusted-data`.
4. **IDE (MCP)**: SAGIHA acts as an MCP server exposing `submit_task`, `get_status`, and `stream_events`.
5. **A2A Peer**: Remote agent-to-agent delegation via standard [Protocols](../03-contracts-and-models/protocols-mcp-a2a.md).

## **Voice Subsystem**

* **STT (Input)**: Transcribes speech into an ordinary `TaskSpec`.
* **TTS (Output)**: An `Observer` narrating filtered events (`StepCompleted`, `ApprovalRequested`, `RunCompleted`). Drops frames under backpressure without stalling the core loop.

## **Mid-Run Steering**

`UserMessageReceived` events trigger a new, immutable `TaskSpec` revision, appending instructions to the prompt tail without invalidating the cached prefix.

## **Streaming & Concurrency Contract**

* **SSE JSON Events**: Resumable via `?since=<step_id>`, redacted at the boundary prior to serialization, backpressure-safe (drops frames for slow consumers).
* **Session Model**: Bounded by `ResourceGovernor.max_concurrent_runs`. Each run is linked to a worktree and addressable across channels via `run_id`.
