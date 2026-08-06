---
status: rationale
updated: 2026-08-06
---

# Front-End Schemas and Contracts (`docs_front/development/schemas_and_contracts.md`)

This document defines the TypeScript and Zod schema definitions for all data structures exchanged across boundaries in the AETHER front-end application suite (`@aether/core`). It serves as the front-end equivalent to the backend's `schemas_and_contracts.md`.

## 1. Schema Validation Strategy

To guarantee architectural rule FI-5 (Strict Zod schema validation at bridge boundary), the front-end employs a rigorous validation strategy:

- **Zod as Runtime Validator**: All data entering the front-end from the backend (via WebSocket, SSE, or mock cassettes) is parsed and validated using Zod.
- **CI Generation**: The Zod schemas for events are generated directly from the backend's `domain/events.py` Pydantic models. A CI step checks for drift to ensure the front-end schemas are always synchronized with the backend.
- **Bridge Boundary**: Validation occurs strictly at the driver layer (`AetherWebsocketClient`, `MockCassettePlayer`). Zustand stores and UI components assume data is well-formed.
- **Casing Conversion**: The backend emits JSON using `snake_case`. The front-end validation pipeline automatically converts this to `camelCase` to align with TypeScript conventions.

## 2. Shared Domain Type Schemas

These foundational schemas are used across events, commands, and store states.

```typescript
import { z } from "zod";

// 2.1 GateStatus & GateReport
export const GateStatusSchema = z.enum(["passed", "failed", "none"]);
export type GateStatus = z.infer<typeof GateStatusSchema>;

export const GateReportSchema = z.object({
  gate: z.string(),
  status: GateStatusSchema,
  detail: z.string(),
  instrumentError: z.string().nullable(),
});
export type GateReport = z.infer<typeof GateReportSchema>;

// 2.2 Provenance
export const ProvenanceSchema = z.enum([
  "trusted-system",
  "operator",
  "agent",
  "untrusted-external",
  "untrusted-derived",
]);
export type Provenance = z.infer<typeof ProvenanceSchema>;

// 2.3 BudgetDims
export const BudgetDimsSchema = z.object({
  usdMicros: z.number().int().nonnegative(),
  promptTokens: z.number().int().nonnegative(),
  completionTokens: z.number().int().nonnegative(),
  wallClockMs: z.number().int().nonnegative(),
  concurrencySlots: z.number().int().nonnegative(),
});
export type BudgetDims = z.infer<typeof BudgetDimsSchema>;

// 2.4 TaintSpan
export const TaintSpanSchema = z.object({
  spanId: z.string(),
  label: ProvenanceSchema,
  text: z.string(),
  source: z.string(),
});
export type TaintSpan = z.infer<typeof TaintSpanSchema>;

// 2.5 Workflow Node & Edge
export const WorkflowNodeSchema = z.object({
  id: z.string(),
  kind: z.string(),
  budget: BudgetDimsSchema,
  params: z.record(z.unknown()).optional(),
});
export type WorkflowNode = z.infer<typeof WorkflowNodeSchema>;

export const WorkflowEdgeSchema = z.object({
  from: z.string(),
  to: z.string(),
  when: z.enum(["always", "on_pass", "on_fail", "on_instrument_error"]).default("always"),
});
export type WorkflowEdge = z.infer<typeof WorkflowEdgeSchema>;
```

## 3. Event Schemas (Zod)

All events emitted by the backend stream over the bridge.

### 3.1 Event Payloads

```typescript
// Run Lifecycle
export const RunStartedSchema = z.object({
  eventType: z.literal("RunStarted"),
  taskId: z.string(),
  manifestHash: z.string(),
  topologyHash: z.string(),
  budget: BudgetDimsSchema,
});

export const RunCompletedSchema = z.object({
  eventType: z.literal("RunCompleted"),
  summary: z.string(),
  finalScore: z.number(),
});

export const RunFailedSchema = z.object({
  eventType: z.literal("RunFailed"),
  error: z.string(),
  failedPhase: z.string(),
});

// Node Execution
export const NodeExecutionStartedSchema = z.object({
  eventType: z.literal("NodeExecutionStarted"),
  nodeId: z.string(),
  nodeKind: z.string(),
  inputDigest: z.string(),
});

export const NodeExecutionFinishedSchema = z.object({
  eventType: z.literal("NodeExecutionFinished"),
  nodeId: z.string(),
  gateReport: GateReportSchema,
  costActuals: BudgetDimsSchema,
});

export const NodeSkippedSchema = z.object({
  eventType: z.literal("NodeSkipped"),
  nodeId: z.string(),
  reason: z.literal("memoization_hit"),
});

// Model Streaming
export const ModelStreamDeltaSchema = z.object({
  eventType: z.literal("ModelStreamDelta"),
  nodeId: z.string(),
  kind: z.enum(["text", "tool_call", "usage", "stop"]),
  text: z.string().optional(),
  toolCallDelta: z.record(z.unknown()).optional(),
});

// Effect & Security Audit
export const EffectAuthorizedSchema = z.object({
  eventType: z.literal("EffectAuthorized"),
  runId: z.string(),
  effectClass: z.string(),
  descriptor: z.string(),
  ruleId: z.string(),
});

export const EffectDeniedSchema = z.object({
  eventType: z.literal("EffectDenied"),
  runId: z.string(),
  effectClass: z.string(),
  descriptor: z.string(),
  decision: z.string(),
  rationale: z.string(),
});

export const TaintSpanEmittedSchema = z.object({
  eventType: z.literal("TaintSpanEmitted"),
  spanId: z.string(),
  label: ProvenanceSchema,
  text: z.string(),
  source: z.string(),
});

// Budget & Resource
export const BudgetLeaseUpdatedSchema = z.object({
  eventType: z.literal("BudgetLeaseUpdated"),
  reserved: BudgetDimsSchema,
  committed: BudgetDimsSchema,
  remaining: BudgetDimsSchema,
});

export const BudgetOverrunSchema = z.object({
  eventType: z.literal("BudgetOverrun"),
  leaseId: z.string(),
  reserved: BudgetDimsSchema,
  actuals: BudgetDimsSchema,
});

// Discriminated Union
export const EventPayloadSchema = z.discriminatedUnion("eventType", [
  RunStartedSchema, RunCompletedSchema, RunFailedSchema,
  NodeExecutionStartedSchema, NodeExecutionFinishedSchema, NodeSkippedSchema,
  ModelStreamDeltaSchema,
  EffectAuthorizedSchema, EffectDeniedSchema, TaintSpanEmittedSchema,
  BudgetLeaseUpdatedSchema, BudgetOverrunSchema,
]);
export type EventPayload = z.infer<typeof EventPayloadSchema>;
```

### 3.2 Bridge Event Envelope & Pipeline

```typescript
export const BridgeEventSchema = z.object({
  seq: z.number().int().nonnegative(),
  runId: z.string(),
  eventType: z.string(),
  at: z.string().datetime(),
  payload: EventPayloadSchema,
});
export type BridgeEvent = z.infer<typeof BridgeEventSchema>;

/**
 * Validates an incoming JSON event, parsing snake_case to camelCase
 * and validating against BridgeEventSchema.
 */
export function validateEventPipeline(rawJson: unknown): BridgeEvent | null {
  try {
    // 1. camelCase conversion logic (assumed utility: snakeToCamel)
    const camelCased = snakeToCamelDeep(rawJson);
    
    // 2. Schema validation
    return BridgeEventSchema.parse(camelCased);
  } catch (error) {
    console.error("Event validation failed. Dropping event:", error);
    return null; // FI-5: Validation errors are logged and dropped, never crash.
  }
}
```

## 4. Command Schemas (Zod)

Commands sent from the client to the engine.

```typescript
export const StartRunSchema = z.object({
  commandType: z.literal("StartRun"),
  topologyHash: z.string(),
  taskId: z.string(),
  budgetDims: BudgetDimsSchema,
});

export const CancelRunSchema = z.object({
  commandType: z.literal("CancelRun"),
  runId: z.string(),
  reason: z.string(),
});

export const AcceptDiffSchema = z.object({
  commandType: z.literal("AcceptDiff"),
  runId: z.string(),
  diffId: z.string(),
  hunks: z.array(z.number().int()).optional(),
});

export const RejectDiffSchema = z.object({
  commandType: z.literal("RejectDiff"),
  runId: z.string(),
  diffId: z.string(),
  reason: z.string().optional(),
});

export const ApproveMutationSchema = z.object({
  commandType: z.literal("ApproveMutation"),
  candidateHash: z.string(),
  familyId: z.string(),
});

export const RollbackTopologySchema = z.object({
  commandType: z.literal("RollbackTopology"),
  targetHash: z.string(),
});

export const CommandPayloadSchema = z.discriminatedUnion("commandType", [
  StartRunSchema, CancelRunSchema, AcceptDiffSchema,
  RejectDiffSchema, ApproveMutationSchema, RollbackTopologySchema,
]);

export const BridgeCommandSchema = z.object({
  commandType: z.string(),
  runId: z.string(),
  payload: CommandPayloadSchema,
});
export type BridgeCommand = z.infer<typeof BridgeCommandSchema>;
```

## 5. Cassette Schemas

Cassettes enable deterministic replay of recorded backend events for parallel front-end development.

```typescript
export const CassetteMetaSchema = z.object({
  recordedAt: z.string().datetime(),
  runId: z.string(),
  stepCount: z.number().int().nonnegative(),
  backendVersion: z.string(),
  topologyId: z.string().optional(),
});
export type CassetteMeta = z.infer<typeof CassetteMetaSchema>;

export const CassetteEntrySchema = z.object({
  offsetMs: z.number().nonnegative(),
  event: BridgeEventSchema,
});
export type CassetteEntry = z.infer<typeof CassetteEntrySchema>;

export const CassetteSchema = z.object({
  meta: CassetteMetaSchema,
  entries: z.array(CassetteEntrySchema),
});
export type Cassette = z.infer<typeof CassetteSchema>;
```

### Cassette Validation Contract
- **Offline Integrity**: Cassettes are parsed using `CassetteSchema` when loaded by `MockCassettePlayer`.
- **Event Parity**: Cassette entries hold complete `BridgeEvent` structures. React components consuming the stream remain agnostic to whether the source is live WebSocket or a mock cassette replay.

## 6. Store State Schemas

These schemas define the runtime shape of the six domain Zustand stores.

```typescript
// 1. Engine Store
export const EngineStateSchema = z.object({
  status: z.enum(["disconnected", "connecting", "connected"]),
  activeRunId: z.string().nullable(),
  events: z.array(BridgeEventSchema),
});

// 2. Workflow Store
export const WorkflowStateSchema = z.object({
  topologyId: z.string().nullable(),
  nodes: z.array(z.any()), // xyflow Node[] equivalent
  edges: z.array(z.any()), // xyflow Edge[] equivalent
  repairLoops: z.array(z.object({
    fromNode: z.string(),
    viaNodes: z.array(z.string()),
    backTo: z.string(),
    maxIterations: z.number().int(),
    currentIteration: z.number().int(),
  })),
  fanOutSites: z.array(z.object({
    nodeId: z.string(),
    n: z.number().int(),
    cacheSequencing: z.string(),
    candidateStatuses: z.array(z.any()),
  })),
  selectedNodeId: z.string().nullable(),
});

// 3. Budget Store
export const BudgetStateSchema = z.object({
  reserved: BudgetDimsSchema,
  committed: BudgetDimsSchema,
  remaining: BudgetDimsSchema,
  overruns: z.array(BudgetOverrunSchema),
});

// 4. Patch Store
export const PatchStateSchema = z.object({
  pendingDiffs: z.array(z.object({
    diffId: z.string(),
    filePath: z.string(),
    hunks: z.array(z.string()),
    status: z.enum(["pending", "accepted", "rejected"]),
  })),
});

// 5. Metrics Store
export const MetricsStateSchema = z.object({
  currentScores: z.record(z.number()),
  history: z.array(z.object({
    timestamp: z.string().datetime(),
    scores: z.record(z.number()),
  })),
  abResults: z.array(z.object({
    experimentId: z.string(),
    pValue: z.number(),
    confidenceInterval: z.tuple([z.number(), z.number()]),
  })),
});

// 6. Taint Audit Store
export const TaintStateSchema = z.object({
  spans: z.array(TaintSpanSchema),
  inspectSpanId: z.string().nullable(),
});
```

### Persistence Serialization Contracts
All stores are strictly JSON-serializable (no Maps, Sets, or class instances) allowing straightforward snapshotting or `zustand/middleware` persistence.

## 7. Cross-Boundary Contract Rules

1. **Serializability**: All store state must be JSON-serializable. No complex JS objects or class instances.
2. **Schema Evolution**: Schemas must only evolve by adding new fields (with safe defaults). Existing fields are never removed or re-typed in a breaking manner. Unrecognized fields are stripped.
3. **Envelope Consistency**: All inbound communication is wrapped in the `BridgeEvent` envelope. All outbound communication is wrapped in the `BridgeCommand` envelope.
4. **Type Generation**: Front-end schemas and TypeScript interfaces MUST be generated from the backend's Python Pydantic definitions (specifically `domain/events.py`). Manual updates are strictly forbidden as they risk introducing divergence.
5. **Validation Error Handling**: `ZodError` instances encountered at the bridge boundary MUST NOT crash the application. They are logged to standard output/console and the payload is dropped, treating it as malformed network noise.
