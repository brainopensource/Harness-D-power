---
status: normative
updated: 2026-07-29
---

# **Event Catalog**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal,
> refined iteratively as practical evaluation progresses.

> [!IMPORTANT]
> **This file is generated** from `src/sagiha/domain/events.py` by `scripts/gen_event_catalog.py`,
> run in CI with `--check`. Edit the Python, not this file — see
> [Contracts to Code](../implementation/contracts-to-code.md).

## **Why This Module Exists**

[Event Bus & Hooks](../02-architecture/event-bus-and-hooks.md) explains the *mechanism*: one stream,
many consumers, observers that cannot influence and interceptors that cannot mutate. This file is the
*registry*: what every event is, what it carries, who emits it, who consumes it, and whether replay
depends on it.

That matters more here than in a typical system, because in an event-sourced harness **a module is
defined by the events it consumes and emits, not by its imports**. The catalog is therefore the real
map of the architecture — and the document to read before adding a feature, because a feature that
needs a new event is a feature that changes this table, in public, on purpose.

## **Conventions**

* Every event extends `Event` ([Domain Schemas](../03-contracts-and-models/domain-schemas.md)):
  `event`, `schema_version`, `run_id`, `step_id`, aware-UTC `timestamp`.
* Names are `group.past_tense`. Events describe **what happened**, never what should happen — an event
  named as a command is a method call wearing a costume.
* `schema_version` is per event type, not global.
* **Replay-relevant** means `sagiha replay --verify-all` asserts on it. Those events are the replay
  contract; changing one requires an upcaster
  ([Port Stability](../03-contracts-and-models/port-stability-and-versioning.md)).

Subscriber abbreviations: **TS** TrajectoryStore · **OT** OTel exporter · **UI** TUI/SSE/A2A
streamers · **HK** user hooks · **GV** ResourceGovernor · **MI** MetaImprover / trajectory mining.

## **Lifecycle**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `run.started` | `task`, `run_context`, `profile`, `extension_manifest` | Orchestrator | TS OT UI MI | ✅ |
| `run.completed` | `gate_report`, `cost` | Orchestrator | TS OT UI HK MI | ✅ |
| `run.failed` | `error_kind`, `disposition`, `message` | Orchestrator | TS OT UI HK | ✅ |
| `run.canceled` | `reason`, `canceled_by` | Orchestrator | TS OT UI | ✅ |
| `checkpoint.created` | `label`, `commit_sha` | Workspace | TS UI | ✅ |

`run.started` carries the **resolved profile** because which events a run can emit depends on it — see "Profile-Dependent Events" below — and because an ungated run must never be mistaken for a gated one by a later benchmark report or outer-loop training set.

`run.started` carries the extension manifest because a trajectory that replays against a different extension set is not a replay. See [ADR-0013](../08-decisions/0013-extension-registration.md).

## **Reasoning**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `step.started` | — | Orchestrator | TS OT UI | ✅ |
| `model.call_started` | `model`, `request_digest`, `cache_breakpoints` | ModelProvider | TS OT UI GV | ✅ |
| `model.delta` | `frame` | ModelProvider | UI | ❌ |
| `model.call_completed` | `usage`, `stop_reason`, `cost` | ModelProvider | TS OT UI GV MI | ✅ |
| `step.completed` | `step` | Orchestrator | TS OT UI MI | ✅ |
| `step.scored` | `scored` | Evaluator / Reviewer / AOI | TS MI | ❌ |

`model.delta` is the one high-volume event and the only one observers are permitted to drop under backpressure — losing a rendering frame is acceptable; losing a step is not.

`step.scored` is a **separate event rather than a mutation** of the stored step. That is what makes the append-only claim true rather than aspirational.

`model.call_completed` is the sole source of spend and cache-hit truth. Every adapter emits exactly one `UsageReported` before `StreamEnd` on the streaming path — without that, the governor never fires and the economics are unmeasured on the default interactive path.

## **Tools**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `tool.call_requested` | `call` | Agency | TS OT UI HK | ✅ |
| `tool.call_authorized` | `decision` | PolicyEngine | TS OT HK | ✅ |
| `tool.call_denied` | `decision`, `reason`, `requires_human` | PolicyEngine | TS OT UI HK | ✅ |
| `tool.call_completed` | `result`, `duration_ms` | Dispatch | TS OT UI HK MI | ✅ |
| `tool.call_failed` | `error_kind`, `disposition` | Dispatch | TS OT UI HK | ✅ |

The **requested / authorized** split is deliberate: it makes the policy decision independently observable, so an audit answers "what did the agent try to do" separately from "what was it allowed to do." Those are different questions and a single event cannot answer both.

**No event ever carries a `Grant`.** Grants do not leave `kernel/dispatch.py`, and an audit log containing capability tokens is a credential store with extra steps. `tool.call_authorized` carries the `Decision`, including the grant *id* for correlation — never the grant.

## **Workspace**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `edit.applied` | `result` | Workspace | TS OT UI HK MI | ✅ |
| `command.executed` | `argv`, `exit_code`, `output`, `truncated`, `full_output_uri` | Workspace | TS OT UI HK | ✅ |
| `diagnostics.changed` | `added`, `removed` | LSPAdapter | TS OT UI MI | ❌ |
| `worktree.allocated` | `branch_id`, `base_commit` | WorktreeManager | TS OT UI | ✅ |
| `worktree.released` | `branch_id`, `disposition` | WorktreeManager | TS OT UI | ✅ |
| `index.updated` | `paths`, `chunk_delta`, `duration_s` | Indexer | OT UI | ❌ |

`edit.applied` carries per-hunk outcomes because `edit.hunk_failure_ratio` is a top-tier quality signal and the edit format is an empirical question. An aggregate boolean would make it unanswerable.

## **Evaluation & Control**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `gate.evaluated` | `gate_report` | Evaluator | TS OT UI HK MI | ✅ |
| `review.completed` | `review` | Reviewer | TS MI UI | ❌ |
| `candidate.proposed` | `branch_id`, `strategy`, `budget_usd` | CandidateSearch | TS OT UI | ✅ |
| `candidate.selected` | `branch_id`, `gate_report`, `selection_basis` | CandidateSearch | TS OT UI | ✅ |
| `approval.requested` | `action`, `scope`, `rationale`, `blast_radius` | PolicyEngine | UI HK (blocking) | ✅ |
| `approval.resolved` | `approved`, `resolved_by`, `note` | Entry point | TS OT UI | ✅ |
| `budget.warning` | `spent_usd`, `remaining_usd`, `projected_usd` | ResourceGovernor | UI HK | ❌ |
| `budget.exhausted` | `spent_usd`, `limit_usd`, `limit_kind` | ResourceGovernor | TS UI HK | ✅ |

`approval.requested` is the only event whose delivery blocks the run — it is a question, and the run cannot proceed without the answer. Every other event is fire-and-observe.

## **Steering**

| Event | Payload | Emitted by | Consumers | Replay |
| :--- | :--- | :--- | :--- | :--- |
| `user.message_received` | `text`, `provenance`, `at_step` | Entry point | TS OT UI | ✅ |
| `task.revised` | `task`, `supersedes` | Orchestrator | TS OT UI MI | ✅ |

Mid-run steering is the dominant interaction mode in every comparable harness, and retrofitting an input channel into a one-shot pipeline is expensive. The rules:

1. A new operator turn **appends to the tail** — the cache-stable prefix is untouched, so steering costs no cache.
2. If it changes the goal or acceptance criteria, the orchestrator emits `task.revised` with a **new `TaskSpec` revision**. `TaskSpec` is frozen; it is never mutated. The trajectory therefore records which revision each step was working against, which is what keeps the gate report interpretable.
3. A revision invalidates the active plan and the retrieval set — both are recomputed. It does **not** invalidate the system prefix, tool definitions, or skill descriptors.
4. Operator content is `Provenance.OPERATOR` and is the only untrusted-by-default channel that is authoritative.

## **Profile-Dependent Events**

Which events a run *can* emit is a function of its
[execution profile](../02-architecture/execution-profiles.md). A consumer must treat these as
optional rather than assuming every run produces them.

| Event group | Requires | Absent under |
| :--- | :--- | :--- |
| `worktree.allocated` / `worktree.released` | `workspace = "worktree"` | `analysis`, `chat` |
| `edit.applied`, `command.executed` | a writable `Workspace` | `analysis`, `review`, `chat` |
| `diagnostics.changed`, `index.updated` | a repository | `chat` |
| `gate.evaluated` | `gates != "none"` | `chat` |
| `candidate.proposed` / `candidate.selected` | writable workspace | `analysis`, `review`, `chat` |
| `review.completed` | a bound `Reviewer` | `chat` |

**`gate.evaluated` is never emitted with an empty `GateReport`.** Under `gates = "none"` the event does
not occur at all and `run.completed` carries `gate_report: None`. `GateReport.acceptance_met` is
vacuously `True` over an empty criteria tuple, so an empty report would announce `admitted=True` — and
absence of a verdict must never be representable as a passing verdict.

Events that are **never** profile-dependent: the full `tool.*` group, `model.*`, `step.*`, `run.*`,
`approval.*`, `budget.*`, and `user.message_received`. Those are the harness operating, and they occur
identically whether the task is a refactor or a question. In particular **every profile emits
`tool.call_requested` and `tool.call_authorized`** — a profile subtracts capability, never supervision.

## **Adding an Event**

1. Add the model to `sagiha/domain/events.py` with `schema_version = 1`, a `group`, `emitted_by`, and
   `consumers`.
2. Regenerate this catalog with `uv run python scripts/gen_event_catalog.py`; the diff is the review
   artifact.
3. Decide replay-relevance deliberately via `replay_relevant`. Marking a high-volume rendering event
   replay-relevant makes every cassette larger and every replay slower, for no audit value.
4. Changing an existing event's payload requires a version bump **and** an upcaster
   ([Port Stability](../03-contracts-and-models/port-stability-and-versioning.md)).
