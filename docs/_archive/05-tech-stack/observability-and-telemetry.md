---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Observability & Telemetry**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

## **Architecture: EventBus Subscribers**

The [EventBus](../02-architecture/event-bus-and-hooks.md) acts as the single source of truth; `TrajectoryStore` and the OpenTelemetry (OTel) exporter subscribe independently to avoid state drift.

```
Kernel ──→ EventBus ──┬──→ TrajectoryStore  (Durable, queryable, replayable)
                      └──→ OTel Exporter    (Traces, metrics, dashboards)
```

## **OTel GenAI Span Model**

Uses standard OpenTelemetry GenAI semantic conventions:

```
run                                        (root: run_id, config_hash)
├── step                                   (step_id, branch_id)
│   ├── gen_ai.chat                        (model call)
│   ├── execute_tool                       (tool dispatch)
│   │   ├── policy.authorize
│   │   └── tool.<name>
│   └── hook.<point>
├── candidate.evaluate                     (System 2 only)
│   └── gate.evaluate
└── checkpoint.commit
```

### Key Span Attributes

| Span | Key Attributes |
| :--- | :--- |
| `gen_ai.chat` | `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read_tokens`, `gen_ai.usage.cache_creation_tokens`, `sagiha.cost_usd`, `sagiha.prompt_version` |
| `execute_tool` | `sagiha.tool.name`, `sagiha.tool.effect`, `sagiha.grant.id`, `sagiha.tool.truncated`, `sagiha.tool.trusted_output` |
| `policy.authorize` | `sagiha.policy.decision`, `sagiha.policy.reason`, `sagiha.policy.requires_human` |
| `gate.evaluate` | Per-gate booleans, `sagiha.gate.admitted` |
| `run` | `sagiha.task_id`, `sagiha.autonomy_level`, `sagiha.config_hash`, `sagiha.harness_version` |

* `cache_read_tokens` tracks [cache-stable prompt layout](../02-architecture/context-and-cache-engineering.md) performance.

## **Key Telemetry Metrics**

| Metric | Type | Purpose |
| :--- | :--- | :--- |
| `sagiha.run.duration` | Histogram | Wall-clock execution time. |
| `sagiha.run.outcome` | Counter | Success vs. failure counts. |
| `sagiha.tokens.total` | Counter | Token distribution (input, output, cache). |
| `sagiha.cache.hit_ratio` | Gauge | Cost-efficiency leading indicator. |
| `sagiha.cost.usd` | Counter | Total spend cross-checked against ResourceGovernor. |
| `sagiha.tool.calls` | Counter | Tool utilization breakdown. |
| `sagiha.tool.duration` | Histogram | Tool execution latency. |
| `sagiha.edit.hunk_failure_ratio` | Gauge | **Patch quality indicator**. |
| `sagiha.gate.failures` | Counter | Gate rejection breakdown. |
| `sagiha.retrieval.recall_at_k` | Gauge | Standalone code retrieval accuracy. |
| `sagiha.degradation` | Counter | Silent component fallback tracking. |
| `sagiha.retry.count` | Counter | Transient error frequency. |
| `sagiha.approval.wait` | Histogram | Human-in-the-loop wait times. |
| `sagiha.lsp.servers_active` | Gauge | Active LSP pool pressure. |

## **Redaction Policy**

Redaction runs **once at the EventBus boundary**:
* **Redacted**: Secret-scoped grant data, env vars matching `redact_patterns`, `Authorization` headers, high-entropy tokens.
* **Preserved**: Tool names, effect classes, policy decisions, file paths, token counts.
* Content payload exports (`sagiha.capture_content`) default to `false` to keep repository code local.

## **Trajectory Store Schema**

Append-only SQLite-WAL (`events` table):

```sql
CREATE TABLE events (
  seq            INTEGER PRIMARY KEY,
  schema_version INTEGER NOT NULL,
  run_id         TEXT NOT NULL,
  branch_id      TEXT NOT NULL,
  step_seq       INTEGER,
  parent_seq     INTEGER,             -- DAG ancestry link
  kind           TEXT NOT NULL,
  payload        TEXT NOT NULL,       -- Serialized event payload
  ts             TEXT NOT NULL        -- ISO-8601, aware UTC
);
CREATE INDEX idx_run_step ON events(run_id, step_seq);
CREATE INDEX idx_kind ON events(run_id, kind);
```

## **Inspection Commands**

CLI utilities for debugging and replay (see [STATUS.md](../STATUS.md)):

```bash
sagiha trajectory show <run-id>              # View steps, tools, diagnostics, scores
sagiha trajectory diff <id-a> <id-b>         # Locate execution step divergence
sagiha trajectory grep <run-id> --tool apply_edit
sagiha trajectory cost <run-id>              # Detailed cost breakdown by step
sagiha replay --run-id <id>                  # Deterministic offline replay
```

## **Operational Baselines**

* **Cache Hit Ratio**: $> 0.80$ on multi-step cloud runs.
* **Edit Hunk Failure Ratio**: $< 0.15$.
* **Degradation Events**: $= 0$ in benchmark runs.
* **Retry Token Share**: $< 0.10$.
