---
status: normative
updated: 2026-07-30
---

# **SAGIHA — Current Status**

> [!IMPORTANT]
> This page is the single source of **implementation truth**. Architecture docs describe the SOTA
> *target*; this page says what exists today and what to build next. When a guide and this page
> disagree, this page wins.
>
> **Sprint 3a & 3b are closed (2026-07-30).** Full suite green in CI.
> **OpenAI-compatible provider adapter** (B.12) & `build_kernel` live/record binding (D3) delivered.
> **Block 2 (E0-lite benchmark harness)** is completed (`sagiha harvest`, `sagiha bench`, A/A noise floor calibration).
> Block 3 (Best-of-N search & path-scoped grants) is next.

Authority: [2026-07-29 Foundation Review](./reviews/doing/2026-07-29-foundation-review.md),
narrowed by the [2026-07-30 Final Review](../final_review_sagiha_concept_and_plan.md) ·
near-term contract: [Sprint 3a / 3b (both closed)](./sprints/sprint-3.md) · [Sprint 4 (E0 closed)](./sprints/sprint-4.md).

## **Doc Audit (C8) — Complete**

The 2026-07-30 final review's cheapest-leverage doc PR (**C8**) is done: broken links to the
foundation review now resolve (X17), SSOT language points at `src/sagiha/{ports,domain}/` rather
than the markdown contracts (X18), the mutation tool is named `apply_edit` everywhere to match
`Workspace.apply_edit` (X20), and every hexagonal port carries the tier it has actually earned —
`provisional` or `experimental`, none `stable` — matching the three-tier scheme in
[Port Stability & Versioning](./03-contracts-and-models/port-stability-and-versioning.md) rather
than a fourth `draft` label an earlier pass introduced (X16, corrected 2026-07-30). Sprint 3 is
split into **3a** (closed runnable loop) and **3b** (hardening) per **C3** — both closed
2026-07-30 — see [Sprint 3](./sprints/sprint-3.md).

## **What Works Now — Sprint 3a and 3b closed**

Commit history through the 2026-07-30 path-containment, CI-closure, and hardening passes. Marked
against code, not intent:

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
| Event bus + interceptors | Implemented — `anyio` task groups, per-observer `fail_after` timeout, quarantine on raise/timeout (**D16/D17 closed**) |
| Capability dispatch choke point | Implemented — grant verified at the point of effect, unconditionally (**R2 closed**: `verify_grant` is now mandatory on `PolicyEngine`) |
| SQLite-WAL trajectory store | Implemented (typed round-trip; NFS/non-local filesystem journal probe with fallback — probe closed) |
| Evaluator / real `GateReport` | Implemented — `admitted` is `all(g is True …)`, now in `outer_loop/evaluator/GateEvaluator`, bound through the `Evaluator` port (**R4 closed**) |
| Tool input schema validation (D13) | Implemented — `DefaultToolRegistry.dispatch` validates before invoking the handler |
| Unknown-tool deny path (C.16) | Implemented — `is_error=True` + `ToolCallFailed`, tested through the full `kernel.dispatch` path |
| Deny-path coverage beyond grant expiry (U1/D8) | Implemented — `always_gate` refusal with `requires_human=True`; interceptor denial and timeout both fail closed |
| Resumable run state (D9) | Implemented — `runs` table, `TrajectoryStore.upsert_run`/`get_run`, `RunLoop.run(resume=True)` derives `seq` from the store, `sagiha run --resume <run_id>` |
| `InMemoryMemory.recall` provenance filtering (D7) | Implemented — trust-ranked `min_provenance` filter |
| Kernel required ports non-optional (D14) | Implemented and regression-tested — was already true in the `Kernel` dataclass; the test was the gap |
| `ShortTermMemoryAdapter` | **Deleted (R7 closed)** — was wired zero times; `RunLoop` keeps history in-process |
| `kernel/react.py` | **Deleted (R1 closed)** — superseded by `RunLoop`; its two tests migrated to drive `RunLoop` instead |
| Port stability labels | **Corrected (R8 closed)** — every port is `provisional` or `experimental`; none claims `stable` |
| `import-linter` agency contract | **Enforced (R6 closed)** — `agency/run_loop.py` gives the contract real code to check; `unmatched_ignore_imports_alerting` no longer set to `warn` |
| Compaction algorithm spec (R9) | **Specified (closed)** — headroom 20%, keep-first-N=2, keep-last-M=6 in `prompt-architecture.md`; not yet implemented in `RunLoop` (out of scope for 3b) |
| Core dependency extras (R11) | **Closed** — `mcp`, `opentelemetry-*`, `lsprotocol`, `watchfiles` moved to optional extras; none was imported in `src/sagiha` |
| Runtime layer honesty (R5) | **Closed (docs)** — `car-model.md` and `runtime/__init__.py` state plainly that Runtime has no code until Block 5's sandbox |
| CI runs `tests/unit/` with coverage | **Implemented (D29 closed)** — `tests` job, 80% floor applied (measured 87–91%) |
| CI replay job | **Implemented (D28 closed)** — real `sagiha replay --verify` CLI invocation against a generated fixture cassette |
| Model provider | **OpenAI-compatible adapter implemented** — `OpenAIModelAdapter` in `adapters/model/openai.py` covers Ollama/Qwen/OpenAI/vLLM, 12 tests passing; `composition.py` wires `live`/`record`/`replay` modes |

## **What Does Not Work Yet**

| Capability | Lands |
| :--- | :--- |
| Compaction *implementation* in `RunLoop` (the algorithm is specified, R9) | Whenever prompt assembly needs it — no scheduled sprint |
| `sagiha bench` / harvest / A/A noise floor | Block 2 (E0-lite) |
| Path-scoped grants beyond built-in tools, approvals, admission | Block 3 |
| FTS5 + code-graph retrieval | Block 4 |
| Workflow DAG (`PRDSpec` → `StoryBoard`, [ADR-0018](./08-decisions/0018-native-workflow-dag.md)) | Block 4, gated on an E0 ablation |
| Container sandbox, worktrees, MCP, OTel | Block 5 |

## **Near-Term Contract — Sprint 3a Exit — ✅ Green in CI (2026-07-30)**

An e2e cassette test in CI where the agent:

```text
model response → ToolUseBlock → authorized tool → ToolResult
→ prompt history → GateReport → sagiha replay --verify
```

fixes a failing test in a fixture repo, with the grant verified at dispatch and every coding-profile
gate `True`/`False` (never `None`). Checklist: [Sprint 3a / 3b](./sprints/sprint-3.md).

**Closed.** `tests/unit/test_sprint3a_e2e.py` runs in CI's `tests` job (D29) and a real
`sagiha replay --verify` invocation against a committed fixture cassette runs in the `replay` job
(D28) — not merely on a branch, which is the distinction the final review's C3 insisted on. One
honest caveat remains, and it is explicitly outside what the exit sentence requires:

- It is satisfied against a **cassette, not a live model** — the loop is closed, but has never been
  closed against a real model, because the OpenAI-compatible provider adapter is not built. Running
  against Ollama/Qwen is tracked as a fast-follow, not a blocker to this sprint's definition of done.

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
| `sagiha run <goal> [--acceptance …]` | **Available now** (cassette or live via `OpenAIModelAdapter`) |
| `sagiha replay <run_id> --verify` | **Available now** — exercised by CI (D28 closed) |
| `sagiha run --resume <run_id>` | **Available now** (D9 closed) — `goal` optional when resuming |
| `sagiha harvest [--repo …]` | **Available now** — Block 2 (E0-lite) |
| `sagiha bench [--suite …] [--aa]` | **Available now** — Block 2 (E0-lite) |
| `sagiha init` | Planned — not scheduled |

## **Verify the Scaffold (today)**

```bash
uv run pytest tests/ -q --cov=src/sagiha --cov-report=term-missing   # what CI runs today
uv run lint-imports
uv run pyright src/sagiha
uv run sagiha version
uv run sagiha replay verify --verify \
  --cassette tests/fixtures/replay_smoke/cassette.json \
  --workspace tests/fixtures/replay_smoke/workspace \
  --trajectory-db /tmp/replay_check.db
```

`sagiha run` (including `--resume`), `sagiha replay --verify`, `sagiha harvest`, and `sagiha bench` execute, and CI enforces the full test suite (coverage-gated) and a real replay invocation. **Sprints 1, 2, 3a, 3b, and 4 (Block 2 E0-lite) are all completed.**

## **Next Items, In Order**

1. **Block 3 (Best-of-N candidate search)** — parallel candidate search across ephemeral worktrees + sequential repair.
2. **Block 4 (Retrieval, AST Code Graph, Workflow DAG)** — FTS5 + code graph retrieval, macro planning stages.
3. **Block 5 (Container Sandbox Perimeter, MCP, OTel, Multi-Agent)** — Podman container isolation, external tools, multi-agent swarms.
