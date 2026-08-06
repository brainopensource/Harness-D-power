---
status: normative
updated: 2026-08-06
---

# Event Stream Bridge Contract (`docs_front/BRIDGE_CONTRACT.md`)

This normative specification defines the communication protocol between the headless backend engine (`src/aether/engine.py`) and the front-end applications (`apps/cli` and `apps/desktop`).

> **Event type naming rule**: Event type strings are **generated from `domain/events.py`** with a CI drift check (spec §8). The TypeScript discriminator union in `@aether/core/types/events.ts` MUST be CI-generated from the same source. The event names listed in this document are **provisional** — the canonical names are whatever `domain/events.py` defines. Until that module lands, the front-end uses the names below.

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

### 1.1 Transport Modes

| Mode | Protocol | Direction | Use Case |
| :--- | :--- | :--- | :--- |
| **Live** | WebSocket | Full-duplex | Real-time streaming + commands |
| **Live** | SSE | Server → Client only | Read-only consumers, HTTP fallback |
| **Mock** | In-process | Simulated | Cassette replay, no network dependency |

---

## 2. Shared Type Definitions

The following TypeScript types are generated from backend domain models. Front-end components MUST use these types — no ad-hoc string literals.

### 2.1 GateStatus (tri-state)

Mirrors `domain/gate.py::GateStatus` (spec §7). `NONE` means *unmeasured / instrument error* and **never silently passes** (B4 rule: instrument error ≠ test failure).

```typescript
enum GateStatus {
  PASSED = "passed",
  FAILED = "failed",
  NONE   = "none",   // instrument error — render as amber, never treat as pass
}

interface GateReport {
  gate: string;
  status: GateStatus;
  detail: string;
  instrumentError: string | null;  // populated iff status === NONE
}
```

### 2.2 Provenance (TaintGate labels)

Mirrors `domain/taint.py::Provenance` (ADR-0015).

```typescript
enum Provenance {
  TRUSTED_SYSTEM     = "trusted-system",
  OPERATOR           = "operator",
  AGENT              = "agent",
  UNTRUSTED_EXTERNAL = "untrusted-external",
  UNTRUSTED_DERIVED  = "untrusted-derived",
}
```

### 2.3 BudgetDims

Mirrors `domain/budget.py::BudgetDims`. Integer-only; currency in micro-USD.

```typescript
interface BudgetDims {
  usdMicros: number;         // integer micro-USD
  promptTokens: number;
  completionTokens: number;
  wallClockMs: number;
  concurrencySlots: number;
}
```

---

## 3. Inbound Event Stream Schemas (Engine → Client)

### 3.1 Wire Envelope

Every event emitted by `kernel/bus.py` conforms to the canonical JSON envelope. The backend `StoredEvent` stores `payload_json` as a JSON string; the WebSocket/SSE transport layer **deserializes** it before emission. Front-end drivers receive `payload` as a parsed object.

```typescript
interface BridgeEvent {
  seq: number;              // monotonic sequence number within the run
  runId: string;            // RunId (NewType<string>)
  eventType: string;        // dot-separated, from domain/events.py catalog
  at: string;               // ISO 8601 UTC timestamp (timezone-aware)
  payload: Record<string, unknown>;  // deserialized from backend payload_json
}
```

> **Serialization boundary**: `@aether/core` bridge drivers (`AetherWebsocketClient`, `MockCassettePlayer`) MUST validate inbound events against Zod schemas generated from `domain/events.py` (FI-5). Invalid events are logged and dropped, never forwarded to stores.

### 3.2 Event Type Registry

> **Provisional names.** These will be reconciled with `domain/events.py` when it lands. The payload field names use camelCase in TypeScript; the backend uses snake_case — the bridge driver handles conversion.

#### Run Lifecycle Events

| Event Type (provisional) | Payload Fields | Description |
| :--- | :--- | :--- |
| `RunStarted` | `taskId`, `manifestHash`, `topologyHash`, `budget: BudgetDims` | Run initialized; establishes execution parameters. |
| `RunCompleted` | `summary`, `finalScore` | Run finished successfully. |
| `RunFailed` | `error`, `failedPhase` | Run terminated with error. |

#### Node Execution Events

| Event Type (provisional) | Payload Fields | Description |
| :--- | :--- | :--- |
| `NodeExecutionStarted` | `nodeId`, `nodeKind`, `inputDigest` | Node enters execution (triggers active node animation). |
| `NodeExecutionFinished` | `nodeId`, `gateReport: GateReport`, `costActuals: BudgetDims` | Node finished; updates node state to `Passed` / `Failed` / `None`. |
| `NodeSkipped` | `nodeId`, `reason: "memoization_hit"` | Node skipped due to M2 memoization cache hit (input digest unchanged). |

#### Model Streaming Events

| Event Type (provisional) | Payload Fields | Description |
| :--- | :--- | :--- |
| `ModelStreamDelta` | `nodeId`, `kind: "text" \| "tool_call" \| "usage" \| "stop"`, `text?`, `toolCallDelta?` | Streaming deltas from `ModelProvider` for real-time turn display. |

#### Effect & Security Audit Events

| Event Type (provisional) | Payload Fields | Description |
| :--- | :--- | :--- |
| `EffectAuthorized` | `runId`, `effectClass`, `descriptor`, `ruleId` | An effect was granted by `PolicyEngine` (security audit trail). |
| `EffectDenied` | `runId`, `effectClass`, `descriptor`, `decision`, `rationale` | An effect was rejected (display in taint audit panel). |
| `TaintSpanEmitted` | `spanId`, `label: Provenance`, `text`, `source` | Context span assembled or produced (TaintGate audit). |

#### Budget & Resource Events

| Event Type (provisional) | Payload Fields | Description |
| :--- | :--- | :--- |
| `BudgetLeaseUpdated` | `reserved: BudgetDims`, `committed: BudgetDims`, `remaining: BudgetDims` | Real-time budget ledger update. |
| `BudgetOverrun` | `leaseId`, `reserved: BudgetDims`, `actuals: BudgetDims` | Actuals exceeded reservation (spec §5 — ledger never lies). |

#### Reserved Namespaces (Future Phases)

| Namespace | Phase | Description |
| :--- | :--- | :--- |
| `sensor.*` | Phase 2+ | FS watch, CI webhook, timer sensor events |
| `context.*` | Phase 2+ | L1–L5 prompt layer assembly events |
| `evolution.*` | Phase 3+ | Meta-loop mutation proposal events |

---

## 4. Outbound Command Schemas (Client → Engine)

Commands are sent from the front-end to the backend via WebSocket. Each command is a JSON object with `commandType` and `payload`.

```typescript
interface BridgeCommand {
  commandType: string;
  runId: string;
  payload: Record<string, unknown>;
}
```

### 4.1 Command Registry

| Command | Payload | Description |
| :--- | :--- | :--- |
| `StartRun` | `topologyHash`, `taskId`, `budgetDims: BudgetDims` | Enqueues a new execution run. |
| `CancelRun` | `runId`, `reason` | Releases active leases and halts node execution. |
| `AcceptDiff` | `runId`, `diffId`, `hunks?: number[]` | Accepts a proposed code patch (full or partial hunk selection). |
| `RejectDiff` | `runId`, `diffId`, `reason?` | Rejects a proposed code patch with optional rationale. |
| `ApproveMutation` | `candidateHash`, `familyId` | Approves a meta-loop proposed topology or prompt mutation (M4–M5). |
| `RollbackTopology` | `targetHash` | Triggers structural topology rollback to a prior hash pin. |

---

## 5. Deterministic Mock Cassette Engine (`packages/mock-server`)

To enable **parallel front-end development** before the backend implementation in `src/aether/` is completed, `@aether/mock-server` provides a replay engine.

### 5.1 Cassette JSON Schema

Cassette files align with the backend `measurement/cassette.py::Cassette` Pydantic model:

```typescript
interface CassetteMeta {
  recordedAt: string;          // ISO 8601
  runId: string;
  stepCount: number;
  backendVersion: string;
  topologyId?: string;         // optional: topology used in the recorded run
}

interface CassetteEntry {
  offsetMs: number;            // milliseconds from recording start
  event: BridgeEvent;          // deserialized event (same shape as live events)
}

interface Cassette {
  meta: CassetteMeta;
  entries: CassetteEntry[];
}
```

### 5.2 MockCassettePlayer API

```typescript
export class MockCassettePlayer {
  /** Load a cassette from a file path (not hardcoded names). */
  public loadCassette(path: string): Promise<void>;

  /** Start replay with optional speed multiplier (1.0 = real-time). */
  public play(speedMultiplier?: number): void;

  /** Pause replay; events stop emitting until resumed. */
  public pause(): void;

  /** Resume from paused state. */
  public resume(): void;

  /** Advance exactly one event (single-step debugging). */
  public stepForward(): void;

  /** Current cassette metadata, if loaded. */
  public get meta(): CassetteMeta | null;

  /** Current playback position (entry index). */
  public get position(): number;
}
```

### 5.3 Replay Semantics

* Entries MUST be replayed in order of `offsetMs`.
* `MockCassettePlayer` implements the same stream interface as `AetherWebsocketClient` — components consume events via the identical `useAetherStream()` hook (FI-3).
* Speed multiplier scales `offsetMs` delays: `2.0` = double speed, `0.5` = half speed.
* **Cassettes**: Stored JSON files in `packages/mock-server/cassettes/` representing complete execution runs (including `NodeExecutionFinished`, `ModelStreamDelta`, and `GateReport` events).
* **Zero UI Disruption**: React components are mock-agnostic by design.

### 5.4 Bundled Fixtures

| Cassette | Description |
| :--- | :--- |
| `swe_bench_pass.json` | Successful retrieve → generate → apply → evaluate cycle |
| `repair_loop_ablation.json` | Evaluate failure triggering 2 repair iterations then pass |
