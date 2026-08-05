---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Audit of `src/sagiha/`: Keep / Refactor / Delete

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Answers RFP [§5.1](../reviews/review_project_rewrite_v300.md). Companion to
[reference teardowns](./rewrite_v300_reference_teardowns.md) and the
[architecture blueprint](./rewrite_v300_blueprint_arquitetura.md).

---

## 0. Summary judgment

`src/sagiha/` is **12,949 LOC across 106 Python files**, with 8,197 LOC of tests (a 0.63:1 ratio).

The honest verdict is uncomfortable in both directions. SAGIHA's *mechanisms* are mostly ordinary —
a run loop, a tool registry, an SQLite store. Its *discipline* is not: reflection-driven port-shape
contracts, import-linter layer enforcement, a CI checker that fails on silent stubs, tri-state gates
that report `None` instead of lying, and a documented history of **deleting** a component
(`SequentialCandidateSearch`, audit M-8) rather than leaving a false-success shell behind. That
discipline is the asset. A rewrite that ports the code and drops the discipline would be a
regression disguised as progress.

Against that, the base has a structural defect the discipline did not catch: **five of seventeen
ports have no implementation at all**, `stream()` raises `NotImplementedError` on every model
adapter, and the run loop reaches around its own port contracts six times via `getattr` duck-typing.
The enforcement is strong on the boundaries that exist and blind to boundaries that were declared
and never built.

| Verdict | Files | LOC | Share |
| :--- | ---: | ---: | ---: |
| **Keep** — port to `src/aether/` with minimal change | 41 | ~5,150 | 40% |
| **Refactor** — the idea survives, the implementation does not | 27 | ~5,400 | 42% |
| **Delete** — no adapter, no caller, or actively misleading | 38 | ~2,400 | 18% |

The 40% Keep figure is the number that justifies a rewrite rather than a refactor: a
majority of the tree either changes shape or disappears, and the parts worth keeping are
self-contained enough to move without dragging the rest.

---

## 1. Keep — port with minimal change

These are the components whose absence would be expensive to rediscover. Each is small,
well-tested, and has no dependency on the parts being deleted.

### 1.1 The security perimeter (the crown jewel)

| Component | Path | LOC | Why it survives |
| :--- | :--- | ---: | :--- |
| Dispatch choke point | `src/sagiha/kernel/dispatch.py` | 179 | Single call site for every effect. `authorize()` → **unconditional** `verify_grant()` → `governor.acquire()` → `registry.dispatch()` → `release()` in a `finally`. Verifying the grant at the point of effect, not merely at issuance, is the property most implementations get wrong |
| Policy engine | `src/sagiha/kernel/policy/engine.py` | 213 | Path containment, effect classes, deny-by-default. TCB |
| Per-call effect narrowing | `src/sagiha/kernel/policy/effects.py` | 52 | `classify_command()` re-classifies `run_command` per invocation instead of trusting a static table |
| Container perimeter | `src/sagiha/adapters/sandbox/container.py` | 372 | Rootless Podman. Sandbox is the perimeter (ADR-0006); no command blocklisting |
| Egress allowlist proxy | `src/sagiha/adapters/sandbox/egress.py` | 132 | Network containment, not just filesystem |
| Resource governor | `src/sagiha/kernel/governor.py` | 122 | Lease acquire/release, budget accounting |

**The design rule to carry verbatim:** no `Grant` object ever crosses a port signature —
`PolicyEngine` returns a `grant_id` and nothing else. This is what makes grants un-forgeable by a
caller and un-serializable into a frozen state file. Restated in
[the security spec](./rewrite_v300_seguranca_sandbox.md).

### 1.2 The measurement instruments

| Component | Path | LOC | Why it survives |
| :--- | :--- | ---: | :--- |
| Statistics | `src/sagiha/e0/statistics.py` | 259 | Exact McNemar, Holm–Bonferroni correction, seeded bootstrap CI. **Pure stdlib**, pinned JSON fixtures. Rewriting this is pure downside risk |
| Gate evaluator | `src/sagiha/outer_loop/evaluator/gate_evaluator.py` | 206 | Tri-state `bool \| None` grading. The `None` is the point: an ungradeable criterion reports "not measured", never `True` |
| Repo cache | `src/sagiha/e0/repo_cache.py` | 99 | Keep the *interface*; the implementation is the M1b blocker (§4.1) |
| Benchmark suite definition | `benchmarks/definitions/s0-core.json` | — | 30 SWE-bench Lite tasks, 12 repos, full 40-char SHAs, each annotated `validated: false`. TCB |

### 1.3 Determinism and contract enforcement

| Component | Path | LOC | Why it survives |
| :--- | :--- | ---: | :--- |
| Cassette record/replay | `src/sagiha/adapters/model/cassette.py` | 123 | Digest-keyed on `request_digest(request)`; raises `CassetteMismatchError` rather than falling through. The entire deterministic-test substrate |
| Port-shape reflection suite | `tests/contracts/test_port_shape.py` | — | Enforces invariants **generically across all ports** by `inspect`/`typing` reflection: every method async, no untyped `dict` crosses a boundary, all payloads serializable, no `Grant` in any public signature, all datetimes aware |
| Adapter conformance | `tests/contracts/test_adapter_conformance.py` | — | Includes a meta-test that fails when a required port/adapter pair has no conformance coverage |
| Import contracts | `.importlinter` | — | 5 contracts: layer ordering, pure domain, pure ports, TCB isolation |
| Loud-stub checker | `scripts/check_loud_stubs.py` | — | CI-enforced doctrine that a stub raises rather than returns a plausible value |
| Docs gates | `scripts/docs_budget.py`, `scripts/check_links.py` | — | Word-budget ratchet and link resolution. Both stdlib-only, no install step |

### 1.4 Mechanisms worth keeping

| Component | Path | LOC | Note |
| :--- | :--- | ---: | :--- |
| Exchange compactor | `src/sagiha/agency/context/compactor.py` | 235 | Whole-exchange granularity, token-budgeted. Never truncates mid-tool-call |
| Freeze/thaw state | `src/sagiha/agency/freeze.py` | 40 | `FrozenRunState` carries **no grant** — grants are re-minted on thaw, never restored |
| Git worktree manager | `src/sagiha/adapters/workspace/worktree.py` | 190 | Zero-copy candidate isolation |
| FTS5 indexer | `src/sagiha/adapters/indexer/` | 645 | AST-bounded chunking, walk, frontmatter awareness. Disk-backed |
| Tree-sitter code graph | `src/sagiha/adapters/code_graph/treesitter.py` | 539 | Imports/calls/co-change edges |
| SFT/DPO exporter | `src/sagiha/outer_loop/export/` | 411 | Eligibility gating, redaction, license check — the parts people forget |

---

## 2. Refactor — the idea survives, the implementation does not

### 2.1 `agency/run_loop.py` (725 LOC) — the highest-value refactor

The repair loop added in v2-S7f is correct and is the single largest score lever in the tree. Its
container is not.

**What is right and must be preserved:**
- Repair lives **inside** the run loop, sharing one transcript, one compaction budget, one `run_id`.
- The gate verdict re-enters as a **tool-result-shaped message** via `assembler.append_exchange`,
  never as a second system prompt — a second system prompt forks the stable prefix and destroys the
  cache hit rate.
- `_repair_signature` (sha256 over failed gates + output tail, **excluding the attempt number**)
  aborts on `no_progress` instead of burning budget on an identical retry.
- Stuck detection at `_STUCK_REPEAT_THRESHOLD = 3` identical tool signatures.
- The RC-1 fix: every skipped `tool_use` block gets a synthetic error `ToolResult`, so the
  transcript never contains a dangling `tool_use` id and stays resumable.

**What must change:**

1. **Six duck-typed escape hatches.** `bind_run`, `last_failover`, `remaining_wall_clock_s`,
   `is_tainted`, `mark_tainted`, and `workspace.root` are all reached via
   `getattr(obj, name, None)` + `callable()`. These are six real capabilities routed *around* the
   port contracts the rest of the architecture spends heavily to enforce. `thaw()` carries an
   explicit `# type: ignore[attr-defined]` to reach `workspace.root`, directly violating the
   documented rule that `Workspace` exposes no path. **In AETHER each becomes a declared port
   method or does not exist.**
2. **Two loops, one class.** `run()` (repair) and `_step_phase()` (steps) are 128 and 268 lines in
   one type with 17 constructor parameters. Split into a step executor and a repair supervisor with
   an explicit state machine.
3. **Provider failover leaks through the loop.** The loop polls `model.last_failover` and re-emits
   it because adapters cannot import `kernel.bus`. That is a real layering constraint solved the
   wrong way — the adapter should return failover as part of its typed result.

### 2.2 Other refactors

| Component | LOC | Problem | Direction |
| :--- | ---: | :--- | :--- |
| `domain/config.py` | 571 | A single module owning profile, autonomy, gates, model roles, context, budget, search, sandbox, workflow and telemetry | Split per-concern; each subsystem owns and validates its own config slice |
| `cli.py` | 805 | Largest file in the tree; command definitions, composition wiring and output formatting interleaved | Thin command layer over a headless engine API. The CLI becomes one client of the event stream, not a privileged path — see [UI/TUI](./rewrite_v300_uiux_tui.md) |
| `composition.py` | 517 | Composition root doing real work | Keep the pattern (ADR-0004: no DI container). Shrink by pushing construction into each adapter package |
| `adapters/model/openai.py` | 343 | Speaks raw `/v1/chat/completions` over `httpx`, defaults to `localhost:11434` (Ollama). Only reads back `cached_tokens`; emits **no** `cache_control` | Two adapters: a native Anthropic adapter (cache breakpoints, extended thinking) and an OpenAI-compatible one. See [context & cache](./rewrite_v300_contexto_memoria.md) |
| `adapters/tools/builtins.py` | 303 | Six core tools, no glob, no multi-edit, no sub-agent, no plan/todo, no web | Expand the catalog with effect classes assigned per tool from the start |
| `adapters/memory/short_term.py` | 61 | In-process only; not memory in any durable sense | Replace with the STM/LTM split |
| `domain/events.py` | 580 | Discriminated union carrying a pyright waiver (`reportIncompatibleVariableOverride`) | Keep the catalog; revisit the union encoding so the waiver is unnecessary |
| `adapters/search/` | 671 | `BestOfNSearch` is real and wired into the benchmark runner; `scoring.py:113` raises `NotImplementedError` on one construction path | Keep BoN; complete or delete the scorer path |
| `tests/unit/` | ~6,000 | 49 files named for the sprint that produced them (`test_sprint3a_phase1.py`, `test_block5_scaffolding.py`) — coverage by concern is unreadable | Re-file by concern when porting. Sprint names are archaeology, not organization |

---

## 3. Delete — no adapter, no caller, or actively misleading

### 3.1 Ports with zero implementations (the port-rent rule, ADR-0023)

| Port | LOC | Status |
| :--- | ---: | :--- |
| `ports/orchestrator.py` | 21 | **Zero implementations anywhere.** Declared as "the single headless signature everything reduces to", yet `RunLoop` is called directly from `cli.py`, `composition.py` and `e0/runner.py`. The contract was never load-bearing |
| `ports/lsp.py` | 24 | Zero implementations. `Kernel.lsp_adapter` exists at `composition.py:72` and is always `None`. The `lsprotocol` extra is dead weight |
| `ports/toolchain.py` | 30 | Zero implementations. Referenced only in comments — this is why `coverage_not_decreased` honestly reports `None` |
| `ports/advisory.py` | 25 | Zero implementations |
| `ports/meta_improver.py` | 22 | Zero implementations |

None of these are bad ideas. `Toolchain` and `LSPAdapter` in particular re-enter AETHER as
`growth`-tier capabilities. But a `Protocol` with no adapter is a design sketch that type-checks,
and shipping five of them taught the codebase that declaring a boundary is the same as having one.
**AETHER starts with the ports that have adapters and adds each new one together with its first
adapter and its conformance test, in the same change.**

### 3.2 Empty and misleading surfaces

| Path | LOC | Reason |
| :--- | ---: | :--- |
| `src/sagiha/aoi/` | 4 | Docstring-only package. `planning_future_sprints.md` §2 lists "AOI statistical control plane" as a capability whose implementation is *an empty package* |
| `src/sagiha/runtime/` | 6 | Docstring-only package redirecting to `adapters/sandbox` |
| `ModelProvider.stream()` | — | Declared on the port; raises `NotImplementedError` in **all three** adapters. Its docstring names a conformance test (`test_stream_emits_exactly_one_usage_before_end`) that **does not exist in `tests/`**. Streaming is a real requirement — it returns in AETHER as a port method with a working adapter and that test actually written |
| `adapters/mcp/driver.py` | 37 | `invoke_tool` raises `NotImplementedError("v2-S7")`; `list_tools()` returns `[]`. Honest, but it is a stub occupying a name |
| `adapters/telemetry/otel.py` | 26 | `on_event` raises `NotImplementedError("v2-S7")` |
| `pyproject.toml` exclusions | — | Ruff excluded `src/claude_code`, `src/grok_build`, `src/hermes_agent`, `src/open_code` while none existed on disk. Now repopulated by the teardown clones — the entry was stale, not wrong |

The `anthropic` and `google` extras are declared in `pyproject.toml` with no code behind them. The
`anthropic` extra's comment — "cache_control prompt caching, extended thinking" — describes exactly
the capability the project most needs and never built.

---

## 4. Two defects that must not survive the rewrite

These are not code smells. They are the reason this project has produced **zero valid benchmark
numbers** in its lifetime, and any roadmap that does not fix them first repeats the outcome.

### 4.1 The E0 runner cannot materialize SWE-bench tasks

`docs/rationale/benchmarks/noise-floor.md` records the A/A run attempted 2026-08-01 failing on all
30 tasks × 2 passes with `fatal: invalid reference:`. Cause: the runner executes
`git worktree add <base_commit>` against the **local** repository, while SWE-bench base commits
live in twelve upstream repositories that were never cloned. The printed `mean_delta: 0.000` /
`Pass rate: 0.0%` are quoted in that file *only so nobody mistakes them for a result*.

Consequence: `search.enabled` and `retrieval.enabled` both remain `false` in the shipped default
config, because no measurement ever justified turning them on.

### 4.2 The editable install defeated worktree isolation

`docs/rationale/benchmarks/s4-harvest-findings.md` defect D3: the editable install's `.pth` file
placed the live `src/` on `sys.path` inside every isolated worktree. Every candidate's tests
therefore imported the same working tree, making candidate diffs **invisible to the gates scoring
them**. Two companion defects: pytest-uncollectable files in `failing_test_cmd` (D1) and exit-127
"command not found" scored as a test failure (D2).

An isolation mechanism that silently does not isolate is worse than none, because it produces
numbers. Both defects belong to the measurement layer, which is why AETHER's roadmap puts
**instruments before capability** — see [measurement strategy](./rewrite_v300_measurement_strategy.md).

---

## 5. What carries over that is not code

Ranked by how expensive it would be to rediscover:

1. **The honesty doctrine.** Four gates once hardcoded to `return True`
   (`docs/rationale/benchmarks/s1_before_baseline.md`); fixing them dropped the measured pass rate
   to 0.0%, and *the drop was the fix*. A gate that cannot fail is the most expensive class of bug
   this project can have.
2. **Delete rather than shim.** `SequentialCandidateSearch` was removed instead of left as a
   false-success shell. `adapters/search/__init__.py` still documents the removal.
3. **Contracts live in code.** `AGENTS.md`: a `Protocol` or `BaseModel` defined in a `.md` file is
   a bug. This audit and every sibling document navigate to `src/`; they never redefine.
4. **Reflection over enumeration.** Testing an invariant generically across all ports catches the
   port added next month. Per-port assertions do not.
5. **Wire-serializable ports.** Every port method `async`, no `Path`, file handle, callable,
   generator or live object crossing a boundary. Nearly free on day one, impossible to retrofit,
   and the property that lets any port move to a sidecar later without touching a caller — see
   [runtime decisions](./rewrite_v300_decisoes_runtime.md).

---

## 6. Migration ledger

| SAGIHA source | AETHER destination |
| :--- | :--- |
| `kernel/dispatch.py`, `kernel/policy/`, `kernel/governor.py` | `src/aether/kernel/` — near-verbatim, TCB |
| `adapters/sandbox/` | `src/aether/adapters/sandbox/` — near-verbatim |
| `e0/statistics.py` | `src/aether/measurement/statistics.py` — verbatim, fixtures included |
| `outer_loop/evaluator/` | `src/aether/measurement/evaluator/` — TCB |
| `adapters/model/cassette.py` | `src/aether/adapters/model/cassette.py` |
| `agency/context/{assembler,compactor,tokens}.py` | `src/aether/context/` — assembler gains explicit cache breakpoints |
| `agency/run_loop.py` | `src/aether/agency/{step_executor,repair_supervisor}.py` — split, de-duck-typed |
| `agency/freeze.py` | `src/aether/agency/hibernation.py` |
| `adapters/{indexer,code_graph}/` | `src/aether/adapters/retrieval/` |
| `adapters/workspace/`, `adapters/tools/`, `adapters/trajectory/`, `adapters/search/` | same-named packages under `src/aether/adapters/` |
| `outer_loop/export/` | `src/aether/measurement/export/` |
| `e0/{runner,harvester,reporter,repo_cache}.py` | `src/aether/measurement/` — `repo_cache` reimplemented per §4.1 |
| `cli.py`, `composition.py`, `domain/config.py` | Rewritten, not ported |
| `aoi/`, `runtime/`, `adapters/mcp/`, `adapters/telemetry/`, the 5 adapterless ports | Not carried |

`src/sagiha/` stays on disk, unmodified, for the duration of the rewrite. It is the reference
implementation and the source of the replay fixtures; it is retired only when AETHER passes the
same conformance suite.
