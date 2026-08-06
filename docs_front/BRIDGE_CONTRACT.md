---
status: normative
updated: 2026-08-06
---

# Event Stream Bridge Contract (`docs_front/BRIDGE_CONTRACT.md`)

This normative specification defines the communication protocol between the headless backend engine (`src/aether/engine.py`) and the front-end applications (`apps/cli` and `apps/desktop`).

---

## 1. Protocol Architecture

Communication flows over a **bi-directional WebSocket connection** (or SSE stream for read-only consumers):

```
+------------------------------------+           +------------------------------------+
|  AETHER Backend (src/aether)       |           |  Front-End Client (@aether/core)   |
|                                    |           |                                    |
|  • engine.py                       |  WS / SSE |  • AetherWebsocketClient           |
|  • kernel/bus.py                   | <=======> |  • MockCassettePlayer              |
|  • JSON RPC / Event Catalog        |           |  • Zustand Stores                  |
+------------------------------------+           +------------------------------------+
```

---

## 2. Inbound Event Stream Schemas (Engine $\rightarrow$ Client)

Every event emitted by `kernel/bus.py` conforms to the canonical JSON envelope:

```json
{
  "seq": 1042,
  "run_id": "run_20260806_001",
  "event_type": "NodeExecutionStarted",
  "at": "2026-08-06T16:50:00.123Z",
  "payload": { ... }
}
```

### Key Event Types

| Event Type | Payload Fields | Description |
| :--- | :--- | :--- |
| `RunStarted` | `task_id`, `manifest_hash`, `topology_hash`, `budget` | Emitted when a run starts; establishes execution parameters. |
| `NodeExecutionStarted` | `node_id`, `node_kind`, `input_digest` | Emitted when a node enters execution (triggers active node animation). |
| `NodeExecutionFinished` | `node_id`, `gate_report`, `cost_actuals` | Emitted when a node finishes; updates node state (`Passed`/`Failed`/`None`). |
| `ModelStreamDelta` | `node_id`, `kind`, `text`, `tool_call_delta` | Streaming deltas from `ModelProvider` for real-time turn display. |
| `TaintSpanEmitted` | `span_id`, `label`, `text`, `source` | Emitted when context spans are assembled or produced (used for TaintGate audit). |
| `BudgetLeaseUpdated` | `reserved`, `committed`, `remaining` | Real-time update of integer budget ledger (`usd_micros`, tokens, wall-clock ms). |

---

## 3. Outbound Command Schemas (Client $\rightarrow$ Engine)

| Command | Payload | Description |
| :--- | :--- | :--- |
| `StartRun` | `topology_hash`, `task_id`, `budget_dims` | Enqueues a new execution run. |
| `CancelRun` | `run_id`, `reason` | Releases active leases and halts node execution. |
| `ApproveMutation` | `candidate_hash`, `family_id` | Approves a meta-loop proposed topology or prompt mutation (M4–M5). |
| `RollbackTopology` | `target_hash` | Triggers structural topology rollback to a prior hash pin. |

---

## 4. Deterministic Mock Cassette Engine (`packages/mock-server`)

To enable **parallel front-end development** before the backend implementation in `src/aether/` is completed, `@aether/mock-server` provides a replay engine:

```typescript
export class MockCassettePlayer {
  private cassette: RecordedEventStream;
  
  public loadCassette(name: "swe_bench_pass" | "repair_loop_ablation"): void;
  public play(speedMultiplier: number = 1.0): void;
  public pause(): void;
  public stepForward(): void;
}
```

* **Cassettes**: Stored JSON files representing complete execution runs (including `NodeExecutionFinished`, `ModelStreamDelta`, and `GateReport` events).
* **Zero UI Disruption**: The React components consume `MockCassettePlayer` through the identical `useAetherStream` hook interface used in production WebSocket mode.
