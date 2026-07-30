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

## **What Works Now (Sprint 2 scaffold)**

| Area | Status |
| :--- | :--- |
| Domain models & typed ports in `src/` | Implemented |
| Port-shape meta-conformance (`tests/contracts/`) | Implemented |
| Import-linter CAR layering | Implemented |
| Config security refusals (subprocess+autonomous, host network, tests_unmodified) | Implemented |
| Event bus + interceptors (basic) | Partial |
| Capability dispatch choke point | Partial (happy path; policy mostly permissive) |
| SQLite-WAL trajectory store | Partial (writes work; event reads are lossy until Sprint 3) |
| Cassette model stub | Partial (index replay; no request digest) |
| CLI | `sagiha version` only |

## **What Does Not Work Yet**

| Capability | Lands |
| :--- | :--- |
| `sagiha run` / `sagiha replay` | Sprint 3a (Block 1) |
| Multi-step run loop with stuck-signature stop condition | Sprint 3a |
| Prompt+history assembly | Sprint 3a |
| Built-in tools (`read_file`, `list_dir`, `grep`, `apply_edit`, `run_command`) with schema path scoping + grant verification at dispatch | Sprint 3a |
| Live / record model modes; OpenAI-compatible (Ollama) adapter | Sprint 3a |
| Evaluator / `GateReport` with non-`None` coding gates | Sprint 3a |
| Digest-verified cassette replay | Sprint 3a |
| Full CI unit tests + coverage + replay job | Sprint 3a |
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
| `sagiha run …` | Planned — Sprint 3a |
| `sagiha replay … --verify` | Planned — Sprint 3a |
| `sagiha run … --resume` | Planned — Sprint 3b |
| `sagiha bench …` / `harvest` | Planned — Block 2 |
| `sagiha init` | Planned — not scheduled |

## **Verify the Scaffold (today)**

```bash
uv run pytest tests/contracts/ -q
uv run lint-imports
uv run pyright src/sagiha
uv run sagiha version
```

Replay and run verification land with Sprint 3a; do not treat them as working until that sprint's
exit test is green.
