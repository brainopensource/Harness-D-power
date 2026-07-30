---
status: normative
updated: 2026-07-30
---

# **SAGIHA — Current Status**

> [!IMPORTANT]
> This page is the single source of **implementation truth**. Architecture docs describe the SOTA
> *target*; this page says what exists today and what to build next. When a guide and this page
> disagree, this page wins until Sprint 3a closes.

Authority: [2026-07-29 Foundation Review](./reviews/doing/2026-07-29-foundation-review.md),
narrowed by the [2026-07-30 Final Review](../final_review_sagiha_concept_and_plan.md) ·
near-term contract: [Sprint 3a / 3b](./sprints/sprint-3.md).

## **Doc Audit (C8) — Complete**

The 2026-07-30 final review's cheapest-leverage doc PR (**C8**) is done: broken links to the
foundation review now resolve (X17), SSOT language points at `src/sagiha/{ports,domain}/` rather
than the markdown contracts (X18), the mutation tool is named `apply_edit` everywhere to match
`Workspace.apply_edit` (X20), and every hexagonal port is labeled `draft` rather than `stable` until
a second adapter exists (X16). Sprint 3 is split into **3a** (closed runnable loop) and **3b**
(hardening) per **C3** — see [Sprint 3](./sprints/sprint-3.md). This doc pass changed no code.

## **What Works Now (Sprint 2 scaffold + Sprint 3a partial)**

Commit `7d8956a` (2026-07-30) landed most of Sprint 3a. Marked against code, not intent:

| Area | Status |
| :--- | :--- |
| Domain models & typed ports in `src/` | Implemented |
| Port-shape meta-conformance (`tests/contracts/`) | Implemented |
| Import-linter CAR layering | Implemented |
| Config security refusals (subprocess+autonomous, host network, tests_unmodified) | Implemented |
| `ModelRequest` v2 (system, tools, sampling, role) | Implemented |
| Digest-keyed cassette replay + `CassetteMismatchError` | Implemented |
| `ToolUseBlock` → `ToolCall` resolution, effect from registry | Implemented |
| `call_id` + `is_error` on `ToolResult` and completion events | Implemented |
| `GateReport.admitted` cannot admit on `None` coding gates | Implemented |
| Typed event reads through `ALL_EVENTS` + `upcasters.py` | Implemented |
| `RunLoop` — max steps, budget, `end_turn`, stuck signature | Implemented |
| Prompt + history assembly into `ModelRequest` v2 | Implemented |
| Five built-in tools over a root-confined local workspace adapter | Implemented |
| Schema-declared path scoping (key-guessing deleted) | Implemented |
| `sagiha run` / `sagiha replay --verify` | Implemented |
| Path containment enforced before a grant is minted | Implemented (traversal, sibling-prefix, symlink escape) |
| Event bus + interceptors (basic) | Partial (asyncio; no observer timeout/quarantine until 3b) |
| Capability dispatch choke point | Implemented — grant verified at the point of effect (shape debt: **R2**) |
| SQLite-WAL trajectory store | Implemented (typed round-trip; NFS journal probe is 3b) |
| Evaluator / real `GateReport` | Implemented — `admitted` is `all(g is True …)` (location debt: **R4**) |
| Model provider | **Cassette only** — no live/local adapter exists |

## **What Does Not Work Yet**

| Capability | Lands |
| :--- | :--- |
| **CI running `tests/unit/` at all** (**D29**) — the e2e test and every deny-path test exist, and nothing executes them | Sprint 3a |
| **Working replay job** (**D28**) — CI invokes flags the CLI does not define | Sprint 3a |
| **OpenAI-compatible (Ollama/Qwen) adapter — no run against a real model is possible** | Sprint 3a |
| **`model.mode=live` / `record` binding** (both fail closed at composition today) | Sprint 3a |
| Tool input validation against the registered JSON Schema (D13) | Sprint 3a |
| Unknown-tool deny test (C.16) | Sprint 3a |
| Resume, `anyio` bus + observer timeout, provenance filtering, NFS journal probe | Sprint 3b |
| Refactor register **R1–R11** — duck-typed `get_grant`, path key-guessing fallback, evaluator location, unwired `ShortTermMemoryAdapter`, port stability labels, deps in core | Sprint 3b |
| `sagiha run --resume` / resumable run state | Sprint 3b |
| `anyio` bus timeouts + quarantine | Sprint 3b |
| Deny-path security tests beyond grant expiry; NFS journal probe | Sprint 3b |
| `sagiha bench` / harvest / A/A noise floor | Block 2 (E0-lite) |
| Path-scoped grants beyond built-in tools, approvals, admission | Block 3 |
| FTS5 + code-graph retrieval | Block 4 |
| Workflow DAG (`PRDSpec` → `StoryBoard`, [ADR-0018](./08-decisions/0018-native-workflow-dag.md)) | Block 4, gated on an E0 ablation |
| Container sandbox, worktrees, MCP, OTel | Block 5 |

## **Near-Term Contract — Sprint 3a Exit**

An e2e cassette test in CI where the agent:

```text
model response → ToolUseBlock → authorized tool → ToolResult
→ prompt history → GateReport → sagiha replay --verify
```

fixes a failing test in a fixture repo, with the grant verified at dispatch and every coding-profile
gate `True`/`False` (never `None`). Sprint 3 is not "closed" until this test is green in CI — a
partial implementation on a branch does not count (final review C3). Checklist:
[Sprint 3a / 3b](./sprints/sprint-3.md).

**Status: the test exists and passes locally** (`tests/unit/test_sprint3a_e2e.py`), **and CI does
not run it** (D29). Two honest caveats on the exit sentence as written:

1. It is satisfied against a **cassette, not a live model** — the loop is closed, but has never been
   closed against a real model, because the provider adapter is not built.
2. "Green in CI" is not yet true of anything under `tests/unit/`. Until D29 is fixed, treat the loop
   as **demonstrated, not verified**.

## **Explicitly Deferred**

MCP stdio driver, OTel exporter, container sandbox, warm LSP, dense retrieval
([ADR-0014](./08-decisions/0014-defer-dense-retrieval.md)), best-of-N with N>1, AOI acting mode,
RHI/MetaImprover, A2A remote pilots, performance sidecars, streaming UI, Workflow DAG / `PRDSpec` /
`StoryBoard` ([ADR-0018](./08-decisions/0018-native-workflow-dag.md) — non-goal until Sprint 3a's
exit test is green).

## **Commands Today vs Planned**

| Command | Availability |
| :--- | :--- |
| `sagiha version` | **Available now** |
| `sagiha run <goal> [--acceptance …]` | **Available now — cassette-driven only** (no live provider) |
| `sagiha replay <run_id> --verify` | **Available now** — not yet exercised by CI (D28) |
| `sagiha run … --resume` | Planned — Sprint 3b |
| `sagiha bench …` / `harvest` | Planned — Block 2 |
| `sagiha init` | Planned — not scheduled |

## **Verify the Scaffold (today)**

```bash
uv run pytest tests/contracts/ -q     # what CI runs today
uv run pytest tests/unit/ -q          # 3a loop, tools, gates, path containment — NOT run by CI yet
uv run lint-imports
uv run pyright src/sagiha
uv run sagiha version
```

`sagiha run` and `sagiha replay --verify` execute, but only against a committed cassette. **Sprint
3a is not closed**: the exit test lives in `tests/unit/test_sprint3a_e2e.py` and CI does not run it,
so nothing yet enforces the one sentence that defines done. Treat the loop as demonstrated, not
verified, until [Sprint 3a](./sprints/sprint-3.md) items D.18/D.19 land.

## **Next Items, In Order**

Sequenced by dependency rather than by architecture level. Full detail and evidence in
[Sprint 3a](./sprints/sprint-3.md); shape debts are the **R1–R11** register in
[`todo_list_development.md`](../todo_list_development.md).

1. **CI runs `tests/unit/` with `--cov`, and a replay job whose flags match the CLI** (D29, D28).
   Cheapest item here and the one that converts 3a from *written* to *closed* — 47 local tests
   currently guard nothing.
2. **OpenAI-compatible provider adapter** behind the `openai` extra — the one blocker for running
   against a local model.
3. **`build_kernel` `live` / `record` binding** — depends on (2).
4. **Tool input schema validation** (D13) and the **unknown-tool deny test** (C.16) — the two
   remaining 3a checklist gaps.
5. **Sprint 3b**, taking the refactor register with it: **R2** (`get_grant` onto the port), **R3**
   (delete the path key-guessing fallback, fail closed), **R4** (evaluator into
   `outer_loop/evaluator/`), **R7** (delete `ShortTermMemoryAdapter`) land before Block 2 records a
   corpus against the wrong shapes.

Item 1 first: until CI runs the suite, every claim below it rests on tests that only ever ran on a
developer's machine.
