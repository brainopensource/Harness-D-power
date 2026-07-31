---
status: rationale
updated: 2026-07-30
---

# **Harness Projects vs. SAGIHA — Comparative Analysis**

> [!NOTE]
> **Status: rationale, not normative.** This document compares four shipping coding harnesses against
> the SAGIHA architecture proposed in `docs/01`–`docs/08`. It defines no contracts and overrides no
> ADR. Where it recommends a change, that change becomes real only when it lands in
> [`03-contracts-and-models/`](../../03-contracts-and-models/) or an ADR — not by being written here.

---

## **1. Scope, Method, and the Honest Baseline**

Four reference harnesses were reviewed from the overviews in
[`docs/reference/harness_examples/`](../../reference/harness_examples/), cross-checked against the
vendored sources in `src/claude_code/`, `src/grok_build/`, `src/hermes_agent/`, and `src/open_code/`:

| Project | Vendor | Language | Scale | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Claude Code** | Anthropic | TypeScript / Node+Bun | ~1,897 `.ts`/`.tsx` files | Shipping, proprietary source-available |
| **Grok Build** | xAI | Rust | ~2,402 files / 75 crates | Shipping, source-available |
| **Hermes Agent** | Nous Research | Python 3.11–3.13 | ~3,634 `.py` files | Shipping, MIT |
| **OpenCode** | Community | Go 1.24 | 140 `.go` files | **Archived** (successor: Crush) |

**The baseline must be stated before any comparison is fair.** All four ship. SAGIHA does not.
`src/sagiha/` currently holds ~2,359 lines: domain models, port Protocols, a partial kernel, and a
composition root. The [2026-07-29 Foundation Review](../doing/2026-07-29-foundation-review.md)
records eighteen code-verified defects in that skeleton, beginning with D1 — *the ReAct loop can never
dispatch a tool*. The rest of this document compares a **specification** against four **products**.

That asymmetry cuts both ways, and both directions matter:

* Every SAGIHA advantage identified below is an advantage **on paper**. A pristine-test gate that has
  never rejected a candidate has rejected nothing.
* Every reference-project weakness identified below is a weakness **discovered by shipping**. Claude
  Code's brittle string-replacement edits and Hermes's 816KB `cli.py` are the residue of real users and
  real deadlines, not of careless design. SAGIHA has not yet earned the right to that kind of scar.

The useful output is therefore not a scoreboard. It is a list of things SAGIHA specifies that no
reference project has (keep these — they are the thesis), and things all four learned the hard way that
SAGIHA's documents do not yet account for (add these before writing the code, because they are cheap
now and expensive later).

---

## **2. Dimension-by-Dimension Comparison**

### 2.1 Architecture & Decoupling

| | Claude Code | Grok Build | Hermes | OpenCode | **SAGIHA (specified)** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Shape** | Layered service, monolithic core | Strict layered, 75-crate workspace | Semi-monolithic + 100-module `agent/` package | Clean architecture, Go `internal/` | Hexagonal ports + CAR three-layer + microkernel |
| **UI ↔ core boundary** | React/Ink over shared state | **ACP (IPC protocol)** — fully decoupled | Gateway adapters over shared core | **Pub/sub broker** — fully decoupled | EventBus; TUI is an `Observer` with **no privileged access** |
| **Boundary enforcement** | Convention | Crate graph (compiler) | Convention | `internal/` (compiler) | **`import-linter` contracts in CI** |
| **Core size** | `QueryEngine.ts` + `query.ts` ≈ 1,700 lines | Distributed across actors | `cli.py` 816KB, `run_agent.py` 332KB | `agent.go` compact | Target: no file > ~500 lines |

**Reading.** Grok Build and OpenCode independently converged on the same conclusion SAGIHA reaches from
first principles: *the UI must not be able to block or privilege itself over the agent core.* Grok pays
for it with an IPC protocol; OpenCode with a pub/sub broker; SAGIHA with an event bus plus an
Observer/Interceptor split. Three independent derivations of one property is strong evidence the
property is right.

SAGIHA's differentiator is that it is the only one enforcing the boundary **mechanically in a dynamic
language**. Rust and Go get encapsulation from the compiler for free; Python does not, which is exactly
why `import-linter` layer contracts are load-bearing rather than decorative. Hermes is the control
experiment — same language, same ambition, no mechanical boundary, and the result is an 816KB entry
point.

Where SAGIHA is exposed: Grok's own listed weakness is over-fragmentation (~75 crates, painful
navigation, actor spaghetti). SAGIHA specifies more distinct mechanisms than Grok encodes — profiles,
grants, leases, interceptors, conformance suites, AOI advisories, sidecars, coprocessors — with none of
it validated by a running system. **The Python analogue of Grok's crate sprawl is a plausible failure
mode for this project, and nothing in the current docs guards against it.**

### 2.2 Execution Flow

| | Approach | Loop control | Escalation |
| :--- | :--- | :--- | :--- |
| Claude Code | Async generator `query()` → `queryLoop()`, dispatches on `stop_reason` | Auto-extend on `max_tokens`; tool errors returned to model for self-correction | None — the model decides |
| Grok Build | `SessionActor` + `MvpAgent`, ACP `SessionCommand` in / `SessionNotification` out | Lifecycle hooks `TurnStart`/`TurnDone`/`TurnAbort` | **Goal system**: orchestrator, planner, tracker, strategist, classifier, evaluator, stop-detector, summarizer |
| Hermes | `agent/conversation_loop.py` (~3,900-line function) | `IterationBudget` + `ToolCallGuardrailController` | Conversational; skills loaded by relevance |
| OpenCode | `processGeneration` `for{}` loop, one `AgentEvent` out | Finish-reason dispatch | None |
| **SAGIHA** | DMARTIC 8-stage cycle; System 1 ReAct / System 2 best-of-N | Gates admit, scores rank; per-step git commit | **Deterministic escalation ladder** that doubles as a label generator for a future learned router |

**Reading.** Everyone runs the same inner cycle — assemble, call, dispatch tools, append, repeat. The
differences are entirely in what wraps it.

Only Grok Build and SAGIHA have an explicit deliberation tier above the ReAct loop. Grok's is a set of
specialized actors with their own prompt templates; SAGIHA's is a dual-process split with parallel
worktree candidates. Grok's is shipping and SAGIHA's is not, but SAGIHA's is the more defensible design
on cost grounds: [ADR-0005](../../08-decisions/0005-best-of-n-not-mcts.md) correctly identifies that
one expansion costs a full agent run plus a test suite, which rules out tree search and makes
best-of-N-plus-sequential-repair the right shape.

The genuinely missing piece is Grok's `goal_stop_detector.rs` and Hermes's `IterationBudget`. SAGIHA's
termination condition is *acceptance criteria met* — which is stronger than either, **but only under
`coding`**. Under `analysis`, `review`, and especially `chat`, [Task & Acceptance](../../03-contracts-and-models/task-and-acceptance.md)
concedes that "a task with no acceptance criteria and no gates terminates on the model's own completion
signal." That is precisely the situation where a stop detector and an iteration budget are load-bearing,
and SAGIHA specifies neither.

### 2.3 Context & Cache Engineering

| | Compaction strategy | Cache discipline |
| :--- | :--- | :--- |
| Claude Code | `autoCompact.ts` summarizes older messages near the limit | Not documented |
| Grok Build | `xai-grok-compaction` crate (policy, prompts, selection, assembly); `PruningConfig` soft-trim / hard-clear; `<memory-context>` canonical tags to defeat dedup bugs | Not documented |
| Hermes | **First-N/last-N protected, middle replaced by a summary from a fast model** | Not documented |
| OpenCode | Fires at **95% of context window**, summary becomes a message in the same session, `SummaryMessageID` truncates subsequent history | Not documented |
| **SAGIHA** | Deliberate checkpoints only; preserves task spec, criteria, plan, open files, unresolved diagnostics; staged re-hydration on compile failure | **Byte-identical prefix rule; layers ordered by decreasing stability; cache hit ratio is an alert metric with a >0.80 target** |

**Reading.** This is SAGIHA's clearest, most defensible lead, and it is worth being precise about why.
All four reference projects treat context as a *space* problem — how do I fit? SAGIHA treats it as a
*cost* problem — what fraction of every call is billed at full price? The consequence is a rule none of
the others state: **order by stability, not by budget share**, because a percentage-based allocator
recomputed per turn churns the prefix and forfeits the cache on every call while saving nothing.

The economics in [LLM Providers & Economics §4](../../05-tech-stack/llm-providers-and-economics.md)
are the justification, and they are correct: over a 30-turn run with a large stable prefix, cache
read-vs-write is the single biggest number in the budget. Grok's compaction crate is more *engineered*
than SAGIHA's spec; SAGIHA's is more *correct* about what it is optimizing.

What SAGIHA lacks is the concrete algorithm. "Compaction preserves X and discards Y at a checkpoint" is
a policy, not a procedure. **Hermes's first-N/last-N protection is a better-specified default than
anything in SAGIHA's docs**, and it composes cleanly with the layered layout: layers 1–7 are already
protected by construction, so first-N/last-N applies to layer 8 alone. Similarly, Grok's `PruningConfig`
soft-trim of oversized tool outputs is a *continuous, cache-cheap* operation on the tail that SAGIHA
currently has no equivalent of — it only has the all-or-nothing compaction checkpoint.

Grok's `<memory-context>` canonical-tag trick deserves a specific callout: identical content injected
from two sources gets silently deduplicated by some assembly paths, and canonical boundary tags prevent
it. SAGIHA already wraps untrusted content in `<untrusted-data>` envelopes for security reasons; the same
mechanism solves this bug for free if every injected block is tagged, not just untrusted ones.

### 2.4 Memory

| | Short-term | Long-term | Retrieval method |
| :--- | :--- | :--- | :--- |
| Claude Code | Message array + auto-compaction | **`memdir/`**: typed taxonomy (`user`/`feedback`/`project`/`reference`), `MEMORY.md` index, memory aging, team sync with secret scanning, **`autoDream` background consolidation**, automatic extraction from sessions | **LLM-driven manifest selection** (small model picks ≤5 files) — no embeddings |
| Grok Build | `xai-chat-state` with per-item token estimates, `edited_paths` | Markdown files in `~/.grok/memory/`; session storage JSONL + FTS | File-based |
| Hermes | Trajectory list + compressor | SQLite-WAL state, **FTS5 over all historical sessions**, `skills/` procedural memory, `learning_graph.py` with visualization | **FTS5 full-text over experience** |
| OpenCode | DB-backed messages (survives restart) | SQLite: sessions, messages, **per-session file version snapshots** | None beyond session scope |
| **SAGIHA** | Ring buffer over SQLite-WAL | **Three tiers**: STM, append-only transaction store, and LTM **split into a deterministic code graph and a bi-temporal episodic graph**; `links` field makes episodic memory a navigable knowledge net; decisions written back to `docs/decisions/` in the target repo | Hybrid: FTS5 lexical + graph expansion; **dense deferred** behind a measured recall@10 trigger |

**Reading.** SAGIHA's split — [ADR-0011](../../08-decisions/0011-split-code-and-episodic-graphs.md),
deterministic code facts separate from contested learned facts — is the single best idea in its memory
design and appears in none of the four. The argument is airtight: passing imports and call edges through
LLM extraction pays tokens for facts Tree-sitter knows with certainty *and* admits hallucinated edges
into a graph that impact analysis then trusts. Equally sharp is the observation that **git is already a
bi-temporal store**, so temporal invalidation is reserved for learned facts only.

Three things the references have that SAGIHA does not:

1. **Claude Code's `autoDream` consolidation and memory aging.** SAGIHA's `MemoryRecord` has `kind`,
   `provenance`, and `links`, and `invalidate()` exists on the port — but nothing ever runs to merge
   duplicates, age out stale records, or prune. A memory store with no consolidation pass grows
   unbounded and its recall precision decays monotonically. Claude Code discovered this and shipped a
   background job with a lock file.
2. **Hermes's FTS5 search across *all past sessions*.** SAGIHA has an append-only `TrajectoryStore` in
   SQLite already; it is used for replay, audit, and training data, but is **not a recall source**.
   Hermes gets "have I seen this failure before?" essentially for free from data SAGIHA is already
   writing. This is the cheapest unclaimed capability in the entire comparison.
3. **OpenCode's per-session file version table.** SAGIHA's rollback story is per-step git commits inside
   the worktree, which is strictly more powerful — but it provides no *diff history UI* and nothing
   survives worktree release. OpenCode's `files` table is what makes "show me exactly what the agent
   changed, step by step" a query rather than a git archaeology exercise.

Claude Code's typed taxonomy deserves note as convergent evolution: SAGIHA's `kind` field and Claude
Code's four-type constraint solve the same problem — an undifferentiated notes file absorbs things
better derived from code and git.

### 2.5 Code Intelligence

| | Mechanism | Depth |
| :--- | :--- | :--- |
| Claude Code | **LSP delegation** — 8 methods exposed as tools (`workspace/symbol`, `definition`, `references`, `hover`, `documentSymbol`, `implementation`, `prepareCallHierarchy`, `didOpen`) | Full symbol-level, zero parsers maintained |
| Grok Build | **`xai-codebase-graph`**: tree-sitter + scope graphs, channel-based `IndexManager`, FSNotify debounce, **>5MB files skipped** | Deepest structural understanding of the four |
| Hermes | `agent/lsp/` — **diagnostics only**, gated on git-workspace detection, before/after delta baseline | Lint-grade feedback, no symbol graph |
| OpenCode | LSP client; diagnostics **auto-injected into `edit`/`write` tool output** as `<file_diagnostics>` | Reactive only |
| **SAGIHA** | **Both**: `LSPAdapter` (diagnostics/definition/references, host-side warm pool with overlays) **and** `CodeGraph` (tree-sitter + git: `impacted_by`, `callers_of`, `co_changed_with`); AST-bounded chunking; skeletonization | Deepest specified — and the only one that treats diagnostics as a *gameable soft score* |

**Reading.** SAGIHA is the only design that takes both routes deliberately, and the reasoning for each
is sound. LSP for diagnostics and symbols (Claude Code's pragmatism), tree-sitter for the deterministic
graph (Grok's depth), with the division drawn on *what each is actually authoritative about*.

The [LSP interface](../../03-contracts-and-models/lsp-interface.md) doc is unusually strong operational
thinking for an unbuilt system: warm pools across tasks, `didOpen`/`didChange` overlays so speculative
edits are checkable before hitting disk, bounded pool size under `ResourceGovernor` to survive N
worktrees × M languages, host-side placement with the trade-off stated plainly. Hermes independently
arrived at the same broken-server-tracking and delta-baseline patterns, which is corroboration.

Two concrete borrows remain:

* **OpenCode and Hermes both auto-attach post-edit diagnostics to the edit tool's own output**, using a
  before/after delta so the model sees only *new* problems it caused. SAGIHA has `get_diagnostics` as a
  separate tool and a `post_edit` hook — which means an extra round-trip and a model that has to
  *remember* to look. Folding the delta into `EditResult` costs one field and removes an entire class of
  "the agent broke the build and didn't notice."
* **Grok's file-size guard and FSNotify debounce.** `>5MB skipped` is three lines of code that prevents
  an OOM class SAGIHA's incremental indexer will otherwise hit on its first minified vendor bundle.
  SAGIHA's [indexing doc](../../05-tech-stack/indexing-and-retrieval.md) specifies file-watch-driven
  per-file re-index and says nothing about either guard.

Claude Code's `prepareCallHierarchy` is worth noting as a fallback: SAGIHA's `CodeGraph.callers_of()`
covers the same question, but only for languages with a tree-sitter grammar and a graph adapter. LSP
call hierarchy answers it for every language with a server, at zero marginal maintenance.

### 2.6 File Editing

| | Strategy | Failure handling |
| :--- | :--- | :--- |
| Claude Code | Literal `old_string` → `new_string`, must match exactly once | Error on 0 or >1 matches; git for rollback; **listed as its own #1 weakness** |
| Grok Build | **Five pluggable strategies** (`codex`, `opencode`, `grok_build`, `_concise`, `_hashline`) + `xai-hunk-tracker` for undo/redo and conflict detection | Strategy is swappable and A/B-testable |
| Hermes | Diff and replacement tools; PTY-backed terminal for interactive editors | Guardrail decision per mutation |
| OpenCode | `edit` / `patch` (unified diff) / `write`; `go-udiff` + file version table | **Rollback from DB snapshots**; visual diff in TUI |
| **SAGIHA** | `edit_file(EditRequest)` — search/replace anchors with `expected_occurrences`; `write_file` reserved for new files/rewrites | `EditResult` with per-hunk `HunkResult` + **tree-sitter `syntax_valid` check before the LSP sees it**; per-step git commit |

**Reading.** SAGIHA has correctly diagnosed Claude Code's biggest production weakness and designed
around it: `expected_occurrences` kills the ambiguous-match failure, per-hunk results tell the model
*which* hunk failed rather than returning a bare `false`, and the tree-sitter syntax check rejects a
structurally broken edit before it propagates. The metric that would prove it — **Edit Hunk Failure
Ratio** — is already named in
[Metrics & Analytics §3C](../../06-guides-and-patterns/metrics-analytics-and-self-improvement.md).

What is missing is Grok's insight that **there is no known-best edit format, so make it swappable and
measure**. xAI ships five implementations, which is only rational if none dominates. SAGIHA has one
format, an `EditRequest` abstraction that could hide several, a metric that would rank them, and no
stated intent to exploit the combination. That is a free experiment left on the table — and, notably,
one of Grok's five strategies is literally named `opencode`, meaning xAI found a competitor's format
worth keeping as an option.

### 2.7 Tool Systems

| | Registry | Budget discipline | Extension |
| :--- | :--- | :--- | :--- |
| Claude Code | `buildTool()` + zod schemas, ~40 tool directories | **None** — feature flags gate availability; `ToolSearchTool` fetches deferred schemas on demand | MCP client + server; skills |
| Grok Build | `ToolBridge` / `ToolDefinition`; **local vs hosted split**; Computer Hub (transport-agnostic contract, JSON-RPC wire, MCP bridge) | Not stated | MCP; plugin marketplace; hooks |
| Hermes | `toolsets.py` + `handle_function_call()`; **toolset distributions per deployment context** | Filtered per context | MCP client + server; plugins; skills |
| OpenCode | `BaseTool{Info(), Run()}` — 12 tools | Small by construction | MCP client (stdio + sse) |
| **SAGIHA** | `ToolRegistry` with `EffectClass` + `grant_scope` + `trusted_output` per tool; open namespace | **Hard cap: 20 core tools**, with a stated ≤5%-of-tasks rule for demotion to MCP | Four surfaces (adapter/tool/skill/hook) via entry points, resolved once then frozen |

**Reading.** Claude Code's ~40 tools and its `ToolSearchTool` are the same finding stated twice: the
catalog outgrew the prompt, so a tool had to be invented to look up other tools. SAGIHA's 20-tool cap
with an explicit demotion rule is the correct response, and the reasoning — selection accuracy degrades
with list length, and every schema is prompt real estate paid on every call until the cache warms — is
right.

Two design choices in the [tool catalog](../../03-contracts-and-models/tool-catalog.md) are better than
anything in the four references:

* **`run_command(argv: str[])`, never a shell string.** This removes an entire class of quoting bugs and
  makes the audit log unambiguous. `bash -lc` remains available explicitly, and *that form is what policy
  inspects.* Every reference project passes shell strings.
* **`run_tests` separated from `run_command`.** Routing the gate signal through generic execution would
  let a candidate's own harness modifications shape the result. None of the four separate them, because
  none of the four have a gate that could be captured.

Grok's local-vs-hosted tool split and its Computer Hub are worth flagging as validation rather than gap:
SAGIHA's contract rule that **every port must be implementable over a wire** (no `Path`, no file handle,
no live object crossing a boundary) is the same design pressure, applied earlier and more uniformly.

Hermes's toolset distributions — a Discord bot gets different tools than a local dev agent — map almost
exactly onto SAGIHA's execution profiles, arrived at independently. Corroboration for
[ADR-0017](../../08-decisions/0017-execution-profiles.md).

### 2.8 Security & Permissions

| | Model | Enforcement point |
| :--- | :--- | :--- |
| Claude Code | Permission modes (`plan`/`auto`/custom) + **YOLO classifier** (heuristic/LLM detection of dangerous commands) + per-tool `checkPermissions()` | Tool-level check, user prompt |
| Grok Build | `PermissionMode` × `ClientType`, `folder_trust.rs` per-directory trust, `xai-grok-sandbox` | Sandbox + trust level |
| Hermes | **Two orthogonal layers**: `tools/approval.py` (regex command analysis, human-in-the-loop) and `agent/tool_guardrails.py` (`ToolCallSignature`, idempotent-vs-mutating loop caps, failure classification) | Pre-execution + per-turn pattern |
| OpenCode | Allow / allow-for-session / deny, blocking modal | Permission service |
| **SAGIHA** | **Unforgeable `Grant` tokens minted only by `PolicyEngine.authorize()`**, scoped and expiring; single dispatch choke point; grants never leave `kernel/dispatch.py`; rootless Podman perimeter; egress allowlisted at an explicit proxy; provenance tracking against memory-laundering; TCB write boundary | **Reachability + type system + CI import contracts** |

**Reading.** This is the widest gap in the comparison, and it is not close.

All four reference projects implement **permission systems** — mechanisms that decide whether to ask the
user. SAGIHA specifies a **capability system** — a mechanism where the effect is structurally impossible
without a token that only one component can mint. The difference shows up in exactly one place: what
happens when the model, a hook, an MCP server, or a future contributor tries to route around the check.
In a permission system the check is a function call someone can forget to make. In SAGIHA's design,
authorization is enforced *by reachability* — the Runtime method has no path to execution without a
`Grant`, the `Grant` never escapes the choke point, and `import-linter` fails the build if `agency/`
imports `runtime/`.

[ADR-0006](../../08-decisions/0006-sandbox-is-the-perimeter.md) states the thing that most harnesses get
wrong: **command-string blocklisting is a usability guardrail, not a security control.** Claude Code's
YOLO classifier and Hermes's regex analysis are both, by SAGIHA's framing, guardrails wearing security
clothing — they fail to `bash -c`, base64 payloads, `$IFS` substitution, and any interpreter in the
image. Both projects would likely agree; neither says so in its own docs.

Three SAGIHA security properties have no counterpart anywhere in the four:

1. **Provenance survives the memory round-trip.** The laundering path — read untrusted web content,
   store it as a memory, recall it later stripped of its tag — is closed by per-record `Provenance` and a
   conformance test (`test_external_provenance_survives_roundtrip`). *Trust travels the links*: a
   traversal reaching an `EXTERNAL` record returns an `EXTERNAL` record. No reference project models
   provenance at all.
2. **`EffectClass` makes replay non-destructive.** T5 — replaying a trajectory containing `git push`
   would perform it again — is a threat none of the four can even have, because none of the four can
   replay.
3. **The TCB is excluded from the agent's writable surface**, enforced three ways (path allowlist,
   unpushable branch, CI diff rejection). Only a self-improving system needs this, and only SAGIHA is
   one.

The one thing to import: **Hermes's loop-level guardrails are genuinely orthogonal to everything SAGIHA
has.** `ToolCallGuardrailController` builds a `ToolCallSignature` from canonicalized arguments plus a
result hash to detect the agent repeating an identical call, classifies idempotent versus mutating tools,
and applies loop caps to the latter. SAGIHA has `EffectClass` (which answers a *replay* question),
`ResourceGovernor` (which answers a *budget* question), and nothing that answers **"is this agent
stuck?"** The signatures Hermes hashes are already visible at SAGIHA's dispatch choke point, so this is a
natural, cheap addition at exactly the right architectural location.

### 2.9 Evaluation

| | Evaluation capability |
| :--- | :--- |
| Claude Code | **None shipped** — tests stripped from the distributed source |
| Grok Build | Hermetic test infrastructure (`xai-grok-test-support`), 40+ session-actor test files — *engineering* tests, not *agent-quality* evaluation |
| Hermes | `batch_runner.py` — trajectory completion evaluation across task sets. Closest of the four |
| OpenCode | 4 `_test.go` files out of 140 |
| **SAGIHA** | **E0 ships before S0**: commit-replay harvester, task runner, **A/A noise floor**, paired statistics with multiple-comparison correction, reporting. Pristine injected test suite; `tests_unmodified` as a **hard gate**; hard gates strictly separated from soft scores; `Reviewer` explicitly a ranker and never an admitter |

**Reading.** This is SAGIHA's actual thesis, and no reference project competes on it. Three specific
ideas stand out:

**The A/A noise floor.** Run the *unmodified* harness twice, measure the score-delta distribution under
pure stochasticity, and reject any candidate that fails to beat it. The observation behind it is the
sharpest in the entire documentation tree: most harness mutations produce effects smaller than run-to-run
variance, so "accept if the score improved" **ratchets permanently on noise** — accumulating changes that
are individually meaningless and collectively a random walk. Without an A/A measurement there is no way
to tell the difference, which means most harness tuning work in this space is an undiagnosed random walk.

**Evaluation capture as a first-class threat (T3).** A candidate branch has filesystem access to its own
`tests/`. Any score computed from tests the candidate could have modified is a number the candidate
controls. The mitigation — inject tests pristine and read-only from the base commit, treat modification
as a hard gate failure rather than a scored penalty — is obvious once stated and absent from all four.

**Gates admit; scores rank.** Every soft signal is a gameable proxy: delete the failing code, add a
suppression, widen a type, swallow an exception. SAGIHA lets proxies order candidates and forbids them
from admitting any. `no_new_suppressions` exists specifically to close the cheapest exploit. The
`Reviewer` port is deliberately not a gate, "because a gate that can be talked out of a denial is not a
gate" — and the judge must be a frontier model that is *never the model that generated the candidate*.

Sequencing E0 before S0 is the right call for a reason worth restating: the chicken-and-egg problem (S0
needs a benchmark, the benchmark needs harvesting, harvesting needs a harness) dissolves when the
harvester *is* the first deliverable. It is also the only piece of this project that is independently
useful in weeks rather than months.

### 2.10 Extensibility

| | Mechanism | Static analyzability |
| :--- | :--- | :--- |
| Claude Code | MCP client + server, skills, `CLAUDE.md`, feature flags | Partial |
| Grok Build | **`ExtensionRegistry` with zero-ownership lifecycle hooks** (`TurnStart`/`TurnDone`/`TurnAbort`) — extensions observe, cannot hijack dispatch; file-based hook discovery; plugin marketplace | Good |
| Hermes | Plugins, skills, optional-skills, optional-mcps; **no global module auto-discovery** | Moderate |
| OpenCode | `.opencode.json` + **generated JSON Schema for IDE autocomplete** | Good |
| **SAGIHA** | Four surfaces — adapter, tool, skill, hook — via **entry points resolved once at composition, then frozen**; conformance suite is the adapter admission gate; recorded in the run manifest | **Full** — every extension is a real import pyright resolves |

**Reading.** Grok's zero-ownership hook principle and SAGIHA's Observer/Interceptor split are the same
insight independently derived: **extensions may watch, and may deny, but may never mutate or hijack.**
SAGIHA goes one step further by making interceptor timeout equal *deny* — failing closed.

SAGIHA's resolve-once-then-freeze lifecycle is the sharpest resolution of a real tension in the tree.
[ADR-0004](../../08-decisions/0004-no-di-container.md) rejects plugin discovery because dynamic wiring
defeats the static analysis an LLM maintainer depends on; but if the only sanctioned wiring is "edit
`build_kernel()`," every extender becomes a maintainer of this repository.
[ADR-0013](../../08-decisions/0013-extension-registration.md) takes the third option and preserves
navigability in full: go-to-definition works, the resolved set is printable, and the run manifest makes
an extension-bearing trajectory reproducible.

Two borrows: **OpenCode generates its config JSON Schema from the config struct by reflection** — SAGIHA's
config is Pydantic, which emits JSON Schema natively, so IDE autocomplete over `config.toml` is nearly
free and currently unclaimed. And **skills are SAGIHA's weakest extension surface relative to the
references** — see §3.3.

### 2.11 Entry Points & Deployment

| | Channels |
| :--- | :--- |
| Claude Code | Terminal (Ink), `--print` headless, daemon, MCP server, **remote bridge with JWT + trusted-device pairing**, push-to-talk voice |
| Grok Build | Ratatui TUI over ACP, `ptyctl` multiplexing, MCP, streaming STT |
| Hermes | **CLI/TUI, 9+ messaging platforms, ACP server, web, desktop app, MCP server, batch runner** — broadest of any project reviewed |
| OpenCode | TUI; `-p` one-shot headless. **No server mode** |
| **SAGIHA** | One headless signature `execute(task, context) -> AsyncIterator[Event]`; CLI/TUI, headless CI, MCP server, A2A (deferred), remote bot **as a separate out-of-repo service** |

**Reading.** SAGIHA's claim — *adding a channel requires zero core changes; if a proposed channel would
require one, the headless boundary is wrong* — is validated by Hermes, which achieved 9+ platforms
against a core that was never designed for it and paid with an 816KB `cli.py`.

Keeping `sagiha-bot` out of the repository is the right call and worth defending explicitly: messaging
platform APIs churn far faster than an architecture should, and a disposable pilot layer can be abandoned
without touching the engine. Hermes's `gateway/platforms/` is the counterfactual — genuinely impressive
reach, permanently coupled to nine vendors' API churn.

Three properties SAGIHA specifies that the references mostly lack: **resumable streaming**
(`?since=<step_id>`, because long autonomous runs outlive mobile connections), **redaction at the
boundary** (once, in the streamer, not per client), and **durable approval state** (the run parks in
`input-required` independent of whether any cockpit is attached). Claude Code's remote bridge routes
permission prompts to a device; SAGIHA's design survives no device being there at all — which is what
[the security model](../../02-architecture/security-and-threat-model.md) means by "nobody watches a
six-hour run, so a gate requiring someone present is a gate that will be disabled."

The gap is **ACP**. Both Grok Build and Hermes speak the Agent Client Protocol; Hermes exposes itself as
an ACP server so any ACP-capable editor (Zed and others) drives it with no bespoke extension. SAGIHA
plans MCP-server mode for the same purpose, which is reasonable — but ACP is the protocol purpose-built
for the *agent↔editor* relationship, and two of four reference projects have already adopted it.

### 2.12 Resilience & Production Engineering

This dimension has no SAGIHA column, which is the finding.

| Project | Production hardening |
| :--- | :--- |
| Grok Build | `xai-sqlite-journal` — classifies the filesystem (NFS, smbfs, cifs, afpfs, webdav, FUSE, wekafs) and degrades WAL→Truncate, per-host DB files, to prevent `SIGBUS` from incoherent mmap'd `-shm` on network mounts. `xai-circuit-breaker` (sliding window), `xai-crash-handler` (SIGBUS/SIGSEGV), `xai-system-power` (sleep/wake), `xai-interjection-core` + `xai-prompt-queue` (mid-turn interjection with merge rules), `xai-grok-secrets` (redaction), `xai-token-estimation` (one shared estimator) |
| Hermes | SQLite WAL for multi-process sub-agents; PID-regex lease tracking for clean sub-process termination; surrogate scrubbing and unicode sanitation on all model inputs |
| Claude Code | Lock files for concurrent task-board access; `TeamDeleteTool` refuses to clean up while a member is active |
| OpenCode | goose migrations; `sqlc` compile-time query safety |
| **SAGIHA** | SQLite-WAL specified as a connection-factory invariant with `busy_timeout` and one-writer-per-database; circuit breaker referenced in the error taxonomy. **Nothing on network filesystems, process crashes, host sleep/wake, or mid-turn interjection queueing.** |

**Reading.** Grok's NFS detection is the most quietly impressive engineering in the four projects, and it
lands directly on SAGIHA: the entire persistence design is SQLite-WAL, and WAL keeps its wal-index in an
mmap'd `-shm` file that network filesystems cannot back coherently. **A developer with an NFS-mounted
home directory gets a `SIGBUS` panic, not an error message.** This is a ~100-line adapter concern that
SAGIHA's docs do not mention and its architecture will absolutely hit.

Host sleep/wake and crash handling matter disproportionately here for a specific reason: SAGIHA's
differentiator is *long autonomous runs*. A six-hour run is exactly the workload that encounters a closed
laptop lid, a killed process, and an OOM. Grok invested in three separate crates for this; SAGIHA's
resumability story is currently "TaskSpec is persisted" plus a foundation review finding that says
**D9 — run state is unresumable** in the code that exists.

### 2.13 Macro-Workflow Orchestration

This dimension was missing from an earlier draft of this document, and the reason it was missing is
itself the finding: **no project reviewed here has this layer, so a comparative method could not
surface it as a gap.** It took an internal design review to name it.

Every dimension above concerns the **inner** loop — `TaskSpec` in, `GateReport` out. This one concerns
what happens *above* it: turning a paragraph of human intent into an ordered set of verifiable tasks.

| | Decomposition mechanism | Is the plan a first-class artifact? |
| :--- | :--- | :--- |
| Claude Code | `TodoWrite` tool — the model maintains a checklist inside the conversation | No. Plan lives in context; lost on compaction |
| Grok Build | **Eight-actor goal system** — orchestrator, planner, tracker, strategist, classifier, evaluator, stop-detector, summarizer | Partially. Tracked in actor state, but the actors are hard-wired Rust types, not a composable contract |
| Hermes | Conversational; skills loaded by relevance | No |
| OpenCode | None — single-turn intent to edits | No |
| **SAGIHA** | `parent_task_id` decomposition with disjoint file-set closures — **the schema exists, the producer does not** | Not yet. Nothing generates the decomposition |

**Reading.** Grok Build is the only reference project that treats planning as machinery rather than as
a prompt, and it is not a coincidence that Grok is also the most production-hardened of the four. But
its goal system is eight concrete actors wired at compile time: you cannot swap the planner, you
cannot A/B two decomposition strategies, and you certainly cannot *measure* whether the planner
helped. Everyone else delegates decomposition to the model inside a single conversation, which is why
none of the four can gate, replay, or measure a **plan** as an artifact. The methodology kits circling
this space (SpecKit, BMAD, GSD) are prompt collections, not execution contracts — they make a human's
process legible without making an agent's process measurable.

SAGIHA's position is unusual and worth stating precisely: **it has the output schema and not the
producer.** [Task & Acceptance](../../03-contracts-and-models/task-and-acceptance.md) already
specifies `parent_task_id` decomposition with disjoint file-set closures — which is the hard half,
because file-set disjointness is what makes parallel story execution safe. What is absent is anything
that produces those values. A human writes every `TaskSpec` today.

Where this becomes a genuine SOTA opportunity rather than a missing feature: SAGIHA is the only design
here where a planning stage *could* be measured. Because `TrajectoryStore` persists every step and E0
provides an A/A noise floor, a decomposition strategy is a hypothesis that can be tested against
running the inner loop directly on the raw prompt. **Planning quality becomes a number instead of a
matter of taste** — and that, not the pipeline itself, is the differentiator. It also makes the macro
layer the first legitimate RHI target: the outer loop can propose a different decomposition and the
benchmark can adjudicate.

The corresponding risk is equally specific. A pipeline of LLM planning stages multiplies cost per task
and adds a failure mode above the loop — a bad `StoryBoard` wastes every downstream step, and unlike
a bad edit, nothing tests it. This is why the layer is specified with an unusual condition attached:
no stage enters the tree without an E0 gate showing it beats no-planning, and if planning does not
beat no-planning, the layer does not ship. Contract and rationale:
[ADR-0018](../../08-decisions/0018-native-workflow-dag.md). Sequencing is not negotiable — this is a
non-goal until Sprint 3's exit test is green, because a planner above a loop that cannot dispatch a
tool (D1) repeats the exact sequencing error the foundation review diagnosed.

**Take from Grok:** that planning deserves dedicated machinery. **Reject from Grok:** hard-wiring it,
which is what makes it unmeasurable and unswappable.

---

## **3. Head-to-Head: SAGIHA vs. Each Project**

### 3.1 vs. Claude Code

**Where Claude Code wins:** it exists, it is used daily at scale, and its memory subsystem is more
complete than SAGIHA's specification (typed taxonomy, aging, background consolidation, automatic
extraction from sessions, secret-scanned team sync). Its tiered multi-agent primitives — a lightweight
`AgentTool` spawn versus a heavyweight persistent `TeamCreateTool` swarm with its own restricted
coordinator allowlist and a lock-protected shared task board — are more nuanced than SAGIHA's single
`spawn_subagent`. Its LSP surface is wider (8 methods vs. 3 plus a graph). `SendMessageTool` — steering a
running teammate mid-task — has no SAGIHA equivalent.

**Where SAGIHA wins:** edits (per-hunk results, `expected_occurrences`, tree-sitter validation vs. a
literal replacement Anthropic itself lists as weakness #1); the decomposed kernel versus a ~1,700-line
`QueryEngine`; capability grants versus a permission classifier; replay determinism; and evaluation,
where Claude Code ships nothing and SAGIHA leads with E0.

**Take:** the memory subsystem and the tiered delegation model.

### 3.2 vs. Grok Build

**Where Grok wins:** almost everything at the engineering layer. Scope graphs, channel-based indexing
that never blocks the agent loop, five pluggable edit strategies, an eight-component goal system with its
own prompt templates, the NFS journal-mode fix, circuit breaker, crash handler, sleep/wake handling, and
mid-turn interjection queueing. It is the most *production-hardened* of the four by a wide margin.

**Where SAGIHA wins:** evaluation (Grok has hermetic engineering tests, no agent-quality measurement, no
noise floor); security model (sandbox and folder trust, but no capability tokens, no provenance, no TCB);
replay determinism; cache economics; and self-improvement, which Grok does not attempt.

**Where Grok is a warning:** ~75 crates produces painful navigation, actor spaghetti, and long compile
times — all self-reported. SAGIHA's specification density is on the same trajectory in a language with
weaker boundary enforcement.

**Take:** the NFS journal-mode probe, file-size and debounce guards, pluggable edit strategies, mid-turn
interjection queueing, and the resilience crates' concerns.

### 3.3 vs. Hermes Agent

**Where Hermes wins:** deployment reach (9+ platforms, ACP, desktop, batch); `batch_runner.py` as the
only real agent-quality evaluation among the four; trajectory compression with first-N/last-N protection;
FTS5 search across all past sessions; layered orthogonal guardrails; and — most importantly — **procedural
skill generation**: successful task patterns are captured as reusable skills, loaded into future
sessions, and visualized as a learning graph. That is inference-time learning without fine-tuning, and it
is the one capability in the four references that SAGIHA has no answer to.

The distinction matters. SAGIHA's skills are **authored artifacts** — versioned bundles a human or a
third party writes and installs. Hermes's skills are **earned artifacts** — the agent writes them from
its own successful trajectories. SAGIHA's self-improvement story runs entirely through the RHI outer
loop, which mutates prompts and parameters at a cost of "thousands of dollars per iteration" and runs on
a deliberate schedule. Skill extraction is a per-task learning loop costing one cheap model call, and
SAGIHA has the trajectory data to do it already.

**Where SAGIHA wins:** structure (no 816KB files, mechanically enforced); code graph (Hermes's LSP is
diagnostics-only, no symbol resolution at all); capability grants; replay; gates and the evaluation-capture
defense; and cache discipline.

**Where Hermes is a warning:** it is the closest analogue — same language, same ambition, similar breadth
— and its listed weaknesses are almost exactly the failure modes SAGIHA's structure exists to prevent.
Its recovery path is also instructive: pull the loop body, tool execution, guardrails, and compression out
of the God class one at a time, leaving thin forwarders. Worth knowing before SAGIHA needs it.

**Take:** skill extraction from successful trajectories (bounded by the TCB rules), first-N/last-N
compaction, FTS5 over trajectories, loop guardrails, iteration budgets, and ACP.

### 3.4 vs. OpenCode

**Where OpenCode wins:** it is the cleanest codebase of the four at 140 files, which is a real argument
about proportion. Its pub/sub broker, `sqlc` compile-time query safety, generated config JSON Schema,
per-session file version snapshots with rollback and visual diff, and automatic post-edit diagnostics
injection are all high-value-per-line.

**Where SAGIHA wins:** essentially every axis of ambition — code graph, candidate search, capability
security, evaluation, self-improvement, multi-channel piloting. OpenCode is also archived.

**Where OpenCode is a caution:** it achieved a genuinely good agent in 140 files. SAGIHA's documentation
tree alone is larger than OpenCode's entire implementation. That is not automatically wrong — SAGIHA
targets autonomous long-horizon work with statistical self-improvement, which is a different problem —
but the ratio should stay uncomfortable rather than becoming invisible.

**Take:** file version snapshots for diff history, config schema generation, auto-injected post-edit
diagnostics, and the discipline of proportion.

---

## **4. Strengths and Weaknesses, Summarized**

| Approach | Core strength | Core weakness |
| :--- | :--- | :--- |
| **Claude Code** | Pragmatic delegation — LSP for intelligence, git worktrees for isolation, filesystem for coordination. Richest shipped memory system. | Brittle edit primitive; monolithic loop; no evaluation; no capability model |
| **Grok Build** | Deepest engineering: scope graphs, non-blocking indexing, production resilience nobody else bothered with | Complexity sprawl; vendor coupling; no agent-quality measurement |
| **Hermes** | Broadest reach and the only genuine inference-time learning loop | Two remaining monoliths; diagnostics without a code graph; discoverability |
| **OpenCode** | Maximum clarity per line; clean event-driven boundaries | Limited ambition; archived; reactive-only intelligence |
| **SAGIHA** | Verification-first: capability security, replay determinism, gates-vs-scores, and a measured noise floor before any self-improvement claim — plus the only design here where *planning quality* could become a measured number | **Unbuilt.** Specification density far exceeds implementation; skeleton has 18 known defects; weakest exactly where the references are strongest (production resilience, shipped ergonomics, earned learning) — and has no producer for the decomposition schema it already specifies |

---

## **5. What SAGIHA Already Has Right — Do Not Trade These Away**

Ranked by how much would be lost if dropped:

1. **E0 before S0.** Evaluation infrastructure first is the decision that makes every later claim a
   number. It is also the only deliverable that is independently useful within weeks.
2. **A/A noise floor before any self-improvement.** Without it, the outer loop ratchets on randomness.
   No reference project has this, and it is the most likely reason harness-tuning efforts elsewhere
   fail invisibly.
3. **Gates admit, scores rank — and `tests_unmodified` is a gate.** T3, evaluation capture, is real and
   universally unaddressed.
4. **Capability grants at a single dispatch choke point**, with `import-linter` enforcing the layer
   boundary. This is the one security property that survives a contributor in a hurry.
5. **Record/replay determinism with `EffectClass`.** Makes the kernel testable at Day 0 with zero API
   cost, and makes replay non-destructive.
6. **Cache-stability-ordered prompt layering.** The largest cost lever in the system, correctly
   identified and correctly constrained.
7. **Split code graph vs. episodic graph**, with git recognized as the existing bi-temporal store.
8. **`run_command(argv)` and `run_tests` separated from it.**
9. **20-tool cap with an explicit demotion rule.**
10. **Ports implementable over a wire**, so a sidecar is an adapter swap rather than a refactor.
11. **Execution profiles composing ports rather than branching the kernel** — with the sharp corollary
    that absence of a verdict and a verdict of "pass" must never be the same value.
12. **Extensions resolved once, then frozen**, recorded in the run manifest.
13. **Cost-per-success as the operative metric**, with a missing price entry as a hard startup error.

---

## **6. Concrete Improvements to Consider**

Each item names the source, the change, and where it lands. Nothing here is normative until it reaches
`03-contracts-and-models/` or an ADR.

### Tier A — cheap now, expensive later (fold into S0/S1)

| # | Change | Source | Rationale |
| :--- | :--- | :--- | :--- |
| A1 | **Fold a post-edit diagnostics delta into `EditResult`** — snapshot before write, return only *new* diagnostics after | OpenCode, Hermes | Removes a round-trip and the "broke the build, didn't notice" failure class. One field. |
| A2 | **Probe the filesystem and select the SQLite journal mode** (WAL → Truncate on NFS/CIFS/FUSE/etc., per-host DB file) | Grok | SAGIHA is SQLite-WAL end to end; on a network-mounted home directory the failure is a `SIGBUS` panic, not an error |
| A3 | **Loop guardrails: canonical tool-call signature + result hash, idempotent-vs-mutating loop caps** at the dispatch choke point | Hermes | Orthogonal to `EffectClass` (replay) and `ResourceGovernor` (budget). Nothing currently answers "is the agent stuck?" |
| A4 | **Iteration budget and a stop detector**, mandatory under `gates = "none"` profiles | Hermes, Grok | Ungated profiles terminate on the model's own completion signal; that needs a backstop |
| A5 | **Indexer guards**: skip files above a size ceiling, debounce file-watch events, never block the agent loop | Grok | Three lines that prevent an OOM class and an indexing stampede |
| A6 | **Specify the compaction algorithm**: protect first-N and last-N of layer 8, summarize the middle with the `fast` role | Hermes | The layered layout already protects layers 1–7; this makes layer 8 concrete rather than policy-shaped |
| A7 | **Tag every injected context block canonically**, not only untrusted ones | Grok | Prevents silent dedup of identical content from different sources |
| A8 | **Generate the config JSON Schema from the Pydantic config model** | OpenCode | Pydantic emits it natively; IDE autocomplete over `config.toml` for near-zero cost |
| A9 | **`dispatch` must verify the grant, not just its id** — call `get_grant(grant_id)`, fail closed on missing/expired | §7.3 audit | Expiry logic already exists in `DefaultPolicyEngine` and is never invoked. Authorization is currently ceremony |
| A10 | **Schema-declared path scoping** — tools declare which schema fields are paths at registration; `authorize()` reads the declaration and enforces containment under `workspace_root` | §7.3 audit | Key-name guessing cannot reach `EditRequest.path`, so the primary mutation tool gets an empty scope. Nested-path tools make the current approach unfixable by extending the key list |
| ~~A11~~ | ~~Generate the event catalog from `events.py` in CI~~ — **already implemented**; withdrawn | §7.5 audit | `scripts/gen_event_catalog.py --check` is wired into `ci.yml:43`. Apply the same generation pattern to the **port stability table** instead (§8.2) |
| A12 | **`WorktreeManager.allocate() -> WorkspaceRef`**, not `-> Workspace`; write `test_port_shape.py` | §7.6 audit | The one live violation of the remoteable-ports rule, on precisely the port a container or remote runtime would replace |
| A13 | **Put real code in `agency/` and `runtime/`** — prompt assembly into `agency/`, tool execution into `runtime/` — then flip `unmatched_ignore_imports_alerting` from `warn` back to `error` in `.importlinter` | §7.7 audit, U1 | The `car-layering` contract is currently self-documented as inert: its own comment says the ignore rule "legitimately matches nothing yet." Sprint 3 B2 and B4 already write this code; the new work is choosing the right package and flipping one setting |

### Tier B — real capability, land with S2/S3

| # | Change | Source | Rationale |
| :--- | :--- | :--- | :--- |
| B1 | **Make `TrajectoryStore` a recall source** — FTS5 over past runs, surfaced through `Memory.recall` or a sibling query | Hermes | The data is already being written for replay and audit; "have I hit this failure before?" is currently unanswerable |
| B2 | **Memory consolidation and aging pass** — scheduled merge/prune/stale-marking, preserving `Provenance` and `links` | Claude Code (`autoDream`) | Without it, precision decays monotonically and the store grows unbounded |
| B3 | **Pluggable edit strategies behind `Workspace.apply_edit`**, ranked by the Edit Hunk Failure Ratio metric that already exists | Grok | xAI ships five because none dominates. SAGIHA has the abstraction and the metric and is not exploiting the pair |
| B4 | **Mid-turn interjection queue with explicit merge rules** | Grok | SAGIHA has `UserMessageReceived`/`TaskRevised` events but no semantics for messages arriving during a turn — and steering is called the dominant interaction mode |
| B5 | **Land `neighbors()` / `backlinks()` on the `Memory` port** | SAGIHA's own S2 flag | The knowledge-net design requires them; honest invalidation is impossible without backlinks |
| B6 | **Crash, sleep/wake, and resumption handling**; close foundation-review D9 | Grok, Hermes | Long autonomous runs are the differentiator, and they are exactly the workload that meets closed laptops and OOM kills |
| B7 | **LSP call hierarchy as a fallback** where no `CodeGraph` adapter exists for a language | Claude Code | Extends `callers_of` coverage to every language with a server, at no maintenance cost |
| B8 | **Native macro-workflow layer** — `WorkflowStep[In, Out]` + `PipelineRunner` in `agency/`, `PRDSpec` → `StoryBoard` → `TaskSpec`, four stages, each boundary an event | Grok's goal system, §2.13 | The one capability gap no reference project exposes. Grok proves planning deserves machinery; SAGIHA already has the output schema (`parent_task_id` + disjoint file sets) and no producer. **Gated:** ships only if E0 shows it beats no-planning — [ADR-0018](../../08-decisions/0018-native-workflow-dag.md) |

### Tier C — strategic, needs a decision

| # | Change | Source | Open question |
| :--- | :--- | :--- | :--- |
| C1 | **Skill extraction from successful trajectories** — the agent proposes a skill after a gated success; it lands as a `MutationProposal` under TCB rules and human sign-off | Hermes | The highest-value borrow in this document, and the one most in tension with SAGIHA's caution. Bounded correctly, it costs one cheap model call per success and gives per-task learning between expensive RHI iterations. Bounded wrongly, it is an unaudited self-modification channel. **Recommend: prototype it in shadow mode, gate the write.** |
| C2 | **Tiered delegation** — keep `spawn_subagent` for one-shot work; add a lock-protected task board and mid-flight steering for persistent multi-agent work | Claude Code | Do not build until single-agent plateaus (already the roadmap trigger). But the SQLite-WAL store makes the task board nearly free when the time comes |
| C3 | **ACP adapter alongside MCP-server mode** | Grok, Hermes | Two of four reference projects adopted the protocol purpose-built for agent↔editor. Cheap editor integration; cost is one more protocol surface |
| C4 | **File version snapshots for diff history** | OpenCode | Per-step git commits are strictly more powerful but do not survive worktree release and make "show me each change" archaeology. Possibly satisfiable by exporting commits at release rather than a second store |
| C5 | **A complexity budget for the specification itself** | Grok's self-reported weakness | Consider an ADR: no new mechanism enters the tree without a slice that uses it and a gate that measures it |

### Explicitly reject

| Pattern | Source | Why |
| :--- | :--- | :--- |
| Literal-only string replacement for edits | Claude Code | Anthropic's own weakness #1; SAGIHA's anchored design is already better |
| Monolithic query loop / God class | Claude Code, Hermes | The failure the CAR layering and import contracts exist to prevent |
| 63–75 module fragmentation | Grok | Grok's own weakness #1 — but keep §6 C5 in view, the risk here is the *docs*, not the crates |
| Messaging-platform gateways in-repo | Hermes | Nine vendors' API churn welded to the engine; `sagiha-bot` stays out-of-repo |
| Forked upstream dependencies | Grok | Adapter pattern instead — [ADR-0008](../../08-decisions/0008-native-sdks-no-litellm.md) already covers this |
| Command-string blocklisting as security | Claude Code, Hermes | Bypassed by `bash -c`, base64, `$IFS`, any interpreter in the image. Guardrail only — [ADR-0006](../../08-decisions/0006-sandbox-is-the-perimeter.md) |
| Embedding-first retrieval | (industry default) | [ADR-0014](../../08-decisions/0014-defer-dense-retrieval.md) is right: bad chunking is the likelier cause of poor recall, and embeddings on bad chunks buy a dependency and no recall |
| Shipping without tests | Claude Code, OpenCode | Conformance suites are the admission gate for adapters; that only works if they ship |
| Third-party orchestration frameworks (LangGraph, LangChain, Prefect, Temporal) | (industry default) | A framework that calls our steps rather than being called by them moves the dispatch choke point outside `kernel/` — outside the TCB. LangChain assembling its own message list forfeits the prefix rule; a wrapped provider client escapes the cassette. [ADR-0018](../../08-decisions/0018-native-workflow-dag.md) |
| Deleting `agency/` / `runtime/` to reduce folder count | (internal proposal) | They are the **A** and **R** of CAR. Deleting them voids the layer contracts that are this project's strongest implemented property. The emptiness is real — the fix is code, not amputation (A13, §7.7) |

---

## **7. Overengineering Audit — Claim Verification**

An internal audit proposed five overengineering findings and a universality assessment. Each claim was
checked against `src/sagiha/` and the normative docs at the commit this document describes. A later
design review added two more claims (7 and 8). Verdicts below; **the findings that survive
verification are folded into §6 as A9–A13 and B8.** The decisions they produced, including the answers
to the tech-lead questions, are recorded in the
[Sprint 0 Decision Record](./proj_plan_design_and_docs_improvs.md).

| # | Claim | Verdict | Notes |
| :--- | :--- | :--- | :--- |
| 1 | "21 typed ports, 74 docs, before a working tool-call loop" | **Substantially correct** | 22 `Protocol` classes in `src/sagiha/ports/`; 82 `.md` under `docs/` (69 excluding `reference/` + `reviews/`). The *examples* are wrong — see below |
| 2 | "3 redundant memory concepts; steps run memoryless" | **Confirmed** | `ShortTermMemoryAdapter` is wired **zero** times; composition binds only `InMemoryMemory` |
| 3 | "Security is ceremony without enforcement" | **Confirmed, and worse than stated** | See below — one structural defect the audit missed |
| 4 | "Evaluator too rigid for unstructured tasks" | **Not a finding** | Already normative policy, verbatim |
| 5 | "32 event subclasses cause maintenance overhead" | **Count exactly right; concern already solved; fix rejected** | 1 base + **32** subclasses. Catalog is generated and CI-checked already; pruning would destroy audit resolution |
| 6 | "Universal across MCP / gRPC / JSON / OpenAI API" | **Right about the design, wrong about the status** | A2A is deferred, not native; one port currently violates the rule |
| 7 | "Prune the empty placeholder folders `agency/`, `aoi/`, `outer_loop/`, `runtime/`" | **Emptiness confirmed; remedy correct for two of four, destructive for the other two** | All four hold a docstring-only `__init__.py`. But `agency/` and `runtime/` are the **A** and **R** of CAR — see §7.7 |
| 8 | "Workflow flexibility 82/100" | **Understated as a gap, and the only genuinely new finding** | Nothing exists: no `WorkflowStep`, no `PRDSpec`, no `StoryBoard`, no doc above the inner loop. Folded in as §2.13 and B8 |

### 7.1 Port and doc count — right number, wrong examples

The count holds. The illustrative list does not: **`AOICoprocessor` and `RHI` are not ports.** AOI is
three advisory Protocols (`RewardPredictor`, `FailurePredictor`, `CostPerformanceEstimator`) in
`ports/advisory.py`; RHI is an outer *loop* with no port at all. Naming non-existent ports in an
overengineering complaint weakens a case that is otherwise sound.

The proposed remedy also misidentifies the five mandatory ports. Sprint 3 item A.10 already names them,
and they are `model_provider`, `policy_engine`, `resource_governor`, `tool_registry`,
`trajectory_store` — **`PolicyEngine`, not `Workspace`**. `Workspace` is profile-optional by
construction: a `chat` run binds none.

**Where the remedy goes too far:** "freeze port expansion until an adapter exists" is right; "keep only
5 ports" is not. A port is ~25 lines of `Protocol` and is precisely the mechanism that makes every
deferral in the [phased migration matrix](../../07-roadmap/phased-migration-matrix.md) safe — deleting
`EmbeddingProvider` does not simplify the system, it converts a deferred component into a future
refactor. **Freeze the compatibility promise, not the declaration.** §8.2 gives the mechanism.

### 7.2 Memory redundancy — confirmed

`ShortTermMemoryAdapter` and `InMemoryMemory` both live in `adapters/memory/short_term.py`;
`composition.py:63` binds only the latter. The `ShortTermMemory` port therefore has a written adapter
that no code path reaches — dead code behind a live contract, exactly as claimed, and exactly what
foundation-review D12 records.

Two corrections to the framing. First, `TrajectoryStore` is not a redundant *third* memory concept — it
is wired (as a bus observer, `composition.py:78`) and serves a different purpose (append-only audit and
replay). Second, "use `TrajectoryStore` as the single authoritative source of step history" is right
about *authority* but insufficient for *prompt assembly*: the store is event-shaped and append-only, so
a sliding window over it is still needed to build a request. That is Sprint 3 B.2, and it is the same
data §6 B1 recommends also exposing as a recall source.

### 7.3 Security — confirmed, plus one defect the audit missed

Every specific is verified:

* **Grant expiry is never checked at the point of effect.** `DefaultPolicyEngine.get_grant()`
  (`kernel/policy/engine.py:24-32`) *does* check `expires_at` — but `kernel/dispatch.py` never calls it.
  It checks only `decision.grant_id is None`. The expiry logic is dead code.
* **Non-gated tools are allowed unconditionally.** `authorize()` returns `allowed=True` for anything
  absent from `always_gate` — no scope check, no autonomy-level check, no containment check against
  `RunContext.workspace_root`.
* **Path scoping guesses argument key names.** `engine.py:45` literally iterates
  `("path", "file_path", "target_file", "dir")`.

**The defect not identified:** the normative [tool catalog](../../03-contracts-and-models/tool-catalog.md)
defines the primary mutation tool as `edit_file(request: EditRequest)`, where `path` lives *nested
inside* the `EditRequest` model. A flat scan of top-level argument keys **cannot find it even in
principle** — so the single most dangerous tool in the catalog produces an empty `scope_paths` tuple.
And `scope_paths` is never enforced anywhere regardless. The mechanism is not merely fragile; it is
structurally incapable of scoping the tool it exists for. The fix is therefore **not** a better key
list — it is schema-declared scoping at registration time (§6 A10).

Two further defects surfaced while verifying: `dispatch.py:41-45` constructs **two distinct**
`ToolCallRequested` instances for emit and intercept (D16), and lines 103-119 branch
`ToolCallCompleted` vs. `ToolCallFailed` on `result.truncated` — so a **successful but truncated**
result is reported as `error_kind="execution_error"` (D5). Both are on the Sprint 3 list.

The project's own [STATUS.md](../../STATUS.md) now states the same conclusion in one line —
*"Capability dispatch choke point: Partial (happy path; policy mostly permissive)"* — which is the
right way to hold it: the gap is recorded as implementation truth rather than argued away.

### 7.4 Evaluator rigidity — already normative

This claim describes existing policy as though it were a gap.
[Task & Acceptance](../../03-contracts-and-models/task-and-acceptance.md) already states that a task
with no criteria and no gates "terminates on the model's own completion signal. Nothing independently
verifies it," that the profile is recorded in `run.started` and persisted "so no later analysis,
benchmark report, or outer-loop training set can mistake an ungated run for a gated one," and that such
runs are "excluded from benchmark suites and from outer-loop evidence by construction." The proposed
fix — classify non-code tasks as unverified in telemetry — *is* that text. No change indicated.

### 7.5 Event schema — count exact, staleness already solved, remedy still wrong

The count is exact: 32 subclasses plus the `Event` base, all 32 registered in `ALL_EVENTS`.

**Two corrections to an earlier draft of this section, both of which change the conclusion:**

* The claim that `StepScoredEvent` and `IndexUpdated` were missing from the catalog was a **false
  positive**. The catalog keys events by *wire name*, not class name — both are present as
  `step.scored` (line 67) and `index.updated` (line 98). There is no taxonomy divergence.
* The "stale CI event catalog" concern is **already fixed structurally**.
  `scripts/gen_event_catalog.py` generates the catalog from `ALL_EVENTS` and supports `--check`, and
  `.github/workflows/ci.yml:43` runs it, so divergence fails the build. Its own docstring gives the
  reasoning this document would otherwise have had to argue: "a hand-maintained registry of thirty-odd
  events drifts within a month."

The catalog *is* stale right now — `--check` currently reports it needs regeneration — but that is an
in-flight working-tree state with a one-command fix, not a design defect. **A11 is therefore withdrawn
as a recommendation and recorded as already implemented.**

What remains valid is the rejection of the proposed remedy.

**But collapsing to four event types would destroy load-bearing properties**, and would trade a
documentation problem for an architectural one:

* The `ToolCallRequested` / `ToolCallAuthorized` split exists *specifically* so an audit can answer
  "what did the agent try to do" separately from "what was it allowed to do." Merging them into one
  event with a payload field makes the security audit trail a matter of reading flags.
* `ApprovalRequested` / `ApprovalResolved` are the durable-gate state machine. They are not detail.
* Profiles require that "absence of a verdict and a verdict of pass must never be representable by the
  same value" — which a generic event carrying an optional `gate_report` field reintroduces immediately.

Typed events are also *cheaper* to read, not more expensive: a discriminated union narrows in one step,
where a generic envelope forces every consumer to branch on a string and re-validate a payload.

**The correct remedy is to generate the catalog from the code** (§6 A11). Staleness is a CI problem with
a CI fix; it is not evidence that the taxonomy is too fine.

### 7.6 Universality — the design is sound, the status claim is not

The architectural reasoning is correct and worth restating: because
[remoteable-ports.md](../../02-architecture/remoteable-ports.md) requires every port method to be
`async` and every payload to be Pydantic-serializable, transport becomes a shim rather than a refactor.
`AsyncIterator[T]` is explicitly permitted where `T` is serializable, which is what makes streaming
remoteable. That rule is real, and it is the right rule.

Three corrections to the matrix:

| Claim | Correction |
| :--- | :--- |
| **A2A — "Native"** | **Deferred.** [protocols-mcp-a2a.md](../../03-contracts-and-models/protocols-mcp-a2a.md) and [ADR-0010](../../08-decisions/0010-defer-exotic-components.md): A2A waits for "a genuinely remote peer agent." The entry point *satisfies its shape*; nothing implements it |
| **gRPC — "Seamless… minimal boilerplate"** | Overstated. The same doc notes gRPC "brings protobuf schema management and a threading model that fights asyncio," and is warranted "when a second consumer or a genuinely remote peer appears, not before." Start with msgpack or JSON-RPC over a Unix socket |
| **"100% async, pure Pydantic" (achieved)** | **Aspiration, not yet enforced.** `test_port_shape.py` is specified but the rule has a live violation: `WorktreeManager.allocate() -> Workspace` (`ports/workspace.py:40`) returns a **Protocol instance** — a live object, forbidden by the rule's own table. `remoteable-ports.md` also self-reports `Toolchain.detect(root: Path)` |

That first violation matters more than it looks. `WorktreeManager` is exactly the port a remote or
containerized runtime would replace, and returning a live `Workspace` is the one shape that cannot cross
a wire. The fix is a serializable handle — `WorkspaceRef(branch_id)` resolved through the registry — and
it is §6 A12.

**Honest verdict:** SAGIHA is *designed* for universality across MCP, JSON/SSE, OpenAI-compatible
endpoints, and later gRPC, with a credible mechanism. It has not yet *demonstrated* it, one port
contradicts it, and A2A is a shape rather than a capability.

### 7.7 Empty packages — the observation is right, the remedy is half wrong

Verified against the tree: `src/sagiha/agency/`, `aoi/`, `outer_loop/` (including
`outer_loop/evaluator/`), and `runtime/` each contain exactly one file, an `__init__.py` of 109–144
bytes holding a docstring and nothing else. `src/sagiha/prompts/` does not exist at all (G7). The
observation is correct and it corroborates three separate foundation-review findings — V1's note that
the CAR contract is vacuous until `agency/` has code, G3's empty `outer_loop/evaluator/`, and U1's
suggestion to add a canary module.

**Why "prune to four folders" is the wrong conclusion for two of them.** `agency/` and `runtime/` are
the **A** and **R** of CAR. Deleting them would contradict
[ADR-0007](../../08-decisions/0007-trusted-computing-base.md), delete the home
[ADR-0018](../../08-decisions/0018-native-workflow-dag.md) assigns to `WorkflowStep`, and — most
damagingly — void the `import-linter` layer contracts, which are the single strongest *implemented*
property this project has. §2.1 rests SAGIHA's architecture argument on mechanical boundary
enforcement in a language that gets none from its compiler. Reducing the folder count by deleting the
layers those contracts constrain would trade the one demonstrated advantage for tidiness.

**The emptiness is nonetheless a real defect, and `.importlinter` already admits it in a comment.**
The `car-layering` contract carries this note against its own ignore rule:

> `agency/` is an empty stub until S3 — the ignore above legitimately matches nothing yet. warn, not
> error, on an unmatched ignore so Sprint 1's empty package skeleton doesn't fail this contract;
> revisit once `agency/` has code.

and sets `unmatched_ignore_imports_alerting = warn` to keep CI green. That is an honest, correctly
annotated temporary concession — but it means the *strongest* claim in §2.1, that SAGIHA is the only
project enforcing its boundary mechanically in a dynamic language, is presently resting on a contract
whose subject is an empty package. **The fix is code, and Sprint 3 already writes it** — it merely has
not assigned it a home: **prompt assembly (B2) belongs in `agency/`** (it is exactly "emits intents
only," per §8.1's ring diagram) and **tool execution over the dev-mode subprocess `Workspace` (B4)
belongs in `runtime/`**. Then flip `unmatched_ignore_imports_alerting` back to `error`, which is what
makes the concession self-closing rather than permanent. That is A13.

`aoi/` and `outer_loop/` are a different case and the prune is right there: both are deferred behind
[ADR-0010](../../08-decisions/0010-defer-exotic-components.md) triggers, neither has a Sprint 3 role,
and a package is not the deferral seam — the **port** is. This is the same distinction §8.2 draws for
ports: freeze the promise, not the declaration. An empty `aoi/` package promises nothing that
`ports/advisory.py` does not already promise, and `ports/advisory.py` is where the three advisory
Protocols actually live.

**One clarification the proposal gets right and this document should not obscure.** The instinct
behind "prune the placeholders" is sound — the ratio of declared structure to running code is the
condition every review here has diagnosed. The correction is only about *which* structure is
load-bearing. Delete what promises nothing; fill what promises something.

---

## **8. Proposed Structure — Extensible, Universal, Fast, Measurable**

The audit's real insight is that SAGIHA specified breadth before proving depth. The remedy is not to
delete specification; it is to make **stability an explicit, machine-checked property** so breadth costs
nothing until it is used. Four mechanisms, in dependency order.

### 8.1 Five rings, one import contract

```
domain/        pure Pydantic. Imports nothing from sagiha.
   ↑
ports/         Protocols only. Imports domain. Never adapters.
   ↑
kernel/        bus · dispatch · policy · governor · runloop.        ← the TCB
   ↑
agency/        prompt assembly · planning · candidate search.        emits intents only
   ↑
adapters/      all I/O. May import domain + ports. Never kernel internals.
   ↑
composition.py the ONLY module permitted to import adapters/
```

`import-linter` already enforces `agency/ ↛ runtime/`. Extend it to the full ring set, and add the one
contract that makes the TCB real in code rather than in prose: **nothing outside `kernel/` may import
`kernel.policy` or construct a `Grant`.** [ADR-0007](../../08-decisions/0007-trusted-computing-base.md)
asserts this; a layer contract proves it on every commit.

### 8.2 Port tiers — the mechanism exists; give it teeth and two axes

**Correction to an earlier draft:** this section originally proposed inventing a three-tier stability
scheme. It already exists. [Port Stability & Versioning](../../03-contracts-and-models/port-stability-and-versioning.md)
defines **Stable / Provisional / Experimental** with a graduation rule ("two adapters implement them and
the conformance suite has been stable for one minor release — evidence, not calendar"), and every port
module in `src/sagiha/ports/` already declares `STABILITY` alongside `PORT_VERSION`.

So the audit's concern is already largely answered by design. What is missing is smaller and more
specific:

**(a) The doc's tier lists and the code's declarations disagree.** The doc names five Stable ports;
the code marks eight (`model`, `workspace`, `memory`, `tool_registry`, `trajectory`, plus `orchestrator`,
`governor`, `policy` — the last three appear in no doc tier list). `lsp` and `search` are `provisional`
in code and absent from the doc's Provisional row; `embedding` is `experimental` in code and unlisted.
This is the *same* drift class the event catalog already solved, so it takes the *same* fix: **generate
the stability table from the `STABILITY` declarations** and `--check` it in CI, exactly as
`gen_event_catalog.py` does for events. One script, one CI line, drift becomes a build failure.

**(b) Tier meaning is documented but unenforced.** Nothing checks that an Experimental port has few
consumers, or that a third-party adapter never declares against one. Two cheap CI assertions:

| Tier | Enforceable rule |
| :--- | :--- |
| **Stable** | Conformance suite required; ≥1 real adapter plus a cassette; breaking change needs an ADR |
| **Provisional** | Conformance suite required once any adapter is bound; changelog entry on every change |
| **Experimental** | **≤1 consumer, and it is a test.** No entry-point adapter may declare against it |

**(c) Stability and binding-requirement are two different axes, and conflating them caused the audit's
error.** "Will this contract change?" is not "must this port be bound?" The evidence is direct: Sprint 3
A.10 makes `model_provider`, `policy_engine`, `resource_governor`, `tool_registry`, `trajectory_store`
**mandatory at composition** — while `Workspace` and `Memory` are *Stable* contracts that a `chat`
profile leaves **unbound**. Both facts are correct simultaneously. Stating the axes separately is what
prevents the next reader from concluding that 22 ports must collapse to 5:

| | Bound in every profile | May be unbound |
| :--- | :--- | :--- |
| **Stable contract** | `ModelProvider`, `PolicyEngine`, `ResourceGovernor`, `ToolRegistry`, `TrajectoryStore`, `Orchestrator` | `Workspace`, `Memory` |
| **Provisional / Experimental** | — | `Toolchain`, `Evaluator`, `LSPAdapter`, `Indexer`, `CodeGraph`, `Reviewer`, `CandidateSearch`, `MetaImprover`, `EmbeddingProvider`, advisory trio |

The payoff is that the audit's real fear — interface churn when adapters finally arrive — applies only
to ports that made a promise. An Experimental port makes none and can be reshaped by its first adapter
at zero cost, while every roadmap trigger still has a port shaped to accept it. **Freeze the promise,
not the declaration.**

### 8.3 Universality: one contract in, one contract out, everything else a shim

Universality does not come from supporting many protocols. It comes from having exactly **two**
boundaries and refusing to add a third.

```
        ┌── inbound: execute(TaskSpec, RunContext) -> AsyncIterator[Event] ──┐
CLI/TUI ┤                                                                    │
MCP srv ┤                          KERNEL                                    │
HTTP/SSE┤                                                                    │
gRPC    ┤   └── outbound: Port Protocols (async, Pydantic frames) ───────────┘
A2A     ┘                            ↓
                     adapters: in-process | UDS+msgpack | gRPC | HTTP
```

| Surface | Direction | Mechanism | Status |
| :--- | :--- | :--- | :--- |
| CLI / TUI | in | In-process `Observer` | S0 |
| MCP client (consume tools) | out | `ToolRegistry` adapter, `trusted_output=False` | S0, stdio |
| MCP server (expose SAGIHA) | in | JSON-RPC over the event stream | S1 |
| HTTP + SSE | in | Event serialization, `?since=<step_id>`, redaction in the streamer | S1 |
| gRPC / protobuf | out | Transport shim behind unchanged Protocols | **Trigger:** a second consumer or a non-Python sidecar |
| A2A | both | Agent card + task lifecycle | **Trigger:** a real remote peer |

Two rules keep this honest, and both are currently violated somewhere:

* **Frames, not objects.** Any port returning a live object is not remoteable regardless of how async it
  is. `WorktreeManager.allocate() -> Workspace` must become `-> WorkspaceRef`, resolved through the
  registry. Enforce with `test_port_shape.py`, which is specified and not yet written.
* **One inbound signature.** No `execute_chat()`, no REST-only entry point. A channel that needs a
  second signature is evidence the boundary is wrong — [entry points](../../02-architecture/entry-points-and-piloting.md)
  already says this; the tier table above is what keeps it true as surfaces are added.

### 8.4 Performance: budgets at the port, sidecars behind it

Performance claims need numbers attached to boundaries, or they become "we'll optimize later." Attach a
p95 budget to each port and make the breach the migration trigger:

| Port | p95 budget | Breach remedy (already port-shaped) |
| :--- | :--- | :--- |
| `Indexer.find_symbols` | < 50 ms warm | Out-of-process indexer over UDS |
| `LSPAdapter.get_diagnostics` | < 500 ms warm, typed `unavailable` never blocking | Wider warm pool under `ResourceGovernor` |
| `CodeGraph.impacted_by` | < 100 ms at 2 hops | Embedded property store (Kùzu) |
| `kernel.dispatch` overhead | < 5 ms excluding tool work | Profile the choke point; it is on every call |
| Prompt cache hit ratio | > 0.80 multi-step cloud | Prefix-stability regression — treat as a defect |

Plus the two structural rules the references paid to learn: **indexing communicates by channel and never
blocks the agent loop** (Grok), and **every file-watch path has a size ceiling and a debounce** (§6 A5).

### 8.5 Quality: no mechanism without a slice and a gate

The complexity budget from §6 C5, made concrete — the single rule that would have prevented the
condition this audit describes:

> **A new port, event type, or subsystem enters the tree only with (a) a vertical slice that uses it and
> (b) a gate in E0 that measures it.** Absent either, it is `provisional` and has at most one consumer.

Paired with generated artifacts — event catalog from `events.py`, config JSON Schema from the Pydantic
config model, port tier table from `STABILITY` declarations — this makes doc/code drift a build failure
rather than a review burden. That is the durable fix for the audit's finding #5, and for the class of
problem it belongs to.

---

## **9. Recommendations — The Best Combination**

**The synthesis in one line:** *keep SAGIHA's verification-and-capability spine exactly as specified,
borrow the reference projects' production ergonomics wholesale, and add one earned-learning loop that
SAGIHA currently lacks entirely.*

**1. Do not dilute the thesis.** SAGIHA's reason to exist is that it can prove a change helped. E0
first, the A/A noise floor, pristine injected tests, `tests_unmodified` as a hard gate, gates separate
from scores, capability grants at one choke point, and replay determinism are the spine. Every one of
them is absent from all four references, and each is far cheaper to build in from the start than to
retrofit. If schedule pressure forces cuts, cut features, never the spine.

**2. Ship Tier A inside S0/S1 — all twelve live items** (A11 is withdrawn as already implemented;
A13 was added later and is the cheapest of the set because Sprint 3 writes that code anyway). They
total a few hundred lines and each closes a
failure mode a shipping project already hit or an audit already confirmed. The diagnostics delta (A1)
and the journal-mode probe (A2) are the two with the worst failure-to-cost ratio if skipped: one is a
silently broken build, the other is a `SIGBUS` panic on an ordinary developer machine. A3 (loop
guardrails) belongs in the same pass because the dispatch choke point already sees everything it needs,
and adding it later means touching the most security-sensitive code in the system twice.

**2a. Treat A9 and A10 as the highest-priority items in the entire document.** Everything §2.8 claims
about SAGIHA's security advantage is currently false in code: the grant is minted, stored, never
verified, and scoped by guessing argument key names in a way that cannot reach the primary mutation
tool's path at all. A capability system that does not check its own capability is strictly worse than
OpenCode's blocking modal, because it *reads* as secure. Until A9 and A10 land, the security column in
§2.8 describes an intention.

**3. Treat the trajectory store as an asset, not an archive (B1).** SAGIHA already writes every step,
tool payload, and diff to SQLite for replay and audit. Hermes gets experiential search from the same
data for the cost of an FTS5 index. This is the highest capability-per-line item in the entire document.

**4. Add earned learning, bounded (C1).** SAGIHA's self-improvement runs exclusively through an outer
loop costing thousands of dollars per iteration on a deliberate schedule. Hermes demonstrates a
complementary loop costing one cheap model call per successful task. These are not competitors: RHI
tunes the harness, skill extraction accumulates domain procedure. Route proposed skills through
`MutationProposal` with TCB restrictions and human sign-off, mark them `OPERATOR` provenance only when
the operator accepts, keep them in shadow mode until they beat the noise floor. The architecture to do
this safely already exists — it simply has not been pointed at this use.

**4a. Build the macro-workflow layer, and make it prove itself (B8).** This is the one capability gap
the comparative method could not find, because no reference project has it — Grok's eight-actor goal
system is the closest and it is hard-wired. SAGIHA is unusually well positioned: it already specifies
the *output* of decomposition (`parent_task_id`, disjoint file-set closures) and has no producer, and
it is the only design here that could *measure* whether a planner helped, because E0 supplies the
noise floor and `TrajectoryStore` supplies the trace. Build it native, not on LangGraph — a framework
that owns the loop owns the choke point, the prefix, and the cassette
([ADR-0018](../../08-decisions/0018-native-workflow-dag.md)). Then hold it to the §8.5 rule without
exception: **a planning stage that does not beat no-planning on the benchmark does not ship.** A bad
`StoryBoard` wastes every downstream step and, unlike a bad edit, nothing tests it. This is the single
place in the document where an unmeasured mechanism would be most tempting and most expensive.

**5. Borrow ergonomics without borrowing scope.** Post-edit diagnostics from OpenCode, memory
consolidation from Claude Code, compaction shape from Hermes, resilience concerns from Grok. Do **not**
borrow nine messaging gateways, five parallel edit implementations shipped at once, a 40-tool catalog,
or 75 modules. The reference projects' weaknesses are as instructive as their strengths, and in every
case the weakness is unbounded scope in a dimension that was not measured.

**6. Keep the specification honest against the code.** The largest risk in this comparison is not any
missing feature — it is that SAGIHA's documentation tree describes a system substantially larger than
what exists, and the foundation review's D1 (the ReAct loop cannot dispatch a tool) shows the gap is
already load-bearing. OpenCode built a genuinely good agent in 140 files. Before adding any mechanism
from Tier B or C, close the S0 slice end to end: one failing test, resolved, gated, logged, and
replayable. **Every recommendation above is subordinate to that one.**

**7. Enforce the port tiers that already exist (§8.2) rather than deleting ports.** The overengineering
audit is right that 22 ports before one working tool loop is inverted, and wrong that the remedy is
amputation — the Stable/Provisional/Experimental scheme is already normative and already declared in
every port module. What it lacks is a generated tier table (the trick the event catalog already uses), a
per-tier CI assertion, and an explicit statement that stability and mandatory-binding are separate axes.
Pair that with §8.5 — no new mechanism without a slice that uses it and a gate that measures it — and
the condition the audit diagnosed cannot recur.

**8. Generalize the one pattern this project has already got right.** `gen_event_catalog.py --check` in
CI is the correct answer to doc/code drift, and it is currently applied to exactly one artifact. The
same three lines apply to the port stability table, the config JSON Schema (§6 A8), and the tool
catalog. Generated-and-checked is the only form of documentation that stays true in a tree this size —
and drift, not any missing feature, is what turned a 69-document specification into something an
internal audit could reasonably mistake for overengineering.

---

## **10. Cross-References**

* [CAR Model](../../02-architecture/car-model.md) · [Microkernel & Bus](../../02-architecture/microkernel-and-bus.md) · [Security & Threat Model](../../02-architecture/security-and-threat-model.md)
* [Hexagonal Ports](../../03-contracts-and-models/hexagonal-ports.md) · [Tool Catalog](../../03-contracts-and-models/tool-catalog.md) · [Task & Acceptance](../../03-contracts-and-models/task-and-acceptance.md)
* [DMARTIC Inner Loop](../../04-workflows-and-loops/dmartic-inner-loop.md) · [RHI Outer Loop](../../04-workflows-and-loops/rhi-outer-loop.md)
* [Phased Migration Matrix](../../07-roadmap/phased-migration-matrix.md) · [ADR Log](../../08-decisions/README.md)
* [2026-07-29 Foundation Review](../doing/2026-07-29-foundation-review.md) — the code-verified defect list this document's §1 baseline rests on
* [Sprint 0 Decision Record](./proj_plan_design_and_docs_improvs.md) — the decisions this document's evidence produced, and the answers to the tech-lead questions
* Source overviews: [Claude Code](../../reference/harness_examples/claude_code_overview.md) · [Grok Build](../../reference/harness_examples/grok_build_overview.md) · [Hermes Agent](../../reference/harness_examples/hermes_agent_overview.md) · [OpenCode](../../reference/harness_examples/open_code_overview.md)
