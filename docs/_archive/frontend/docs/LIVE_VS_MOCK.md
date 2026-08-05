---
status: rationale
updated: 2026-07-31
retrieval: excluded
---

# LIVE vs MOCK — Frontend Feature Matrix

> Source of truth for what the GUI/CLI may claim as working against the Python harness.
> Backend authority: `docs/STATUS.md` + `src/sagiha/`. Frontend design: `docs/superpowers/specs/2026-07-31-frontend-hybrid-live-mock-design.md`.

**Legend**

| Tag | Meaning |
| :--- | :--- |
| **LIVE** | Backend capability exists; frontend can use it once `transport-live` bridge exists |
| **MOCK** | UI + mock-engine only; no real harness behavior yet |
| **HYBRID** | Partial backend signal; full UX mocked or incomplete |
| **BRIDGE** | Blocked on thin SSE/IPC pilot (Wave 1) — not a kernel gap |

Update this file whenever a mock surface flips to live.

---

## Operator / coding cockpit

| Feature | Backend | Frontend now | After bridge | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Submit coding `TaskSpec` / chat-as-goal | LIVE (CLI `sagiha run`) | MOCK | LIVE | No HTTP today → BRIDGE |
| Event stream (step/tool/gate/cost) | LIVE (EventBus) | MOCK | LIVE | Grow Zod to full `events.py` |
| Token / $ gauges | LIVE | MOCK | LIVE | From `model.call_completed` / CostSummary |
| Gate report / admitted | LIVE | MOCK | LIVE | `gate.evaluated` |
| Step timeline / trajectory | LIVE (SQLite) | MOCK | LIVE | `list_runs` / events_for_run |
| Resume thaw | LIVE (`--resume`) | MOCK | LIVE | Freeze files under `.sagiha/freeze/` |
| Operator pause / play | HYBRID (freeze API; no pilot) | MOCK | HYBRID→LIVE @ v2-S7 | |
| Mid-run steer | Spec only | MOCK | MOCK until v2-S7 | Tail-append; cache-safe |
| Token streaming (`model.delta`) | NotImplemented | MOCK | MOCK until v2-S7 | |
| Taint badge | LIVE | MOCK (wire display) | LIVE | `tool.taint_introduced` |
| Mutation approval UX | HYBRID (deny + requires_human) | MOCK | HYBRID→LIVE @ v2-S7 | Modal + `resolveApproval` |
| Compaction card | LIVE event | MOCK | LIVE | `context.compaction_applied` |
| Built-in tool rows (6 tools) | LIVE | MOCK | LIVE | |
| Replay player | LIVE CLI | MOCK UI | LIVE | Differentiator — prioritize |
| Trace export SFT/DPO | LIVE (`sagiha export`) | MOCK UI | LIVE | Wrap CLI or thin API |

## Context, memory, repo conventions

| Feature | Backend | Frontend | Notes |
| :--- | :--- | :--- | :--- |
| Prompt layers 1–7 inspector | Assembler live; no dump API | MOCK | Digests on steps only |
| AGENTS.md preview / editor | Consumed in prompts; no `init` | MOCK | `sagiha init` = v2-S6 |
| Skills.md / skill library | Conductor C6 | MOCK | |
| Short-term memory pane | InMemoryMemory only | MOCK | Ephemeral |
| Long-term / consolidator | Spec | MOCK | AETHER |
| Code graph / FTS / LSP | Scaffold empty | MOCK | v2-S6 |

## Workflow / AGI / swarm

| Feature | Backend | Frontend | Notes |
| :--- | :--- | :--- | :--- |
| Story-DAG drag-drop editor | ADR-0018 only | MOCK | n8n/ComfyUI UX; no execute |
| Integration / conflict repair | Spec | MOCK | |
| Queue / multi-run scheduler | None | MOCK | FleetGovernor |
| AETHER swarm topology | Spec | MOCK | Entire product area |
| Behaviours / DMARTIC ladder UI | Stuck detection partial | MOCK | |
| Best-of-N candidate UI | LIVE lib + `bench --compare` CLI; `search.enabled=false` by default | MOCK | Opt-in search after bridge; suite needed before default-on |
| RHI / self-improve mutations | Dormant | MOCK | |

## Config / models / harness params

| Feature | Backend | Frontend | Notes |
| :--- | :--- | :--- | :--- |
| Profile display (coding/analysis/review/chat) | Config schemas | MOCK editors; coding path LIVE-shaped | Only coding tools real |
| Model tier / role bindings | Config live | MOCK editor → read-only LIVE later | Hot-swap = new run |
| Spend caps / governor | LIVE in loop | MOCK editor → LIVE read | |
| Autonomy / sandbox status | Stub autonomous | MOCK | v2-S5 |
| MCP tools | Stub | MOCK | v2-S7 |
| Prompt engineering studio | None | MOCK | |

## Transport

| Feature | Backend | Frontend | Notes |
| :--- | :--- | :--- | :--- |
| `EventSource` interface | Piloting spec | Defined | apps must use factory only |
| MockEventSource | N/A | Target of FE-B | Implements full control verbs |
| LiveEventSource SSE/IPC | Missing | Stub package FE-B | See BRIDGE_CONTRACT.md |
| `SAGIHA_TRANSPORT=mock\|live` | N/A | Required | Default `mock` |

---

## UI labeling rule

- Any view or control that does not yet consume live events **must** show a `MOCK` badge in the GUI chrome and `[mock]` in CLI status lines.
- Cockpit may show `LIVE` only when `SAGIHA_TRANSPORT=live` and the bridge health check succeeds.
