---
status: normative
updated: 2026-07-30
---

# **SAGIHA — Current Status**

> [!IMPORTANT]
> This page is the single source of **implementation truth**. Architecture docs describe the SOTA
> *target*; this page says what exists today and what to build next. When a guide and this page
> disagree, this page wins until Sprint 3 closes.

Authority: [2026-07-29 Foundation Review](./reviews/2026-07-29-foundation-review.md) ·
near-term contract: [Sprint 3](./sprints/sprint-3.md).

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
| `sagiha run` / `sagiha replay` / resume | Sprint 3 (Block 1) |
| Multi-step run loop, prompt+history assembly | Sprint 3 |
| Built-in tools (`read_file`, `list_dir`, `grep`, `apply_edit`, `run_command`) | Sprint 3 |
| Live / record model modes; OpenAI-compatible (Ollama) adapter | Sprint 3 |
| Evaluator / `GateReport` from acceptance checks | Sprint 3 |
| Digest-verified cassette replay | Sprint 3 |
| Full CI unit tests + coverage + replay job | Sprint 3 |
| `sagiha bench` / harvest / A/A noise floor | Block 2 (E0-lite) |
| Path-scoped grants, approvals, admission | Block 3 |
| FTS5 + code-graph retrieval | Block 4 |
| Container sandbox, worktrees, MCP, OTel | Block 5 |

## **Near-Term Contract — Sprint 3 Exit**

An e2e cassette test in CI where the agent:

```text
model response → ToolUseBlock → authorized tool → ToolResult
→ prompt history → GateReport → sagiha replay --verify
```

fixes a failing test in a fixture repo. Checklist: [Sprint 3](./sprints/sprint-3.md).

## **Explicitly Deferred**

MCP stdio driver, OTel exporter, container sandbox, warm LSP, dense retrieval
([ADR-0014](./08-decisions/0014-defer-dense-retrieval.md)), best-of-N with N>1, AOI acting mode,
RHI/MetaImprover, A2A remote pilots, performance sidecars, streaming UI.

## **Commands Today vs Planned**

| Command | Availability |
| :--- | :--- |
| `sagiha version` | **Available now** |
| `sagiha run …` | Planned — Sprint 3 |
| `sagiha replay … --verify` | Planned — Sprint 3 |
| `sagiha bench …` / `harvest` | Planned — Block 2 |
| `sagiha init` | Planned — not scheduled |

## **Verify the Scaffold (today)**

```bash
uv run pytest tests/contracts/ -q
uv run lint-imports
uv run pyright src/sagiha
uv run sagiha version
```

Replay and run verification land with Sprint 3; do not treat them as working until that sprint's
exit test is green.
