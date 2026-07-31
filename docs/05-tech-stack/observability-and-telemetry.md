---
status: rationale
retrieval: excluded
updated: 2026-07-29
---
# **Observability & Telemetry**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **One Truth, Two Views**

The trajectory store and the OTel span log record the same facts. Maintaining them independently guarantees drift, so:

**The [EventBus](../02-architecture/event-bus-and-hooks.md) is the single source. The `TrajectoryStore` and the OTel exporter are both subscribers.** Neither is derived from the other, and no component writes to both.

```
Kernel ──→ EventBus ──┬──→ TrajectoryStore  (durable, queryable, replayable)
                      └──→ OTel exporter    (traces, metrics, dashboards)
```

## **Span Model — GenAI Semantic Conventions**

Standard OTel GenAI conventions are used rather than a bespoke schema, so existing tracing backends understand SAGIHA traces without adapters.

```
run                                        (root, run_id)
├── step                                   (step_id, branch_id)
│   ├── gen_ai.chat                        model call
│   ├── execute_tool                       one per dispatch
│   │   ├── policy.authorize
│   │   └── tool.<name>
│   └── hook.<point>
├── candidate.evaluate                     System 2 only
│   └── gate.evaluate
└── checkpoint.commit
```

### Key Attributes

| Span | Attributes |
| :--- | :--- |
| `gen_ai.chat` | `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read_tokens`, `gen_ai.usage.cache_creation_tokens`, `sagiha.cost_usd`, `sagiha.prompt_version` |
| `execute_tool` | `sagiha.tool.name`, `sagiha.tool.effect`, `sagiha.grant.id`, `sagiha.tool.truncated`, `sagiha.tool.trusted_output` |
| `policy.authorize` | `sagiha.policy.decision`, `sagiha.policy.reason`, `sagiha.policy.requires_human` |
| `gate.evaluate` | one boolean per gate, plus `sagiha.gate.admitted` |
| `run` | `sagiha.task_id`, `sagiha.autonomy_level`, `sagiha.config_hash`, `sagiha.harness_version` |

`cache_read_tokens` is not an optional nicety. It is the primary evidence that the [cache-stable prompt layout](../02-architecture/context-and-cache-engineering.md) is working, and a cache hit rate collapse is usually the first visible symptom of a prompt-assembly regression — often before task success moves at all.

`sagiha.config_hash` and `sagiha.prompt_version` on every root span are what make a months-old run explicable.

## **Metrics**

| Metric | Type | Why it matters |
| :--- | :--- | :--- |
| `sagiha.run.duration` | histogram | Wall-clock per run |
| `sagiha.run.outcome` | counter (by result) | Success rate |
| `sagiha.tokens.total` | counter (by kind) | Input/output/cache split |
| `sagiha.cache.hit_ratio` | gauge | Cost-efficiency leading indicator |
| `sagiha.cost.usd` | counter (by model) | Spend, cross-checked against governor |
| `sagiha.tool.calls` | counter (by tool, outcome) | Tool selection distribution |
| `sagiha.tool.duration` | histogram (by tool) | Feedback-loop latency |
| `sagiha.edit.hunk_failure_ratio` | gauge | **Edit reliability — a top-tier quality signal** |
| `sagiha.gate.failures` | counter (by gate) | Where candidates die |
| `sagiha.retrieval.recall_at_k` | gauge | Retrieval quality, independent of task success |
| `sagiha.degradation` | counter (by component) | Silent capability loss |
| `sagiha.retry.count` | counter (by class) | Transient-failure burden |
| `sagiha.approval.wait` | histogram | Human-gate latency |
| `sagiha.lsp.servers_active` | gauge | Pool pressure under parallel search |

Two of these deserve dashboard placement most teams wouldn't predict. `edit.hunk_failure_ratio` is the earliest indicator that a model or prompt change degraded patch quality — it moves before task success does. And `degradation` catches the failure mode where a benchmark run silently lost retrieval and produced a number that means nothing.

## **Redaction**

Applied **once, at the event boundary**, before any subscriber sees an event — never per-subscriber, which guarantees eventual inconsistency.

Redacted: env values matching `redact_patterns`, `Authorization` headers, anything from a secret-scoped grant, and high-entropy strings matching known key formats.

**Never redacted**: tool names, effect classes, policy decisions, file paths, token counts. Redacting the audit trail to protect secrets that were never in it costs the ability to answer what happened.

Prompt and completion text are **not exported by default** (`sagiha.capture_content = false`). They live in the trajectory store locally. Turning capture on ships source code to a telemetry backend, which is a decision an operator makes deliberately.

## **Trajectory Store**

Append-only SQLite-WAL. Events are the write unit; scores arrive as separate `StepScored` rows rather than updates, which keeps the append-only guarantee true rather than aspirational.

```sql
CREATE TABLE events (
  seq            INTEGER PRIMARY KEY,
  schema_version INTEGER NOT NULL,
  run_id         TEXT NOT NULL,
  branch_id      TEXT NOT NULL,
  step_seq       INTEGER,
  parent_seq     INTEGER,             -- DAG ancestry, not a linear counter
  kind           TEXT NOT NULL,
  payload        TEXT NOT NULL,       -- serialized event model
  ts             TEXT NOT NULL        -- ISO-8601, aware UTC
);
CREATE INDEX idx_run_step ON events(run_id, step_seq);
CREATE INDEX idx_kind ON events(run_id, kind);
```

It serves four consumers with different needs: replay (ordered read), audit (policy decisions), RHI training data (outcomes and features), and debugging (`sagiha trajectory show`).

## **Schema Versioning**

Both the `events` table and cassette headers include a `schema_version: int` field. 

**Upgrade policy**:
* Replay compatibility window of one major version.
* Migration scripts for older cassettes.
* Or explicit re-record.

Note: the first change to any event model without this will orphan every cassette.

## **Inspection**

> **Planned — Sprint 3** for `replay`; trajectory inspection commands land with or after the run loop ([STATUS.md](../STATUS.md)). Trajectory *storage* exists today; these CLIs do not.

```bash
sagiha trajectory show <run-id>              # steps, tools, diagnostics, scores
sagiha trajectory diff <id-a> <id-b>         # where two runs diverged
sagiha trajectory grep <run-id> --tool apply_edit
sagiha trajectory cost <run-id>              # spend breakdown by step
sagiha replay --run-id <id>                  # deterministic, zero API calls
```

`trajectory diff` is the workhorse for outer-loop analysis: given a mutation that helped on some tasks and hurt on others, it locates the exact step where behavior changed.

## **What Good Looks Like**

Baselines to alert against, not aspirations:

* Cache hit ratio **> 0.80** on multi-step runs. Below that, inspect prompt assembly for prefix churn.
* Edit hunk failure ratio **< 0.15**. Above that, the edit format or anchoring strategy needs work.
* Degradation events **= 0** in benchmark runs. Any nonzero count invalidates the run's numbers.
* Retry share of total tokens **< 0.10**.
