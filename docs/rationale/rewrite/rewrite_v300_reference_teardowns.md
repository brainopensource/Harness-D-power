---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Reference Teardowns

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Satisfies **D-03** of the [Phase-0 charter](../reference/PLANNING.md) and grounds RFP
[§3](../reviews/review_project_rewrite_v300.md). Each reference produces a **take** and a **reject**
column with file-level citations. *Reading code without producing an artifact is entertainment, not
research.*

Reference trees are cloned into `src/<name>/`, gitignored, excluded from `ruff` and `pyright`, and
never imported. Paths to them appear here as code spans, never as markdown links — the trees do not
exist in CI.

---

## 0. Study policy — binding on this project

**We study concepts. We do not copy implementation.**

1. **Only open-source and officially published sources are cloned.** Every tree below carries a
   permissive license (MIT/Apache-2.0) that allows study; that permission is not the reason for the
   rule. The reason is that AETHER is a greenfield system whose value is its own measured design.
2. **De-obfuscated or decompiled artifacts are deferred, not permanently excluded.** Third-party
   de-minified bundles of closed CLIs circulate publicly. They are **not in scope now**. If they are
   ever brought in, it will be as a separate, explicitly recorded decision with its own legal review
   — never silently, and never as a source of code.
3. **What transfers is theory, not text.** Published computer science, algorithms, protocol shapes,
   and design patterns are the transferable layer. A competitor's specific implementation is not.
4. **Convergence requires our own evidence.** If AETHER later adopts a design decision that
   resembles a competitor's, the justification must be **our own KPIs** — an ablation on our suites,
   against our noise floor, recorded in `docs/rationale/benchmarks/`. "Hermes does it" is not a
   reason. "Our ablation shows +N points, CI excluding the noise floor" is.
5. **Dependencies are open-source only, license class reviewed on addition.** See
   [runtime decisions §4.4](./rewrite_v300_decisoes_runtime.md).

---

## 1. Hermes — `NousResearch/hermes-agent`

The primary competitor. MIT licensed. **~233,000 lines of Python**, plus ~274k TypeScript and ~171k
TSX across the web and TUI surfaces, and ~459k lines of markdown. The `agent/` package alone
contains **135 modules**.

### Take

| Mechanism | Where | Why it matters to AETHER |
| :--- | :--- | :--- |
| **Anthropic prompt-cache placement** | `agent/prompt_caching.py` | The single most directly applicable artifact in any reference. Default layout places **4 `cache_control` breakpoints** — static system prefix, end of system prompt, and the last 2 non-system messages — falling back to one system breakpoint plus the last 3 messages when no static prefix exists; uniform TTL (5 m or 1 h). Implemented as **pure functions with no agent dependency**, which is exactly the shape a port-based design needs. This is precisely the capability SAGIHA declared in `pyproject.toml` and never built |
| Context engineering split | `agent/context_engine.py`, `context_compressor.py`, `conversation_compression.py`, `context_breakdown.py`, `context_references.py` | Compaction, breakdown reporting and reference tracking are separate concerns rather than one compactor |
| Trajectory compression | `trajectory_compressor.py` (1,598 LOC) | Long-horizon transcript reduction as a first-class component |
| Session search | `hermes_state_search.py` (2,229 LOC) | FTS5 search over past sessions with LLM re-summarization on recall — the long-term-memory shape AETHER wants |
| Closed learning loop | `skills/` (14 bundles), `agent/skill_bundles.py`, `skill_commands.py`, `skill_preprocessing.py`, `learn_prompt.py` | Agent-authored, versioned, self-improving procedure files, created after complex tasks and refined during use. The differentiating capability |
| Scheduling | `cron/scheduler.py`, `jobs.py`, `executions.py`, `lifecycle_guard.py` | Cron-driven autonomous missions with a lifecycle guard — the long-horizon autonomy surface |
| Tool-result trust classification | `agent/tool_result_classification.py`, `tool_guardrails.py` | Independent arrival at the same conclusion as SAGIHA's TaintGate: tool output needs a trust class, not just a value |
| Benchmark runner in-tree | `mini_swe_runner.py` (732 LOC) | A working SWE-bench runner living beside the agent, not in a separate harness |

### Reject

| What | Why |
| :--- | :--- |
| **The 135-module flat `agent/` package** | `anthropic_adapter.py`, `bedrock_adapter.py`, `azure_identity_adapter.py`, `codex_responses_adapter.py`, `copilot_acp_client.py` and `conversation_loop.py` all live in the same package with no interface between them. There is no hexagonal seam: provider adapters, the loop, billing, display and credential pooling are peers. This is the concrete form of "breadth over depth" |
| 20+ messaging platforms, 6 terminal backends | `gateway/`, `acp_adapter/`, `plugins/`, `apps/` — surface area AETHER does not need in Phase 1, and PLANNING.md **R9** names copying it as a named risk |
| 233k LOC of control plane | AETHER's competing claim is that a disciplined ~15k-LOC core with real port boundaries outperforms this on resolve-rate-per-dollar. That claim is falsifiable and is the reason to build the thing |

### The competitive read

Hermes wins on **capability breadth and a genuinely closed learning loop**. It has no visible
capability-security model, no port/adapter boundary, and no published noise floor or ablation
record. AETHER's wedge is not more features — it is **measured features**: a smaller core where
every mechanism has an ablation showing it earned its place. See
[measurement strategy](./rewrite_v300_measurement_strategy.md).

---

## 2. Hermes Self-Evolution — `NousResearch/hermes-agent-self-evolution`

Small and dense: **3,892 lines of Python**. DSPy + GEPA applied to a running agent.

**Take.** The partition of the mutable surface is the whole lesson:
`evolution/{prompts, skills, code, tools, core, monitor}` — four *separately evolvable targets*
rather than one "improve the agent" objective, plus a monitor and a report generator
(`generate_report.py`). AETHER's meta-loop adopts the same partition, with one addition Hermes does
not appear to enforce: the evolvable surface is defined by **exclusion from the TCB** (invariant
I8), so `code` evolution can never reach policy, evaluator, gates, or benchmark definitions.

**Reject.** Nothing structural at this size. The dependency on DSPy/GEPA is deferred, not declined —
`planning_future_sprints.md` §3 already places prompt evolution at S13, and it needs a trajectory
corpus that does not yet exist.

---

## 3. Claude Code CLI — `anthropics/claude-code`

**The CLI source is not published here.** The repository is 229 files: ~32,000 lines of markdown,
~7,600 lines of Python across `scripts/` and `examples/`, ~750 lines of TypeScript, plus `plugins/`,
`Script/`, `CHANGELOG.md`, `SECURITY.md`. The shipped CLI is distributed as a compiled npm artifact.

This corrects a premise in the RFP: there is no official TypeScript implementation to read.

### Take

| Artifact | Lesson |
| :--- | :--- |
| `settings.json` permission schema | Three-valued `allow` / `ask` / `deny` with rule matching per tool and per argument pattern. Deny-first, and *ask* as a first-class state rather than a fallback — AETHER's `PolicyEngine` returns `Decision`, and `ask` is the state that makes an autonomous agent usable rather than merely safe |
| Hooks | Pre/post-tool interception as a **configuration** surface, not a plugin API. The user extends behavior without extending the type system |
| Slash commands + plugin manifests | `plugins/`, `.claude-plugin/` — extension by declaration, resolved at load. Aligns with ADR-0013 (entry points resolved once, then frozen) |
| Memory injection | The `CLAUDE.md` / `AGENTS.md` convention: project instructions injected into the stable prefix, therefore cached, therefore free after the first turn |
| `CHANGELOG.md` | The most useful file in the repository. A dated record of which capabilities a production coding CLI added and in what order — a prioritization signal that cost someone years to generate |

### Reject / defer

- **De-obfuscated bundles: deferred** per §0.2. Not cloned, not read, not in scope now.
- TypeScript control plane — see [runtime decisions §2](./rewrite_v300_decisoes_runtime.md).
- Single-workspace model. AETHER needs N parallel candidate worktrees for System-2 search.

---

## 4. OpenCode — `sst/opencode`

**~484,000 lines of TypeScript** and ~142k TSX. Real source, permissively licensed, actively
developed.

**Take.** Auto-compaction triggered at a context-utilization threshold rather than on overflow;
the LSP integration shape (a warm server pool as a diagnostics source, not a code-navigation
feature); SQLite session and message persistence; TUI interaction patterns for streaming output and
diff review.

**Reject.** The architecture wholesale. The ReAct loop is less rigorous than the dual-process design
AETHER inherits from SAGIHA, and half a million lines of TypeScript is the opposite of the thin core
this project is arguing for.

---

## 5. Codex CLI — `openai/codex`

**~60,000 lines of Rust** across ~80 crates, plus ~50k Python and ~10k TypeScript. Apache-2.0. The
most instructive *decomposition* in the reference set.

### Take

| Crate | Lesson |
| :--- | :--- |
| **`apply-patch`** | The most valuable single artifact for RFP §4-B. Its modules are `parser.rs`, **`seek_sequence.rs`**, `streaming_parser.rs`, `invocation.rs`. `seek_sequence` is anchor-sequence matching — locating a hunk by its surrounding context lines rather than by line number — which is the robustness property a search/replace editor lives or dies on. `streaming_parser.rs` shows patch application beginning **before the model finishes emitting it**. Directly informs [the edit mechanism](./rewrite_v300_mecanismo_edicao.md) |
| **`execpolicy`** | A dedicated crate for command authorization policy, separate from execution. The same separation as SAGIHA's `kernel/policy/effects.py::classify_command`, arrived at independently — good evidence the seam is real |
| **`bwrap`, `linux-sandbox`, `sandboxing`, `windows-sandbox-rs`** | Sandboxing as several small crates behind one abstraction, with a per-platform backend. AETHER's Podman perimeter is one backend of the same shape |
| **`exec-server`, `exec-server-protocol`** | Command execution behind a **protocol**, not a function call — the concrete form of invariant I3 (wire-serializable ports) |
| **`app-server-protocol`, `app-server`, `app-server-transport`** | A published UI↔engine wire protocol as its own crate, with the transport separated from the schema. This is the design [UI and TUI](./rewrite_v300_uiux_tui.md) adopts |
| **`code-mode`, `code-mode-host`, `code-mode-protocol`, `code-mode-runtime`** | Code-mode tool orchestration — the agent writes a script that calls tools via RPC, collapsing an N-round-trip pipeline into one context-cheap turn — is decomposed into protocol / host / runtime. Corroborates Hermes' independent version of the same idea |

### Reject

A full Rust control plane, for the reasons in [runtime decisions §2](./rewrite_v300_decisoes_runtime.md).
Also the ~80-crate decomposition itself: it is right for a compiled multi-platform binary with a
large team, and it would be ceremony in a Python core where a module boundary costs nothing.

---

## 6. Grok Build — `xai-org/grok-build`

**~274,000 lines of Rust**, `crates/{build, codegen, common}`.

**Take.** Crate layout as a template for a *sidecar* if a [reversal trigger](./rewrite_v300_decisoes_runtime.md)
ever fires; worktree-based concurrency; codegen discipline for generated types.

**Reject.** Wholesale Rust, again. Included in the reference set for the sidecar question, not the
control-plane question.

---

## 7. SAGIHA — `src/sagiha/`

Full treatment in [the audit](./rewrite_v300_auditoria_sagiha.md). Summarized here for the
take/reject table's completeness:

**Take.** The CAR model and single dispatch choke point with grants verified at the point of effect;
port conformance suites driven by reflection; import-linter contracts; tri-state gates that report
`None` instead of lying; the A/A noise-floor protocol; the docs budget ratchet; the loud-stub
doctrine; and the H1–H4 honesty audit as a permanent cautionary tale.

**Reject.** Anything measured before its instruments were verified — which, in SAGIHA's case, is
every number it ever produced.

---

## 8. Capability provenance

Every `core` capability in [PLANNING.md §5](../reference/PLANNING.md) traces to a reference or is
declared original.

| Capability | Provenance |
| :--- | :--- |
| Long-session autonomy / hibernation | Hermes `cron/lifecycle_guard.py`; SAGIHA `FrozenRunState` |
| Short-term memory / compaction | Hermes `agent/context_compressor.py`; OpenCode threshold auto-compact; SAGIHA `ExchangeCompactor` |
| Long-term memory | Hermes `hermes_state_search.py` |
| Code indexing | SAGIHA `adapters/indexer/`, `code_graph/treesitter.py`; Aider repomap |
| Prompt caching | **Hermes `agent/prompt_caching.py`**; Anthropic caching protocol |
| Cache economics | Anthropic pricing model — write 1.25× / read 0.1× |
| Skills | Hermes `skills/`, `agent/skill_bundles.py` |
| Code-mode tool orchestration | Codex `code-mode-*` crates; Hermes RPC tool scripts |
| Workflow DAG + memoization | ComfyUI node graph. **No reference in this set implements it for agent cognition** — original to AETHER |
| Config-driven pipeline | ComfyUI; SAGIHA composition root |
| Dual-process loop | SAGIHA `agency/run_loop.py` + `adapters/search/best_of_n.py` |
| Parallel isolation | Grok Build; SAGIHA `adapters/workspace/worktree.py` |
| Sandboxing | Codex `bwrap`/`linux-sandbox`/`sandboxing`; SAGIHA `adapters/sandbox/` |
| Hooks & permissions | Claude Code `settings.json` schema and hook surface |
| Edit mechanism | **Codex `apply-patch/seek_sequence.rs`**; Aider search/replace blocks; SAGIHA `apply_edit` with `expected_occurrences` |
| Wire protocol | Codex `app-server-protocol` |
| LSP diagnostics | OpenCode; SAGIHA `ports/lsp.py` (declared, never implemented) |
| Sub-agent delegation | Hermes `agent/delegation_context.py`; Claude Code |
| MCP interop | Claude Code; Codex `codex-mcp` |
| Meta-loop (RHI) | **Hermes self-evolution `evolution/{prompts,skills,code,tools}`**; SAGIHA RHI design |
| Deterministic replay | SAGIHA `adapters/model/cassette.py`. **No other reference in this set has it** — a genuine differentiator |
| Trajectory export | Hermes `trajectory_compressor.py`; SAGIHA `outer_loop/export/` |
| Observability | OpenHands event stream; SAGIHA `domain/events.py` |
| Measurement discipline | **Originates here.** No reference in this set publishes a noise floor, an ablation record, or a private held-out suite |

The last row is the thesis. Every competitor in this set has more features than AETHER will have in
Phase 2. None of them can tell you which of those features actually works.
