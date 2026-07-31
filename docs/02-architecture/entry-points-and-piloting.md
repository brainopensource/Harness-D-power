---
status: rationale
retrieval: excluded
updated: 2026-07-29
---
# **Entry Points & Multi-Channel Piloting**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **One Core, Many Cockpits**

Every way of driving SAGIHA reduces to the same headless call. There is no "CLI mode" or "bot mode" inside the kernel — those are clients of one interface.

```python
async def execute(
    task: TaskSpec,
    context: RunContext,
) -> AsyncIterator[Event]: ...
```

All cockpits (TUI, SSE, TTS) subscribe to this event stream. TrajectoryStep is a persistence-shaped type built by the TrajectoryStore observer, not a streaming contract.

A task spec goes in; a stream of typed events comes out. Everything below is a translation layer over that signature plus an [EventBus](./event-bus-and-hooks.md) subscription.

The signature is also what generalizes the harness beyond coding. Work that needs no worktree — a
question, a review, a conversation — selects a different [execution profile](./execution-profiles.md)
**inside the `TaskSpec`**, not through a different entry point. There is no `execute_chat()`: a second
entry point would fork the event stream every cockpit subscribes to, and "adding a channel requires
zero core changes" would stop being true the first time a channel only spoke one of them.

```
  CLI / TUI ─┐
  IDE (MCP) ─┤
  Bot pilot ─┼─→ TaskSpec ─→ Orchestrator.execute() ─→ Event stream ─→ back to caller
  CI / cron ─┤
  A2A peer ──┘
```

The architectural claim worth stating plainly: **adding a channel requires zero core changes.** If a proposed channel would require one, that is evidence the headless boundary is wrong, not that the channel is special.

## **Channels**

### 1. CLI / TUI — the reference client

`typer` for commands, `rich` for rendering. The TUI is an `Observer` on the event bus with no privileged access whatsoever — it sees exactly what a remote pilot sees.

> **Sprint 3a closed (2026-07-30)** ([STATUS.md](../STATUS.md)). `sagiha run <goal>` and
> `sagiha replay <run_id> --verify` are available now, cassette-driven only. `--spec`/`--autonomy`
> flags and `trajectory show` below remain **target UX**, not yet implemented.

```bash
sagiha run "fix the failing test in tests/test_parser.py" --cassette .sagiha/cassettes/default.json
sagiha run --spec task.yaml --autonomy hybrid    # planned — not yet implemented
sagiha replay <run-id> --verify --cassette .sagiha/cassettes/default.json
sagiha trajectory show <id>                      # planned — not yet implemented
```

Interactive approval prompts are the CLI's rendering of `ApprovalRequested`; they are not a kernel feature. Under `--autonomy scheduled` the same event routes to a notifier instead.

### 2. Headless / CI

The same entry point with no TTY. Exit code reflects the terminal `GateReport`; the trajectory is written for later inspection.

> **Planned — Sprint 3** (autonomous/scheduled profiles harden further in later blocks).

```bash
sagiha run --spec .sagiha/tasks/nightly-lint.yaml --autonomy autonomous --json
```

This is also how the [RHI outer loop](../04-workflows-and-loops/rhi-outer-loop.md) and benchmark runs invoke the agent — the loop is a client of its own harness, which is what keeps the headless path honest.

### 3. Remote Pilot (Clawdbot / Telegram / Slack / WhatsApp / Discord)

**A separate, disposable service — never part of this repository.**

```
Telegram ──→ sagiha-bot ──A2A/SSE──→ SAGIHA ──events──→ sagiha-bot ──→ chat
```

`sagiha-bot` translates chat messages into `TaskSpec` submissions, streams events back as message edits, and renders `ApprovalRequested` as an inline keyboard. It holds no harness logic.

Keeping it out-of-repo is deliberate: messaging platform APIs churn far faster than an architecture should, and a disposable pilot layer can be rewritten or abandoned without touching the engine. The bot is a **client**, subject to the same policy and grants as any other — it does not get elevated authority for being convenient.

Chat-originated task text is **untrusted input**. It sets the goal; it does not carry authority to widen grants or change autonomy level.

### 4. IDE (VS Code / Cursor) — via MCP

SAGIHA runs as an **MCP server**, exposing `submit_task`, `get_status`, and `stream_events`. Any MCP-capable editor becomes a cockpit with no bespoke extension.

This inverts the usual relationship — the harness that *consumes* MCP tools also *serves* MCP — and it is why no VS Code-specific code is needed.

### 5. A2A Peer

For genuinely remote agent-to-agent delegation, per [Protocols](../03-contracts-and-models/protocols-mcp-a2a.md). Deferred until a real remote peer exists; the entry point already satisfies its shape.

## **Voice — Both Directions Are Subscribers**

Neither direction touches the kernel.

* **Speech-to-text (input)**: a pilot client transcribes audio and submits an ordinary `TaskSpec`. Indistinguishable from typing.
* **Text-to-speech (output)**: an `Observer` subscribed to a filtered event slice — `StepCompleted`, `ApprovalRequested`, `RunCompleted` — narrating summaries.

The observer contract does the work here: narration is bounded, drops frames under backpressure, and a failing TTS engine is disabled for the run rather than stalling the agent. Voice is genuinely plug-and-play *because* the event bus was specified with these properties, not by coincidence.

## **Mid-Run Steering**

* A `UserMessageReceived` event type
* When received, the orchestrator creates a new `TaskSpec` revision (TaskSpec is frozen — new revision, not mutation)
* The new revision appends to the prompt tail (cache-friendly)
* Active plan and retrieval set may be invalidated by the revision
* This is the dominant interaction mode and must be supported from S1

## **Streaming Contract**

Remote channels receive newline-delimited JSON events over SSE. Three rules keep long-running remote sessions viable:

* **Resumable**: clients pass `?since=<step_id>` to replay from the trajectory after a disconnect. Long autonomous runs outlive mobile connections, so this is not optional.
* **Redacted at the boundary**: secret scrubbing happens before serialization, once, in the streamer — not in each client.
* **Backpressure-safe**: a slow consumer drops frames and is told it did, rather than applying backpressure to the kernel.

## **Session & Concurrency Model**

One run owns one worktree. Multiple concurrent runs are bounded by `ResourceGovernor` (`max_concurrent_runs`), and a run is addressable by `run_id` across every channel — a task started from the CLI can be monitored from chat and approved from an IDE, because all three are views over the same event stream and the same durable trajectory.

Durable approval state is what makes this work: the run parks in `input-required` and waits, independent of which cockpit is currently attached, or whether any is.
