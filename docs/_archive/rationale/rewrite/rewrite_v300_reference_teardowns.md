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

### Take — the seven mechanisms worth stealing outright

Read at depth rather than surveyed. Ranked by what they change in AETHER's design.

#### T1. Compaction summaries are re-read as instructions — `agent/context_compressor.py` (6,789 LOC)

**The most valuable single insight in the entire reference set, and it is not architectural.**

A compaction summary re-enters the context as text the model reads. If that summary carries a
`## Next Steps` or `## Remaining Work` heading, **the model reads them as current directives** — so
after compaction it starts "wrapping up" work already finished, or treats a historical to-do as live.
The summary silently becomes a competing instruction source.

Hermes' fix is verbatim-worthy:

- Every forward-looking heading is renamed to a **historical** one: `## Historical Task Snapshot`,
  `## Historical In-Progress State`, `## Historical Pending User Asks`, `## Historical Remaining Work`.
- The block is wrapped in `[CONTEXT COMPACTION — REFERENCE ONLY]`.
- An explicit **precedence rule** ships inside the summary: where the historical block diverges from
  the latest message, *the latest message wins* — discard the historical section entirely, do not
  wrap up.
- The summarizer preamble is **filter-safe**: prior turns are framed as *source material to preserve*,
  never as instructions. This is prompt-injection defense **at the compaction boundary** — a boundary
  most designs do not treat as a trust boundary at all.
- Secrets are redacted during summarization by explicit instruction, not hoped away.

The file also carries the scar tissue: a code comment records that the `REFERENCE ONLY` framing once
**bled into general tool-use suppression** — the model read it as "don't act" and stopped calling
tools. The wording had to be tuned back. That is exactly the kind of finding that costs a week and is
invisible from the outside.

Six further mechanics from the same module, all adopted:

| Mechanic | Why |
| :--- | :--- |
| **Tool-output pruning as a cheap pre-pass** before LLM summarization | Do not pay a model to read output you were going to discard |
| **Token-budget tail protection** instead of a fixed message count | A fixed "keep last N" keeps 20 trivial turns or truncates 2 large ones |
| **Scaled summary budget**, proportional to the compressed content | A fixed summary size over-summarizes small regions and under-summarizes large ones |
| **Iterative summary updates** across successive compactions | Directly counters the documented "repeated compression loses nuance" decay |
| Auxiliary (cheap) model for summarization, with a **startup feasibility probe** | `conversation_compression.py` checks the aux model's window against the main model's compression threshold, auto-lowers the threshold when it can, and hard-rejects an aux below a minimum. A summarizer that cannot fit what it must summarize fails at the worst moment |
| Historical media stripping; head **and** tail protected | Images in compacted history are pure cost |

#### T2. Tool-loop guardrails as a pure decision component — `agent/tool_guardrails.py` (632 LOC)

SAGIHA's stuck detection is one threshold: three identical tool signatures. Hermes' is a **typed
policy object** and it is strictly better.

- **Three distinct signals, each with its own thresholds**: exact repeated failure (warn 2 / block 5),
  same-tool repeated failure (warn 3 / halt 8), and idempotent no-progress (warn 2 / block 5).
- **`idempotent_tools` and `mutating_tools` are separate sets.** No-progress detection is only
  meaningful for idempotent tools — re-reading a file and getting the same bytes is a loop; re-running
  a mutating command and getting the same result is not necessarily one. SAGIHA's single signature
  counter cannot express this.
- **Warnings on by default; hard stops opt-in.** Interactive sessions get a nudge; circuit-breaker
  behavior is a deliberate config choice. A harness that halts an interactive user on a heuristic is
  worse than one that warns.
- **The controller is side-effect free**: it observes tool calls and *returns decisions*. Runtime code
  decides whether a decision becomes warning guidance, a synthetic tool result, or a controlled halt.
  Pure policy, impure runtime — the same separation AETHER draws at every other boundary.
- **One failure classifier, shared.** `classify_tool_failure` deliberately mirrors the CLI's
  user-visible `[error]` tag *exactly*, "so the guardrail never disagrees with the CLI". Divergence
  between what the system counts as a failure and what the user sees as a failure is a debugging
  nightmare, and this closes it by construction.

#### T3. Background review — writing memory without touching the conversation — `agent/background_review.py`

After a turn, fork the agent into a daemon thread, replay a conversation snapshot, and ask *"should
any skill or memory be saved or updated?"*. Writes go to the memory and skill stores.

**The main conversation and the prompt cache are never touched.** The fork inherits the parent's live
runtime — provider, model, base URL, credentials, and the cached system prompt — **so it hits the same
prefix cache**.

This is the "fork operations must reuse the parent's exact prefix" rule from
[context & cache §1](./rewrite_v300_contexto_memoria.md) implemented in production, and it solves a
problem AETHER has not addressed: *when* does an agent write memory? Doing it in-loop costs tokens and
pollutes the transcript; doing it never means no learning. Doing it in a cache-sharing fork costs a
cheap tail on an already-warm prefix.

#### T4. The curator — the answer to skill-corpus rot — `agent/curator.py` (2,019 LOC)

[Context & memory §5.3](./rewrite_v300_contexto_memoria.md) identifies a problem and does not solve
it: an agent-authored skill corpus grows monotonically, and past ~150 always-on rules adherence
degrades. Hermes has the missing half.

A **curator** periodically reviews agent-created skills and maintains the collection: auto-transitions
lifecycle states from derived activity timestamps, then spawns a forked review agent that can **pin,
archive, consolidate, or patch** skills.

Two design choices worth copying exactly:

- **Inactivity-triggered, no cron daemon.** It runs when the agent is idle *and* the last run is older
  than an interval. Maintenance work costs nothing during active work and needs no separate scheduler
  to supervise.
- **Consolidation is a first-class outcome**, alongside archival — the corpus can get *smaller and
  denser*, not merely shorter. The module tracks "absorbed into" declarations so a consolidated skill
  records where its content went.

#### T5. API error classification as a taxonomy — `agent/error_classifier.py` (1,841 LOC)

A structured taxonomy plus a **priority-ordered classification pipeline** that maps an API failure to a
recovery action: retry · rotate credential · fail over to another provider · **compress context** ·
abort. Explicitly written to replace "scattered inline string-matching".

SAGIHA has exactly that scattered string-matching (`_is_transient()` in `fallback.py`). AETHER's
[disposition ladder](./rewrite_v300_mecanismo_edicao.md) covers *gate* failures and says nothing about
*API* failures — this is the missing sibling. The detail that makes it more than a lookup table:
**"compress context" is a recovery action.** A context-length error is not a retry and not an abort; it
is a signal to compact and continue.

#### T6. The evaluation-to-training pipeline — `mini_swe_runner.py` · `batch_runner.py` · `trajectory_compressor.py`

Three components that compose, which is the point:

- A SWE runner over **local / Docker / Modal** execution environments, emitting trajectories in a
  single canonical format.
- A batch runner over the same format.
- A **trajectory compressor** that post-processes completed trajectories to a target token budget
  *while preserving training signal*: protect the first turns (system, human, first assistant, first
  tool) and the last N; compress only the middle, starting from the second tool response; compress
  only as much as needed; replace the compressed region with a single summary message; **keep the
  remaining tool calls intact** so the model continues working after the summary.

That last constraint is the non-obvious one — compression for *training data* has different invariants
than compression for *runtime context*, and conflating them produces a corpus that teaches the model to
stop after a summary.

#### T7. Smaller mechanisms worth carrying

| Mechanism | Where | Value |
| :--- | :--- | :--- |
| **Prompt-cache placement as pure functions** | `agent/prompt_caching.py` (393 LOC) | 4 breakpoints — static system prefix, end of system prompt, last 2 non-system messages; fallback to 1 + last 3 without a static prefix; uniform TTL. No class state, no agent dependency. Already adopted in [context & cache §1.2](./rewrite_v300_contexto_memoria.md) |
| **Turn prologue extracted as a unit** | `agent/turn_context.py` (1,267 LOC) | ~470 lines of straight-line per-turn setup lifted out of the loop. Carries **preflight compaction** (compact *before* the call, not on overflow) and **idle compaction**. AETHER's `RunLoop` refactor has the same shape of problem |
| **Composable toolsets** | `toolsets.py` (1,003 LOC) | Named tool groups, composable from other groups, dynamically resolved. Tool-surface management as config — relevant to scoped sub-agent registries |
| **Delegated children fail closed** | `agent/delegation_context.py` | Context-local state that scrubs the parent's dispatcher env vars for delegated children **without mutating global env**. A child must not inherit the parent's identity |
| **Memory providers: exactly one** | `agent/memory_manager.py` | Registering a second external memory provider is rejected — "prevents tool schema bloat and conflicting backends". A hard cap on extension surface, enforced |
| **MoA as a turn mode, not a tool** | `agent/moa_loop.py` (2,384 LOC) | Mixture-of-Agents marks *one user turn* as MoA-enabled; the normal loop still owns tool calling and termination. Multi-model consultation without a second control flow |
| **Session insights from the state DB** | `agent/insights.py` | Token consumption, cost, tool-usage patterns, activity trends, model breakdowns — computed from the trajectory store, not a separate telemetry pipeline |
| Session search | `hermes_state_search.py` (2,229 LOC) | FTS + trigram + CJK over past sessions, as a mixin over the session DB |

### Reject

| What | Why |
| :--- | :--- |
| **The 135-module flat `agent/` package** (110,000 LOC) | `anthropic_adapter.py`, `bedrock_adapter.py`, `azure_identity_adapter.py`, `codex_responses_adapter.py`, `copilot_acp_client.py` and `conversation_loop.py` (7,336 LOC) all live in the same package with no interface between them. There is no hexagonal seam: provider adapters, the loop, billing, display and credential pooling are peers. This is the concrete form of "breadth over depth" |
| **`cli.py` at 18,485 lines** | One file, larger than SAGIHA's entire source tree. The natural end state of a CLI that is the only surface — and the reason [A-004](./rewrite_v300_decisoes_adr.md) makes every surface a protocol client |
| 20+ messaging platforms, 6 terminal backends | `gateway/`, `acp_adapter/`, `plugins/` (337 files), `apps/` — surface area AETHER does not need in Phase 1, and PLANNING.md **R9** names copying it as a named risk |
| 233k LOC of control plane | AETHER's competing claim is that a disciplined ~15k-LOC core with real port boundaries outperforms this on resolve-rate-per-dollar. That claim is falsifiable and is the reason to build the thing |

**A caveat on the reject column.** The mechanisms in T1–T7 are excellent *because* they were forged
against 233k lines of production traffic across many platforms — the scar tissue is the product of the
breadth we are declining. We take the findings without taking the surface, and we should be honest
that this is having it both ways: our core will be missing failure modes Hermes has already found.
The mitigation is the measurement discipline, which is the one thing Hermes does not publish.

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

This corrects a premise in the RFP: there is no official TypeScript implementation to read. Two
third-party trees partially fill the gap at different provenance classes — see §3b.

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

## 3b. Secondary Claude Code sources — `src/claude_refs/`

Two further trees, of **different provenance classes**. The distinction matters under §0 and is
recorded rather than glossed.

### 3b.1 Community field guide — `claude-code-ultimate-guide`

~210,000 lines of markdown across 626 files: an independent, citation-carrying practitioner guide with
per-claim confidence tiers, field data, and named sources. **Provenance is clean** — original analysis
and community observation, not derived from proprietary source.

This is the single most productive reference in the entire set, and not for architecture. Its value is
**quantitative field constraints that no code teardown yields**:

| Contribution | Where it landed |
| :--- | :--- |
| Context rot is structural (n² attention); MECW ~92% of advertised; a **non-linear** quality cliff near ~70% of budget; shipped auto-compaction triggers spanning 75–95% | [context & memory §5](./rewrite_v300_contexto_memoria.md) — and the *spread* is the finding: our trigger is an ablation parameter, not a copied constant |
| Degradation hits **monitor and classifier models too** (recall 98.6% → 88% with 800K benign tokens prepended) | The Best-of-N judge gets its own context budget |
| The **~150-instruction ceiling** and adherence-by-size curve | A rule budget on AETHER's own frozen prefix; a second reason for progressive skill loading |
| **Failure-triggered context drift** — error output dilutes intent independently of context size | [edit mechanism §1.3](./rewrite_v300_mecanismo_edicao.md) — a real gap in the ported repair loop |
| Blast-radius success rates (1–3 files ~85% → 8+ ~40%); session limits (15–25 turns, 80–100K tokens) | Decompose rather than widen the working set |
| Sandbox escape vectors: domain fronting, Unix-socket escalation, `$PATH` write escalation | [security §2.1](./rewrite_v300_seguranca_sandbox.md) — an allowlist entry is a capability grant |
| Sub-agent depth-1 rationale; hub-and-spoke; **context is never inherited**; team size as a context-pressure decision | [autonomy §7](./rewrite_v300_autonomia_agi.md) |
| Chain-of-thought costs compound in 20+ tool-call runs; the reversal curse on fine-tuning | Reasoning depth is per-step; the trajectory corpus is behavioral, not a knowledge substitute |

**Reject:** the tool-inventory and workflow-recipe material — it describes a product we are not
building. And every number above is someone else's; each enters as a **hypothesis to re-measure**, per
[measurement strategy §1](./rewrite_v300_measurement_strategy.md).

### 3b.2 Architecture analysis — `claude-code-analysis`

An 801-line reverse-engineering teardown of the Claude Code source tree (MIT-licensed, dated
2025-03-31): module inventory, tool and command counts, state shape, task taxonomy, architectural
patterns.

> **Policy note — this sits in the grey zone of [§0.2](#0-study-policy--binding-on-this-project).** It
> is not code and does not enable copying an implementation, but it *is* derived from analysis of a
> closed source tree, which §0.2 defers. It was not commissioned by this project and is already
> public; the resolution taken here is to use it **only at capability-inventory altitude** — the level
> equally available from Claude Code's public documentation and `CHANGELOG.md` — and to take no design
> decision from it that is not independently supported by an open source or by our own measurement.
> **Flagged for the reviewer rather than resolved silently.** If that reading is too permissive, the
> deletion cost is low: nothing below is load-bearing.

**Take, at that altitude** — as a capability checklist confirming what a mature coding CLI ships:

- **Scale as calibration.** ~1,884 TypeScript files, 41 tools, 101 slash commands, 130+ UI components,
  300+ utility modules. Useful as a reality check on scope: the surface a polished product carries is
  an order of magnitude beyond a measured core, and most of it is not the agent loop.
- **Compaction is not one mechanism but three** — full compaction, automatic triggering, and
  *micro-compaction* (selective message pruning), plus memory persistence across compaction. AETHER
  has one compactor; selective pruning is the cheaper, lossier sibling already noted as an ablation
  target in [context & memory §2](./rewrite_v300_contexto_memoria.md), and this is corroboration that
  the split is real rather than theoretical.
- **A task-type taxonomy**, not a single "background job" — local shell, local sub-agent, remote agent,
  in-process teammate, workflow, monitor. Relevant when AETHER's scheduling lands: these are different
  lifecycles, not one with flags.
- **Permission-first execution and plan mode as a tool-restricted state** — corroborates the
  three-valued permission model and the read-only planning surface already adopted.
- **Cost tracking as a named subsystem**, not a logging afterthought.

**Reject:** the TypeScript/React/Ink stack, the 100-command surface, and every product feature
(voice, bridge, desktop) — surface area we are explicitly not building.

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
| Context budget thresholds | Community field guide (§3b.1) — adopted as parameters to measure, not constants |
| Failure-drift mitigation | Community field guide (§3b.1) |
| Sandbox escape vectors | Community field guide (§3b.1) |
| Sub-agent topology constraints | Community field guide (§3b.1); Codex depth enforcement |
| Measurement discipline | **Originates here.** No reference in this set publishes a noise floor, an ablation record, or a private held-out suite |

The last row is the thesis. Every competitor in this set has more features than AETHER will have in
Phase 2. None of them can tell you which of those features actually works.
