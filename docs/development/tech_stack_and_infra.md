---
status: rationale
updated: 2026-08-06
---

# TECH_STACK_AND_INFRASTRUCTURE — Pre-Phase 1 Engineering Specification

**Owners**: CTO · Principal Architect
**Standing**: `rationale`. Nothing here overrides `spec.md`, `measurement.md`, or the ADRs; where a choice below can be a contract in code, the code is the contract and this file navigates. Every selection carries a **rejection trigger** — the measured condition under which it is replaced — in keeping with ADR-0001's "a trigger nobody has instrumented cannot fire."

---

## 1. Runtime & Language

| Item | Decision | Justification | Rejection trigger |
|:--|:--|:--|:--|
| Language | **Python 3.13** (pin `>=3.13,<3.14`) | Ratified (spec §3, ADR-0001). Free-threading and JIT builds are **not** enabled: both are experimental in 3.13 and the workload is I/O-bound (inference wall-clock dominates) | RT-1/RT-2/RT-3 per ADR-0001, measured per component |
| Concurrency | **stdlib `asyncio`** with `TaskGroup`, `asyncio.timeout`, `ExceptionGroup` handling. **No `anyio`, no `trio`** | 3.13 asyncio has structured concurrency natively. `anyio` buys backend-neutrality we will never use (no trio adapter is ever planned) at the cost of a dependency in the TCB's import graph. Zero-bloat rule applies | A named library forcing an anyio boundary (none in the current matrix does) |
| Process model | Single process; `ProcessPoolExecutor` for CPU-bound bursts (AST batch parses) behind an internal seam; sandboxed effects run in **containers**, never host subprocesses | Wire-serializable ports (I3) mean any component can move out-of-process later without caller changes — so we do not pre-pay for multiprocess architecture | RT-2 (RSS/idle-CPU) promotes the offending component to a sidecar |
| Package manager | **`uv`** — `uv.lock` committed; `uv sync --frozen` in CI; dependency groups `core` / `dev` / `bench` | Deterministic, fast, single tool for venv+resolve+lock. Lockfile is part of reproducibility: benchmark runs record the lock hash in the run manifest | — |
| Lint/type/format | `ruff` (lint+format), `pyright --strict` (zero errors, I2), `import-linter` (full lattice per spec §3 amendment) | Ratified in STATUS CI table | — |

**Version pinning policy.** Direct dependencies pinned to compatible-release (`~=`); the lockfile pins everything transitively. A dependency upgrade is a PR whose CI run includes the conformance suites — an upgraded adapter dependency is a changed adapter.

---

## 2. Library & Dependency Matrix

The bar for entry: **stdlib first; a dependency enters only when it is load-bearing for an invariant or a measured gate.** Every row names its owner seam so no library leaks across a port.

| Concern | Library | Version pin | Owner seam | Justification / notes |
|:--|:--|:--|:--|:--|
| Domain models & schema validation | **`pydantic` v2** (`~=2.9`) | v2 only; `model_config = ConfigDict(frozen=True)` on all domain models | `domain/`, `ports/` payloads | Already mandated (TASK-001). Rust-core validation is fast enough that a serialization sidecar trigger (below) is unlikely to fire early |
| JSON wire serialization | pydantic `model_dump_json` / `model_validate_json` | — | port boundaries | **`msgspec` rejected for now**: measurable speedup, but a second schema system violates the one-source-of-truth rule. Trigger: serialization > 5% of end-to-end task wall-clock on a recorded replay |
| YAML (workflow topologies, manifests, families) | **`ruamel.yaml`** (safe load only) | `~=0.18` | `workflow/` loader, `measurement/` manifests | Round-trip preservation matters for meta-loop edits to topology files (comments, ordering survive). `PyYAML` rejected: lossy round-trip. All loads are `safe`; **no arbitrary-object YAML anywhere, ever** (deserialization is an injection surface) |
| JSON Schema validation of declarative assets | **`jsonschema`** (`~=4.23`, Draft 2020-12) | — | `workflow/validator.py`, `measurement/` | Schemas in `SCHEMAS_AND_CONTRACTS.md`; validator is TCB (ADR-0014) |
| AST parsing (target code) | **`tree-sitter`** (`~=0.23`) + **`tree-sitter-language-pack`** | grammars pinned by the pack version | `adapters/indexer/`, T1 verification tier | Ratified (ADR-0011). Language pack gives pinned, prebuilt grammars for every SWE-bench language without per-grammar build steps |
| Shell command AST (classifier) | **`tree-sitter-bash`** (via the pack) | — | `kernel/shell_ast.py` | One parser technology for all parsing. `bashlex` rejected: unmaintained, POSIX-only. Classification-not-containment per ADR-0008 — a mis-parse is an escalation bug, not a perimeter breach |
| Git operations | **`git` CLI via `asyncio.subprocess`**, thin typed wrapper | system git `>=2.43` | `adapters/workspace/` | `GitPython`/`pygit2` rejected: GitPython leaks handles and is semi-maintained; pygit2 adds a C build for worktree ops the CLI does flawlessly. The wrapper is where the worktree-creation timer (ADR-0001) lives |
| HTTP (model endpoints) | **`httpx`** (`~=0.27`, async, HTTP/2) | — | `adapters/model_provider/` only | Single async HTTP client for all providers. Streaming via `httpx` SSE handling |
| Terminal UI | **`textual`** (`~=0.85`) | — | `tui/` (event-stream consumer only) | Pure consumer of the typed event stream (spec §8); zero privileged access, therefore free to choose the best TUI toolkit |
| Statistics | **stdlib only** (`math`, `random`, `statistics`) | — | `measurement/statistics.py` (TCB) | Ratified (ADR-0003): 259-LOC verbatim port, pinned JSON fixtures. `scipy` explicitly rejected from the TCB — the judge's dependency graph is minimized on principle |
| SQLite persistence (trajectory store) | **stdlib `sqlite3`** (WAL mode) via the `TrajectoryStore` adapter | — | `adapters/trajectory_store/` | An ORM is bloat for an append-heavy event log. Trigger for revisit: multi-writer or remote-store requirement (then a new adapter, not a rewrite — that is what the port is for) |
| Container control | **Podman CLI via `asyncio.subprocess`** (see §3) | podman `>=5.0` | `adapters/sandbox/` | No Python docker/podman SDK: the SDKs pin API versions and add daemon-socket coupling; the CLI is the stable interface and is already required on the host |

**Explicitly rejected (recorded so they are not re-litigated):** `langchain`/`llamaindex` (framework inversion of control violates the harness-owns-the-loop premise); `litellm` (see §4.2); `anyio` (§1); `msgspec`/`orjson` (until the serialization trigger fires); any DI container (ratified — explicit `composition.py`).

---

## 3. Execution Sandbox Strategy

**Runner: Podman, rootless, daemonless.** Docker rejected for the evaluation path: the root daemon is a standing host-privilege surface, and rootless Podman gives user-namespace isolation with an OCI-compatible CLI (images and Dockerfiles work unchanged; CI portability to Docker-only environments is a one-flag fallback, `--runtime docker`, kept working by the conformance suite).

### 3.1 Isolation contract (each item is a gate, not a description)

| Property | Mechanism | Verifying gate |
|:--|:--|:--|
| No network by default | `--network none` on every evaluation container; model calls happen **outside** the sandbox — the agent process talks to providers; the *patch under evaluation* never does | Canary: container attempts egress, must fail |
| No host filesystem | Only two mounts: the task worktree (RW) and the pinned environment image layers (RO). No home, no `/var/run` sockets, no `.pth` leakage — **fixes B3 by construction** | **B3 canary (ratified)**: deliberately broken candidate must fail evaluation |
| No privilege | `--userns=keep-id`, `--cap-drop all`, `--security-opt no-new-privileges`, read-only root FS, `--pids-limit`, memory & CPU limits from the `ResourceGovernor` lease | Conformance test inspects the container spec of a live run |
| Deterministic environment | Per-task **image digest pinned in the task manifest** (`manifest_schema`); container created from digest, never from tag | Manifest schema validation + digest verification at run start |
| Audited escape hatch | The only path from sandbox to host is the dispatcher-mediated tool result channel (stdout/exit-code/files-in-worktree), which enters context as `untrusted-external` (TaintGate) | I5 architecture test + TaintGate red-team gate |

### 3.2 Worktree topology

`git worktree add` per candidate, under a run-scoped temp root; container mounts exactly one worktree. Parallel candidates (M3 fan-out) = parallel worktrees = parallel containers; the governor's concurrency lease caps simultaneous containers. Worktree creation is timer-instrumented from day one (ADR-0001's F1 measurement).

### 3.3 Two container roles, one technology

- **Evaluation container** (TCB-side): runs the task's test command. Its image digest and test command hash are TCB data (manifest).
- **Tool-execution container** (agency-side): runs agent-requested shell commands after shell-AST classification and policy grant. Same isolation contract, separate image, separate lease class — so a runaway tool loop cannot starve the evaluator.

---

## 4. LLM Cost & Performance Harnessing

### 4.1 Prompt caching mechanics

Ratified frame (ADR-0010 + audit amendment): **the gated CI metric is harness-side prefix stability** — the byte-identical-prefix rate over a fixed recorded replay — because provider cache semantics differ and the B2 local endpoint may expose none. Provider-reported hit rate is a secondary metric where available.

Implementation contract for the context assembler (`agency/context/assembler.py`):

1. **Five layers, fixed order** (ADR-0010 rev.): L1 system/policy · L2 tool schemas · L3 repo brief · L4 task statement · L5 dialogue/trajectory. Layers L1–L4 are append-only within a run; only L5 mutates turn-to-turn.
2. **≤ 4 cache breakpoints**, emitted as provider-specific markers by the `ModelProvider` adapter (Anthropic: `cache_control: {type: "ephemeral"}` blocks; OpenAI-compatible: rely on automatic prefix caching — the adapter simply guarantees byte-stable prefixes; local endpoints: prefix stability still pays via KV-cache reuse in vLLM-class servers).
3. **Fan-out cache sequencing** (ADR-0010 consequence, TASK-033): under Best-of-N, candidate 1's request is issued and its prefix confirmed warm before candidates 2..N are released (a one-request barrier). Naive parallel fan-out re-pays the full prefix N times.
4. **Compaction never rewrites L1–L4.** The compactor operates on L5 only; a compaction that would touch a lower layer is a bug by type (the assembler exposes no API for it).

### 4.2 Routing — no LiteLLM

**Decision: routing lives behind the `ModelProvider` port as thin native adapters; LiteLLM is rejected.** Rationale: (a) LiteLLM is an in-process translation megalayer — 100+ provider shims we will use three of — squarely the bloat rule; (b) it owns retry/timeout/normalization policy internally, which duplicates and fights the `ResourceGovernor` and the dispatcher's single-choke-point accounting (I5): budget must be reserved *before* the call by our kernel, not retried opaquely inside a vendor layer; (c) its normalization lags provider features we depend on (cache-control blocks, fine-grained streaming events).

What we build instead is small: one adapter per provider (`anthropic_native.py`, `openai_compatible.py` — the latter covers the B2 local endpoint, vLLM, and most gateways), each ~200 LOC over `httpx`, each passing the same `ModelProvider` conformance suite (I4). A `RoutingModelProvider` composite adapter (policy: static per-role map from config; no learned routing before an ablation clears the floor) satisfies multi-model needs (ADR-0007 Architect/Editor seam) without any framework.

**Rejection trigger for this decision**: a fourth provider family with materially divergent semantics arriving in one quarter — then re-evaluate a translation layer *as an adapter implementation detail*, never as a port change.

### 4.3 Token conservation

- **Budgets are first-class**: every model call carries a `TokenBudget` (prompt ceiling, completion ceiling) from the governor lease; the adapter enforces `max_tokens` and truncation policy from it — conservation is a kernel policy, not a prompt-engineering hope.
- **Context diet by provenance**: tool outputs enter L5 with byte ceilings per tool class (test output: tail-biased truncation keeping the failure block — the repair edge needs the traceback, not the pass list).
- **Compaction v1** (TASK-024): deterministic structural compaction (drop superseded file snapshots, collapse resolved tool exchanges to one-line summaries) before any model-generated summarization is considered; model-summarized compaction is a *mechanism* and does not promote without its ablation (spec §7).
- **Measured, not assumed**: cost-per-resolved-task is a mandatory report column (ADR-0003 rev.2); token totals per layer are emitted as events so cost regressions are diffable per layer.

### 4.4 Streaming response handling

The `ModelProvider` port returns an **async iterator of typed `ModelStreamEvent`s** (`TextDelta`, `ToolCallDelta`, `Usage`, `StopReason`) — wire-serializable per I3 (an async iterator of serializable payloads crosses process boundaries as a stream; a callback does not). The adapter normalizes provider SSE framing; the agency loop consumes deltas for early tool-call dispatch (a complete tool call is dispatchable before the full completion finishes); the TUI consumes the same deltas from the event bus. Backpressure: bounded per-consumer queues on the bus; the model stream is never blocked by a slow UI consumer (drop-oldest for display consumers, never for the loop or the trajectory store).

### 4.5 `ResourceGovernor` budget triple — exact mechanism

Ledger semantics (full protocol skeleton in `CORE_SKELETONS_AND_PROTOCOLS.md` §4):

```
reserve(run_id, dims) -> Lease | InsufficientBudget     # atomic, pre-effect
commit(lease_id, actuals)                               # actuals ≤ reservation? release remainder : record Overrun
release(lease_id)                                       # cancel path; idempotent
```

- **Dimensions**: `usd_micros`, `prompt_tokens`, `completion_tokens`, `wall_clock_ms`, `concurrency_slots` (containers, model calls). Integers only — currency in micro-USD; float budget arithmetic is banned.
- **Atomicity**: single-process now ⇒ one `asyncio.Lock` around the ledger; the port is already async + serializable (I3), so the same protocol survives a future out-of-process governor unchanged.
- **Reserve-before-effect is enforced at the choke point**: `kernel/dispatch.py` will not dispatch an effect without a live lease — this is *why* after-the-fact accounting (the predecessor's Best-of-N failure, spec §5) cannot recur: it is structurally unrepresentable.
- **Overrun policy**: `commit` with actuals over reservation records a typed `BudgetOverrun` event and debits reality (the ledger never lies to itself); repeated overrun by one effect class trips a governor alarm that tightens that class's reservation multiplier. Estimation is conservative: reservations use ceiling estimators (prompt tokens counted exactly pre-call; completion reserved at `max_tokens`).
- **Fan-out**: N candidates ⇒ N child leases carved from one parent reservation; a child's release returns to the parent, not to the global pool — cancellation of N−1 losers refunds instantly and correctly.

---

## 5. Reproducibility spine (cross-cutting)

Every benchmark run records: `uv.lock` hash · git SHA of `src/aether/` · topology hash (ADR-0014) · task-manifest hash · model identifier + endpoint fingerprint · container image digests · seed. This tuple is the run's identity; two runs with equal tuples are the A/A design's definition of "identical configuration." It is emitted as the first event of every run and stored by the `TrajectoryStore`.
