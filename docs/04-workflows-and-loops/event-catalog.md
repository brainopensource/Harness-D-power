---
status: normative
updated: 2026-07-30
---

# **Event Catalog**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

> [!IMPORTANT]
> **This file is generated** from `src/sagiha/domain/events.py` by `scripts/gen_event_catalog.py` (run in CI with `--check`). Edit the Python source, not this file — see [Contracts to Code](../implementation/contracts-to-code.md).

## **Why This Module Exists**

While [Event Bus & Hooks](../02-architecture/event-bus-and-hooks.md) defines bus mechanisms, this catalog is the registry mapping event schemas, emitters, consumers, and replay relevance. In an event-sourced harness, modules are defined by consumed and emitted events.

## **Conventions**

* Extends `Event` ([Domain Schemas](../03-contracts-and-models/domain-schemas.md)): `event`, `schema_version`, `run_id`, `step_id`, aware-UTC `timestamp`.
* Naming format: `group.past_tense` (describes occurrences, not commands).
* `schema_version` is per event type.
* **Replay-relevant** events form the replay contract (`sagiha replay --verify-all`, see [STATUS.md](../STATUS.md)). Changing them requires upcasters ([Port Stability](../03-contracts-and-models/port-stability-and-versioning.md)).

**Subscriber Key:** **TS** TrajectoryStore · **OT** OTel exporter · **UI** TUI/SSE/A2A streamers · **HK** user hooks · **GV** ResourceGovernor · **MI** MetaImprover.

## **Lifecycle**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `run.started` | `task`, `run_context`, `profile`, `extension_manifest` | Orchestrator | TS OT UI MI | ✅ |
| `run.completed` | `gate_report`, `cost` | Orchestrator | TS OT UI HK MI | ✅ |
| `run.failed` | `error_kind`, `disposition`, `message` | Orchestrator | TS OT UI HK | ✅ |
| `run.canceled` | `reason`, `canceled_by` | Orchestrator | TS OT UI | ✅ |
| `checkpoint.created` | `label`, `commit_sha` | Workspace | TS UI | ✅ |

* `run.started` includes resolved profile and extension manifest ([ADR-0013](../08-decisions/0013-extension-registration.md)) to guarantee replay reproducibility.

## **Reasoning**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `step.started` | — | Orchestrator | TS OT UI | ✅ |
| `model.call_started` | `model`, `request_digest`, `cache_breakpoints` | ModelProvider | TS OT UI GV | ✅ |
| `model.delta` | `frame` | ModelProvider | UI | ❌ |
| `model.call_completed` | `usage`, `stop_reason`, `cost` | ModelProvider | TS OT UI GV MI | ✅ |
| `step.completed` | `step` | Orchestrator | TS OT UI MI | ✅ |
| `step.scored` | `scored` | Evaluator / Reviewer / AOI | TS MI | ❌ |
| `model.provider_failover` | `from_provider`, `to_provider`, `reason`, `reasoning_dropped` | FallbackModelAdapter | TS OT UI MI | ✅ |

* `model.delta` is droppable under backpressure.
* `step.scored` is a discrete event rather than step mutation to maintain append-only invariants.
* `model.call_completed` tracks spend and cache usage via `UsageReported`.

## **Tools**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `tool.call_requested` | `call` | Agency | TS OT UI HK | ✅ |
| `tool.call_authorized` | `decision` | PolicyEngine | TS OT HK | ✅ |
| `tool.call_denied` | `decision`, `reason`, `requires_human` | PolicyEngine | TS OT UI HK | ✅ |
| `tool.call_completed` | `call_id`, `result`, `duration_ms` | Dispatch | TS OT UI HK MI | ✅ |
| `tool.call_failed` | `call_id`, `error_kind`, `disposition` | Dispatch | TS OT UI HK | ✅ |
| `tool.taint_introduced` | `call_id`, `tool_name`, `source` | Dispatch | TS OT UI HK MI | ✅ |

* `requested` vs `authorized` split separates intent from permission auditability.
* Events carry `Decision` and grant IDs, never raw `Grant` tokens.

## **Context**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `context.compaction_applied` | `exchanges_before`, `exchanges_after`, `tail_tokens_before`, `tail_tokens_after`, `tainted_span` | ContextAssembler | TS OT UI MI | ✅ |

* Replay-relevant to maintain token digest alignment across execution replays.

## **Workspace**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `edit.applied` | `result` | Workspace | TS OT UI HK MI | ✅ |
| `command.executed` | `argv`, `exit_code`, `output`, `truncated`, `full_output_uri` | Workspace | TS OT UI HK | ✅ |
| `diagnostics.changed` | `added`, `removed` | LSPAdapter | TS OT UI MI | ❌ |
| `worktree.allocated` | `branch_id`, `base_commit` | WorktreeManager | TS OT UI | ✅ |
| `worktree.released` | `branch_id`, `disposition` | WorktreeManager | TS OT UI | ✅ |
| `index.updated` | `paths`, `chunk_delta`, `duration_s` | Indexer | OT UI | ❌ |

* `edit.applied` carries per-hunk outcomes for edit quality metric tracking.

## **Evaluation & Control**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `gate.evaluated` | `gate_report` | Evaluator | TS OT UI HK MI | ✅ |
| `review.completed` | `review` | Reviewer | TS MI UI | ❌ |
| `candidate.proposed` | `branch_id`, `strategy`, `budget_usd` | CandidateSearch | TS OT UI | ✅ |
| `candidate.selected` | `branch_id`, `gate_report`, `selection_basis`, `diversity_ratio` | CandidateSearch | TS OT UI | ✅ |
| `approval.requested` | `action`, `scope`, `rationale`, `blast_radius` | PolicyEngine | UI HK (blocking) | ✅ |
| `approval.resolved` | `approved`, `resolved_by`, `note` | Entry point | TS OT UI | ✅ |
| `budget.warning` | `spent_usd`, `remaining_usd`, `projected_usd` | ResourceGovernor | UI HK | ❌ |
| `budget.exhausted` | `spent_usd`, `limit_usd`, `limit_kind` | ResourceGovernor | TS UI HK | ✅ |
| `benchmark.task_harvested` | `task_id`, `repo` | Harvester | TS OT UI | ✅ |
| `benchmark.task_completed` | `task_id`, `agent_id`, `resolved` | TaskRunner | TS OT UI MI | ✅ |
| `replay.verified` | `replay_run_id` | CLI | TS OT | ✅ |

* `approval.requested` is the only execution-blocking event.

## **Steering**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `user.message_received` | `text`, `provenance`, `at_step` | Entry point | TS OT UI | ✅ |
| `task.revised` | `task`, `supersedes` | Orchestrator | TS OT UI MI | ✅ |

* Mid-run operator inputs append to the trajectory tail (preserving prompt cache).
* Goal/criteria changes emit `task.revised` with an immutable updated `TaskSpec`, invalidating active plans and retrieval sets.

## **Profile-Dependent Events**

Events vary by [execution profile](../02-architecture/execution-profiles.md):

| Event group | Requires | Absent under |
| :--- | :--- | :--- |
| `worktree.allocated` / `worktree.released` | `workspace = "worktree"` | `analysis`, `chat` |
| `edit.applied`, `command.executed` | Writable `Workspace` | `analysis`, `review`, `chat` |
| `diagnostics.changed`, `index.updated` | Repository | `chat` |
| `gate.evaluated` | `gates != "none"` | `chat` |
| `candidate.proposed` / `candidate.selected` | Writable workspace | `analysis`, `review`, `chat` |
| `review.completed` | Bound `Reviewer` | `chat` |

* `gate.evaluated` is omitted when `gates = "none"` (`run.completed` carries `gate_report: None`).
* Core framework events (`tool.*`, `model.*`, `step.*`, `run.*`, `approval.*`, `budget.*`, `user.message_received`) fire across all profiles.

## **Adding an Event**

1. Define model in `sagiha/domain/events.py` (`schema_version = 1`, `group`, `emitted_by`, `consumers`).
2. Run `uv run python scripts/gen_event_catalog.py`.
3. Set `replay_relevant` status deliberately.
4. Payload changes require schema version bumps and upcasters ([Port Stability](../03-contracts-and-models/port-stability-and-versioning.md)).
