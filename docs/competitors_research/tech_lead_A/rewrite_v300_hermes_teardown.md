---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# Hermes — full teardown of the agent and its self-evolution loop

**References under study:**
`src/hermes_agent/` — Nous Research's Hermes Agent, MIT, © 2025 Nous Research.
`src/hermes_self_evolution/` — Hermes Agent Self-Evolution, MIT, © 2026 Nous Research.

**Reader:** Tech Lead A, ahead of the AETHER v3.0.0 architecture review.

---

## 0. What this document is, and is not

Same posture as the Grok Build teardown: an **audit followed by suggestions**, not a plan.
Nothing here decides anything, nothing here overrides
[`rewrite_v300_decisoes_adr.md`](rewrite_v300_decisoes_adr.md), and where a finding contradicts a
decision we already made the document says so and leaves it open for the review.

No code is proposed for reuse. Both repositories are MIT, so the licence would permit it; the
standing constraint is about provenance, and it holds regardless of licence — we study
mechanisms and write our own.

Hermes is our **designated primary competitor**. The RFP frames AETHER against it directly, and
`PLANNING.md` T-targets are stated relative to it. That makes this teardown different in kind
from the Grok Build one: Grok Build is a reference we mine for ideas, while Hermes is the thing
we have to beat on a measured axis. Some of what follows is therefore about *where its
architecture creates a ceiling we can price*.

Proposals continue the shared numbering at **P42**, after
[`rewrite_v300_grokbuild_proposals.md`](rewrite_v300_grokbuild_proposals.md) (P1–P15) and
[`rewrite_v300_grokbuild_teardown.md`](rewrite_v300_grokbuild_teardown.md) (P16–P41).

---

## 1. Method and scale

Read directly: the whole of `hermes_self_evolution` (it is small); in `hermes_agent`, the
`agent/` runtime modules, the verification ledger and its stop guard, the compaction stack, the
curator and background-review loop, delegation, checkpoints, cron, the toolset and skill
machinery, and `AGENTS.md` in full. Not read in depth: the platform adapters (Telegram, Discord,
Slack, Feishu, Matrix, Google Chat — ~40k lines together), the gateway/web server, the browser and
computer-use tools, the TTS/image/video providers, billing and auth.

| | `hermes_agent` | `hermes_self_evolution` |
| :--- | ---: | ---: |
| Python files | 1,001 | 22 |
| Lines of Python | ~779,000 | 3,892 |
| Largest file | `gateway/run.py` — 26,877 | `generate_report.py` — 504 |
| Second | `cli.py` — 18,485 (859 KB) | `external_importers.py` — 785 |
| Bundled skills (`SKILL.md`) | 33 core + 69 optional | — |
| Licence | MIT | MIT |

One caveat on the checkout: the `tests/` tree is not present in our copy, although `AGENTS.md`
and the self-evolution constraint gate both reference it (`scripts/run_tests.sh
tests/skills/test_<skill>_skill.py`, `pytest tests/ -q`). Test discipline is therefore something
this teardown can describe from the doctrine but not verify from the source, and no claim below
depends on it.

---

# Part A — `hermes_agent`

## 2. Shape, and an honest critique of it

Hermes is a **product**, and the shape shows it. It ships eight messaging platforms, a gateway, a
web dashboard, a TUI, an Electron desktop app, a cron daemon, a kanban board, a skills hub with
GitHub-backed distribution, a plugin system with five extension categories, browser automation,
computer use, TTS/STT, image and video generation, and roughly two dozen model providers. The
coding agent is one posture among many.

The concentration is extreme: `gateway/run.py` at 26,877 lines and `cli.py` at 18,485 lines
(859 KB — very long lines) are god-files by any measure. `AGENTS.md` is candid about it and lists
"refactor god-files into clean modules" as *wanted* work, explicitly naming `cli.py`,
`run_agent.py` and `gateway/run.py`. It also names the countervailing pressure honestly:

> "We are expansive at the edges and conservative at the waist."

That sentence is the design thesis of the whole repository, and it is worth sitting with. Hermes
lets the product grow without bound at the periphery while treating the **model tool schema** as
the scarce resource — because "every tool ships on every API call." The god-files are a
consequence of that trade being enforced at the prompt boundary rather than at the module
boundary.

For our purposes the relevant observation is narrower: none of the mass is in the mechanisms that
determine whether a hard coding task gets solved. As with Grok Build, the ideas are cheap and the
product is expensive.

---

## 3. The governance layer — the highest-value artifact in the repository

`AGENTS.md` is 75 KB of engineering doctrine, and it is more valuable to us than any single
module. It reads as a rubric an automated reviewer can apply, and it encodes real closes rather
than aspirations.

### 3.1 The Footprint Ladder

A decision procedure for "should this be a new capability, and at what cost?" — choose the
**highest (least-footprint) rung that correctly solves the problem**:

| Rung | Mechanism | Permanent prompt footprint |
| ---: | :--- | :--- |
| 1 | Extend existing code | zero |
| 2 | CLI command + skill | zero model-tool footprint |
| 3 | Service-gated tool (`check_fn`) | zero unless a prerequisite is configured |
| 4 | Plugin (out-of-tree, runtime-discovered) | zero in core |
| 5 | MCP server in the catalog | zero permanent core-schema footprint |
| 6 | New core tool | **paid on every API call** |

With a stated escalation rule: "When 3+ open PRs try to integrate the same *category* of thing
(memory backends, providers, notifiers), don't merge them one at a time — design an ABC +
orchestrator, wrap the existing built-in as the first provider, and turn the competing PRs into
plugins against that interface."

> **P42 · Adopt a footprint ladder for capability decisions.** Grade A, zero cost, and it is a
> decision that has to exist before the first "can we just add a tool for that?" conversation.
> Our blueprint starts at ~8 core ports and ADR-0023 already says ports pay rent; the ladder is
> the *tool-side* equivalent and it is sharper, because it names the cheaper alternatives in
> order instead of just setting a bar. It also interacts directly with the cache-stable prefix
> layout in [`rewrite_v300_contexto_memoria.md`](rewrite_v300_contexto_memoria.md): the tool
> schema is the first block in the prefix, so a tool added at M2 is a cost paid on every call
> through M5.

### 3.2 The caching policy, stated as a hard rule

> "**Do NOT implement changes that would:** alter past context mid-conversation; change toolsets
> mid-conversation; reload memories or rebuild system prompts mid-conversation. […] The ONLY time
> we alter context is during context compression."

And the corollary, which is the part we do not currently have: **slash commands that mutate
system-prompt state must be cache-aware — deferred invalidation by default, with an opt-in
`--now` flag.** `/skills install` is named as the canonical pattern.

> **P43 · Deferred-by-default state mutation, with an explicit `--now` opt-in.** Grade A. Any
> AETHER surface that can change the stable prefix — enabling a tool, installing a skill, loading
> a memory file, switching a profile — should default to taking effect at the *next* run and
> require an explicit flag to invalidate now. This is one boolean per command and it prevents an
> entire class of silent cost regression that is nearly impossible to attribute after the fact.

### 3.3 "Before you call it a bug — verify the premise"

Four named failure patterns, each distilled from a real closed PR: *intentional design, not a
gap*; *the premise doesn't hold against how X actually works*; *this fix was wrong — the omission
was deliberate* (a real case where restoring "missing" `__init__.py` files made a test tree
shadow the real plugin and delete its `register()` at import time); *overreached / resurrected an
approach we'd moved past*.

The throughline: "If you can't point to the exact line where the bug manifests AND show the fix
changes that line's behavior, you haven't verified the premise."

> **P44 · A premise-verification rubric for autonomous change.** Grade A for M4+, and it is
> free to write now. This is written for human contributors, but the failure modes are exactly
> the ones an autonomous agent exhibits: fixing an intentional design, acting on a wrong model of
> an existing mechanism, restoring a load-bearing absence. If AETHER is going to make unattended
> changes to a real codebase, a version of this rubric belongs in the operating brief, and the
> "point at the line" requirement is a checkable output contract rather than a vibe.

### 3.4 Skill authoring, HARDLINE

Eight enforced rules, of which the sharpest is: **`description` ≤ 60 characters, one sentence,
ends with a period.** Stated reason: "Long descriptions bloat skill listings and dilute the
model's attention when many skills are loaded." No marketing words; don't repeat the skill name;
state the capability, not the implementation. It even ships the assertion to verify it.

Also: a fixed section order (`## When to Use`, `## Prerequisites`, `## How to Run`,
`## Quick Reference`, `## Procedure`, `## Pitfalls`, `## Verification`); target ~200 lines for a
complex skill; **scripts go in `scripts/`, not inlined** — "don't expect the model to inline-write
parsers, XML walkers, or non-trivial logic every call."

And a rule that reads like an anti-pattern we would otherwise walk into: **no `offset`/`limit`
pagination on instructional tools.** "Models will read page 1 and skip the rest."

> **P45 · Hard budgets on every model-visible text artifact, enforced in CI.** Grade A. A
> 60-character description limit sounds petty until you multiply it by the number of skills in the
> listing and by every call in a run. The generalizable rule is that *anything injected into the
> prompt has a declared byte budget and a test that fails when it is exceeded* — which pairs with
> the graded-degradation ladder we noted from Grok Build's skill listing (§9.4 there).

---

## 4. Prompt caching

The default layout uses **four `cache_control` breakpoints**: the static system prefix, the end
of the system prompt, and the last two non-system messages. When a static system prefix is
unavailable it falls back to one system breakpoint plus the last three messages.

Two details worth recording because they are provider-portability scars, not design:

- On OpenRouter, a top-level `cache_control` on a `role: "tool"` message causes a **silent hang** —
  so the marker is skipped for empty tool messages and placed on a content part otherwise.
- An empty assistant turn (pure `tool_calls`) gets no top-level marker, because it is ignored on
  the envelope layout.

The module is written as pure functions with no agent dependency, and `marker_count` is computed
lazily "on demand… only tests consume this; keeping it lazy avoids walking every message part and
tool schema on the per-request hot path."

This is the layout our context doc already specifies, arrived at independently. The confirmation
is useful, and the two provider quirks are worth carrying into our adapter tests since we would
otherwise find them the same way Hermes did.

---

## 5. The coding posture — one seam, many consumers

`agent/coding_context.py` is the module I would most like us to have an equivalent of, because it
solves a problem our design has not yet named.

When Hermes runs inside a code workspace it "shifts into a **coding posture**", and this module is
"the single place that decides whether we're in that posture and what it implies, so the rest of
the codebase never re-derives 'are we coding?' on its own."

The posture is a frozen `RuntimeMode` selected from a small `ContextProfile` registry (today:
`coding` and `general`). **A profile is data.** It declares the toolset to collapse to, the
operating brief to inject, and hints for other domains — `model_hint`, `memory_policy`,
subagent behaviour. Five consumers read the same resolved object: system prompt, toolset,
delegation, model routing, memory/compression.

The cache-safety contract is explicit and matters:

> "The mode is resolved **once** and is immutable. The workspace snapshot is built once at
> prompt-build time and baked into the *stable* system-prompt tier — never re-probed per turn
> (that would shatter the prompt cache). Branch and dirty state drift mid-session, so the brief
> tells the model to re-check with `git` before acting on the snapshot."

That last sentence is the elegant part: rather than keeping the snapshot fresh (expensive, cache-
breaking) or letting it go stale silently (wrong), the brief tells the model the snapshot is a
point-in-time fact and to re-derive it before acting. **Staleness is disclosed rather than
prevented.**

There is also a restraint worth noting. The default posture is *prompt-only* and does not touch
the user's configured toolsets; collapsing the toolset happens only under an opt-in `focus` mode,
because "someone who explicitly enabled image-gen or Spotify shouldn't lose it for being in a git
repo."

> **P46 · A resolved, immutable run profile as a single seam.** Grade A. AETHER will accumulate
> the same conditional logic — is this a benchmark run or an interactive one, a Python repo or a
> polyglot one, a container or the host — and the alternative to a profile object is that same
> question re-answered in eight places with eight subtly different answers. Making the profile
> *data* (declaring toolset, brief, model hint, memory policy) rather than *code* is what makes
> it testable and what lets a benchmark run pin its profile in the manifest.
>
> **P47 · Disclosed staleness for snapshot facts.** Grade A, near-zero cost. Any repo fact baked
> into the stable prefix — branch, dirty state, file inventory, dependency versions — should
> carry an explicit "this was true at prompt-build time; re-check before acting" instruction
> rather than being refreshed per turn. This is a direct cache-cost lever.

---

## 6. The verification evidence ledger — the headline mechanism

This is Hermes' answer to the same question Grok Build answers with a skeptic panel, and the
answer is completely different, much cheaper, and complementary rather than competing.

### 6.1 The ledger (`agent/verification_evidence.py`, 649 lines)

A SQLite store at `~/.hermes/verification_evidence.db` that records **what the agent actually
proved while working in a code workspace.** Its self-description is precise about what it is not:

> "It is deliberately passive: it never decides to run a suite, never blocks completion, and never
> upgrades targeted checks into 'repo green'."

Every terminal result passes through `classify_verification_command`, which produces a
`VerificationEvidence` record: `command`, `canonical_command`, `kind`, `scope`, `status`,
`exit_code`, `cwd`, `root`, `session_id`, `output_summary`.

The classification is the interesting part, and it is entirely deterministic:

- Commands are split on `&&`, `||`, `;` and tokenized with `shlex`.
- Known prefixes are stripped (`_strip_command_prefix`) and equivalent forms are matched
  (`_equivalent_needles`), so `python -m pytest`, `pytest`, and `uv run pytest` canonicalize
  together.
- `kind` is derived from the canonical command (test / build / lint / typecheck).
- `scope` is derived from whether arguments look like targets — so `pytest` is repo-scope and
  `pytest tests/test_foo.py::test_bar` is narrow-scope. **A narrow pass is never promoted to
  "repo green."**
- Ad-hoc verification scripts are recognized by path convention
  (`hermes-verify-*`, `hermes-ad-hoc-*` under a temp dir) so a throwaway repro script still
  counts as evidence.

And the freshness mechanism: `mark_workspace_edited` **invalidates prior evidence when the
workspace changes.** Evidence is therefore a claim about a specific state of the tree, not a
permanent property of the session.

Retention is bounded on three axes: 30 days, 100 events per session-root, 10,000 total
unreferenced events.

### 6.2 The stop guard (`agent/verification_stop.py`, 273 lines)

> "This module is intentionally policy-only. It never runs checks itself; it turns the passive
> verification ledger into a bounded follow-up when the model tries to finish immediately after
> editing code without fresh evidence."

Three refinements that show this shipped and got tuned:

- **Non-code suppression.** A frozen set of extensions (`.md`, `.rst`, `.txt`, `.adoc`, …) whose
  edits "carry no verifiable runtime behavior." When a turn touches *only* those, the nudge is
  suppressed — the comment names this as the fix for a real false positive: "a `SKILL.md` or
  `README` edit must never demand a `/tmp` verification script."
- **Surface awareness.** The default is `"auto"`: ON for interactive coding surfaces (CLI, TUI,
  desktop) and programmatic callers, OFF on messaging platforms "where the verification narrative
  would reach a human as chat noise."
- **Bounded nudge.** At most 8 changed paths are listed, and the evidence summary is capped at
  1,200 characters.

### 6.3 Why this matters for us

Our repair loop currently has a gate that runs checks. Hermes' arrangement is orthogonal and adds
something we do not have: **a record of what has already been proven, keyed to a tree state**,
which makes it possible to ask "does this claim of completion have evidence behind it?" without
running anything.

Put beside Grok Build's cascade, the three approaches occupy different price points:

| | Cost per check | What it proves | When it fires |
| :--- | :--- | :--- | :--- |
| Hermes ledger + stop guard | ~zero (SQLite lookup) | the agent *did* run something relevant, and the tree has not changed since | every turn end after a code edit |
| AETHER tri-state gate (current design) | one test-suite run | the tree passes *our* checks now | per repair cycle |
| Grok Build skeptic panel | N subagent runs | an adversary could not refute the claim | once, on candidate-complete |

These compose. A ledger makes the gate cheaper (skip the suite when fresh evidence covers the
changed scope) and makes the panel sharper (the panel audits recorded evidence instead of
rebuilding it — which is exactly what Grok Build's verifier prompt already demands, without
Hermes' machinery to make it reliable).

> **P48 · A verification evidence ledger, keyed to tree state.** Grade A, and I think this is the
> single most transplantable mechanism in the Hermes codebase. Roughly: a table of
> `(run_id, root, canonical_command, kind, scope, status, exit_code, tree_digest)`, a
> deterministic canonicalizer, and an invalidation hook on every write to the workspace. The
> scope-never-promotes rule is the part that makes it honest, and it is the same discipline as
> our tri-state gates.
>
> **P49 · Policy-only stop guards.** Grade A. The separation — a ledger that *observes* and never
> decides, a guard that *decides* and never observes — is clean hexagonal design applied to a
> place we had not thought to apply it, and it makes both halves independently testable. It is
> also the same shape as Grok Build's `ToolGuardrails` controller and our own `PolicyEngine`:
> pure decision functions over recorded facts.

---

## 7. Tool-loop guardrails

`agent/tool_guardrails.py` is "pure tool-call loop guardrail primitives… intentionally
side-effect free: it tracks per-turn tool-call observations and returns decisions. Runtime code
owns whether those decisions become warning guidance, synthetic tool results, or controlled turn
halts."

The classification is an explicit two-set partition: `IDEMPOTENT_TOOL_NAMES` (read_file,
search_files, web_search, web_extract, session_search, browser_snapshot, plus the MCP filesystem
read family) and `MUTATING_TOOL_NAMES` (terminal, execute_code, write_file, patch, todo, memory,
skill_manage, the browser interaction family, send_message). Repetition of an idempotent call
with identical arguments is a loop; repetition of a mutating call is not necessarily one.

The pure-controller shape is already in our design notes. What is new here is that the
idempotent/mutating partition is *data on the tool*, which means adding a tool cannot silently
break the guardrail — the same lesson as Grok Build's capability-mode-by-tool-kind (P33).

---

## 8. Compaction, and a documented failure of the alternative

### 8.1 The default compressor

`agent/context_compressor.py` summarizes middle turns with an auxiliary model while protecting
head and tail. The self-documented improvements list is a compressed changelog of things that
went wrong:

- **Structured summary template** with Resolved/Pending question tracking.
- **Filter-safe summarizer preamble** that treats prior turns as source material.
- **Historical (reference-only) section headings** replacing "Next Steps" / "Remaining Work" —
  because those headings read as *active instructions* to the successor model.
- **Token-budget tail protection** instead of a fixed message count.
- **Tool output pruning before LLM summarization** — a cheap pre-pass.
- **Scaled summary budget**, proportional to the compressed content.
- **Iterative summary updates**, preserving information across multiple compactions.

The third bullet is the one our context doc already carries as the summary-as-instruction-channel
finding; seeing it here as a fixed defect rather than a theory strengthens it.

### 8.2 Micro-compaction, and the cache bill

`docs/micro-compaction.md` describes an alternative: instead of one big summarization at the
threshold, fold "the single oldest un-absorbed exchange into a running summary" after each turn.
"Micro-compaction pays the same bill in instalments."

And then the documentation does something unusually honest — it argues against its own feature:

> "Each pass also rewrites already-sent history, which **breaks the provider prompt-cache prefix
> every turn**; read Prompt caching before enabling it, because for some setups that cost exceeds
> the benefit."

It ships **off by default**.

This is a direct, documented comparison with Grok Build's prefire two-pass compaction (P24), and
the two land on opposite sides:

| | Hermes micro-compaction | Grok Build prefire two-pass |
| :--- | :--- | :--- |
| When the work happens | continuously, one exchange per turn | in background, ~10 pp before the threshold |
| What it rewrites | already-sent history, every turn | nothing until the compaction moment |
| Cache consequence | **prefix broken every turn** | prefix intact; one break at compaction |
| Latency at the threshold | none (amortized) | pass-2 only (small tail) |
| Default | **off** | on |

Both amortize the *summarization* cost. Only one of them amortizes it without paying a cache
prefix rewrite. This is a good example of why our measurement doctrine matters: the amortization
argument is intuitively compelling and, on the cache-cost axis, wrong.

> **P50 · Treat any mechanism that rewrites sent history as cache-hostile until measured.**
> Grade A as a design rule. Our cost model already carries the 1.25× write / 0.1× read asymmetry;
> the rule that follows is that a feature which rewrites the prefix per turn converts every
> cached read back into a write, and that multiplier has to appear in its ablation before it can
> ship.

---

## 9. The closed learning loop

This is what the RFP means by Hermes' "closed loop", and it has four moving parts.

### 9.1 Background review — the cache-warm fork

After a turn, `spawn_background_review` fires a daemon thread that "replays the conversation
snapshot in a forked `AIAgent` and asks itself 'should any skill/memory be saved or updated?'".

The mechanism detail is the good part:

> "The fork inherits the parent's live runtime (provider, model, base_url, credentials, cached
> system prompt) so **it hits the same prefix cache** and uses the same auth. It runs with a tool
> whitelist limited to memory and skill management tools; everything else is denied at runtime."

And the corollary, spelled out in the model-selection comment: routing the review to a cheaper
model *loses* the cache, "so the fork is cold regardless — replaying the full transcript would
just cold-write it." The default is therefore the **main** model, because a cache read on an
expensive model beats a cold write on a cheap one.

That is a genuinely counter-intuitive cost result and it generalizes to every auxiliary task that
wants the conversation as input.

> **P51 · Cache-sharing forks for auxiliary tasks.** Grade A. Already noted in
> [`rewrite_v300_autonomia_agi.md`](rewrite_v300_autonomia_agi.md) §2.2; this teardown adds the
> quantitative reasoning and the tool-whitelist-at-runtime enforcement. Note the tension with
> Grok Build's skeptic panel, which deliberately uses *different* models per skeptic for
> diversity — so the right answer is task-dependent: forks that need the transcript should share
> the cache, panels that need independence should not.

### 9.2 The curator

`agent/curator.py` (2,019 lines) is inactivity-triggered — no cron daemon. When the agent is idle
and the last run was more than `interval_hours` ago, it spawns a forked agent to review
agent-created skills.

The invariants are strict and stated:

- Only touches skills with `created_by: "agent"` provenance — bundled and hub-installed skills
  are off-limits.
- **Never auto-deletes.** The maximum destructive action is archive, and archive is recoverable
  (`hermes curator restore`), with pre-run `tar.gz` snapshots.
- Pinned skills bypass every auto-transition *and* the LLM review pass.
- "Uses the auxiliary client; **never touches the main session's prompt cache**."

Lifecycle state (`active` / `stale` / `archived`) is derived from a usage sidecar
(`~/.hermes/skills/.usage.json`: `use_count`, `view_count`, `patch_count`, `last_activity_at`,
`pinned`) rather than from LLM judgement.

> **P52 · Provenance-scoped, never-destructive self-modification.** Grade A, and it should be an
> invariant rather than a proposal. Three properties compose into a safe autonomy story: the loop
> may only touch artifacts it created; the worst action is reversible; and a human can pin an
> artifact out of its reach entirely. Our RHI bound is currently "may optimize prompts, routing
> and skills; may never touch the TCB" — that says what it may not touch, and Hermes' formulation
> adds what it may not *do* and what a human can *exempt*.

### 9.3 `/learn` — skill authoring with no new machinery

`agent/learn_prompt.py` (150 lines) builds **one prompt** that instructs the live agent to gather
sources with the tools it already has and author a `SKILL.md` via `skill_manage`, following the
HARDLINE standards embedded verbatim in the prompt.

> "There is no separate distillation engine and no model-tool footprint: the agent does the work
> with its existing toolset, so this works identically on local, Docker, and remote terminal
> backends."

This is the Footprint Ladder applied to its own learning loop — rung 1, zero new surface. A
capability that most designs would implement as a subsystem is implemented as a prompt builder.

### 9.4 The learning graph

`agent/learning_graph.py` assembles a graph of what the user has learned over time: non-base
learned skills as nodes, `MEMORY.md` / `USER.md` chunks as first-class nodes, skill-to-skill edges
from declared `related_skills`, and memory-to-skill edges derived from **lexical overlap**.
`learning_mutations.py` gives every node a stable id so a human can edit or delete one — deleting
a skill archives it, deleting a memory rewrites its file.

The graph is a product feature (a desktop visualization), and it is only lexical, so it is not a
retrieval mechanism. But the underlying decision is interesting: memory and skills are the *same
kind of node*, and the human has a direct, per-node edit surface into the agent's accumulated
state.

> **P53 · A human-editable index over agent-accumulated state.** Grade B. Any system that
> accumulates memories and skills unattended for eight hours needs an inspection and correction
> surface, or the accumulation becomes unauditable. Stable per-node ids and archive-not-delete are
> the cheap half of that; the visualization is not required.

---

## 10. Delegation

`tools/delegate_tool.py` spawns a subagent with isolated context and its own terminal session.
Two shapes: single (`goal` + optional `context`/`toolsets`) and batch (`tasks: [...]`, concurrent,
capped by `delegation.max_concurrent_children`, default 3).

Two roles, and the difference is a capability subtraction:

- `role="leaf"` (default) — cannot call `delegate_task`, `clarify`, `memory`, `send_message`,
  `cronjob`. Retains `execute_code`.
- `role="orchestrator"` — retains `delegate_task`, bounded by `max_spawn_depth` (default 2).

`agent/iteration_budget.py` is a thread-safe consume/refund counter, one per agent. The parent's
cap is 500; each subagent gets an independent 50 — with the consequence stated plainly: "total
iterations across parent + subagents can exceed the parent's cap." And a refinement:
`execute_code` iterations are **refunded** so programmatic tool calling does not eat the budget.

And a durability rule that names a real trap:

> "Background `delegate_task` is detached from the current turn but **still process-local**. For
> work that must survive process restart, use `cronjob` or `terminal(background=True,
> notify_on_complete=True)`."

> **P54 · Per-agent budgets that are independent, not shared — stated as such.** Grade B. The
> honest framing matters more than the mechanism: a tree of agents with per-node caps has no
> global cap, and pretending otherwise produces cost surprises. If AETHER's `ResourceGovernor`
> issues per-subagent budgets, the run manifest needs to record the *tree* total, and there
> should be a separate global ceiling. This connects to P2 (two-phase budget reservation) in the
> companion document — reservation is how you get a real global cap under fan-out.
>
> **P55 · Refund non-model iterations.** Grade B, cheap. If a step does not consume a model call,
> charging it against a model-call budget makes the budget mean two things at once.

---

## 11. Checkpoints — one shared shadow git store

`tools/checkpoint_manager.py` (1,953 lines) creates automatic snapshots before file-mutating
operations, once per conversation turn. "This is NOT a tool — the LLM never sees it."

The v2 design is the interesting part. The pre-v2 layout kept a full shadow repo per working
directory:

> "Each one re-stored most of the project's files under its own `objects/` tree, with zero sharing
> across worktrees of the same project. A single user with a dozen worktrees of the same repo
> burned ~40 MB each (~500 MB total) storing the same blobs over and over."

The fix: a **single shared store** at `~/.hermes/checkpoints/store/` with standard git internals,
`refs/hermes/<hash16>` as the per-project branch tip, `indexes/<hash16>` as the per-project index,
and a `projects/<hash16>.json` metadata sidecar. Git's content-addressable object DB then
deduplicates across projects and across turns.

> **P56 · One content-addressed checkpoint store across all worktrees.** Grade A **for us
> specifically**, more than for Hermes. Our benchmark harness will create many worktrees of the
> *same* upstream repository — that is precisely the pathological case the pre-v2 design hit, and
> we will hit it at higher multiplicity. Deciding the store layout at M0 costs nothing; migrating
> it after a few thousand benchmark runs is the "legacy-<timestamp>/ auto-migrated" directory
> Hermes now carries.

---

## 12. Reliability details worth carrying

**`TurnRetryState`** collapses ~16 one-shot recovery guards into one object. Its docstring is a
useful enumeration of what actually goes wrong on a single model call: credential-pool 429 retry,
per-provider OAuth refresh, long-context compression restart, length-continuation restart,
thinking-signature stripping, multimodal-tool-content stripping, llama.cpp grammar fallback, image
shrink, invalid-encrypted-content, 1M-beta header. Each fires at most once per attempt. Loop
control variables deliberately stay as plain locals: "they are the `while` mechanics, not recovery
bookkeeping, and putting them on the object would add indirection without clarifying anything."

**`bounded_response.py`** bounds reads of HTTP error bodies on streaming requests — a byte cap
*and* a hard wall-clock deadline. The subtlety is worth reading in full: `httpx.iter_bytes()`
blocks inside the socket read, so a deadline checked between chunks cannot interrupt a server that
opens the body and stalls. The fix runs the read on a daemon thread and the caller waits with a
hard deadline, closing the response on timeout. The failure it prevents — an agent hung
indefinitely reading an error message — is exactly the kind of thing that kills an 8-hour
unattended run.

**`cron/lifecycle_guard.py`** rejects cron specs whose prompt or script contains a gateway-
lifecycle command, because an agent that schedules `hermes gateway restart` creates a
SIGTERM-respawn loop every ~10 seconds "until manually broken." The pattern is deliberately
command-shaped, anchored on concrete command identifiers, "so it cannot fire on prose. A cron
`prompt` is fed to a future LLM, not a shell, so an over-broad substring match on English
('Kong API gateway autoscaling and restart behavior') would produce a high false-positive rate
without preventing the actual foot-gun."

> **P57 · Self-DoS as a named lifecycle class, with defence in depth.** Grade A. Already in
> [`rewrite_v300_seguranca_sandbox.md`](rewrite_v300_seguranca_sandbox.md) §3.4; Hermes adds two
> refinements. First, the guard is enforced at *creation* time as well as execution time so the
> agent gets an immediate informative rejection instead of a job that silently fails later.
> Second, the pattern is command-shaped rather than keyword-shaped, with the false-positive
> reasoning written down. Both are cheap and both are the difference between a guard that works
> and one that gets disabled for being annoying.
>
> **P58 · Hard deadlines on every read that can block in native code.** Grade A. The
> daemon-thread-plus-deadline pattern is unglamorous and it is what makes an 8-hour unattended
> target (T5) achievable. Any port that wraps a socket, a subprocess, or a C extension needs it.

---

## 13. The pluggable context engine

`agent/context_engine.py` is an ABC with a declared lifecycle: `on_session_start()` →
`update_from_response()` after each API response → `should_compress()` after each turn →
`compress()` → `on_session_end()` "at real session boundaries (CLI exit, `/reset`, gateway session
expiry) — **NOT per-turn**." Selection is config-driven (`context.engine`), default `"compressor"`,
exactly one active.

This is a clean port in our sense: a small lifecycle contract, one implementation shipped, third
parties substitutable. It is worth noting as evidence that the compaction strategy is the *right
granularity* for a port — coarse enough that a second implementation is meaningful (their example
is an LCM-based engine), fine enough that the contract stays small.

---

# Part B — `hermes_self_evolution`

## 14. The RHI reference

3,892 lines. This is the closest thing in any of our references to what AETHER's M5 meta-loop is
supposed to be, and its scope discipline is instructive: **Phase 1 (skill files) is implemented;
phases 2–5 are planned.** The repository ships one working vertical rather than five partial ones.

Engines: **DSPy + GEPA** (Genetic-Pareto Prompt Evolution, MIT, ICLR 2026 Oral) for text;
Darwinian Evolver (AGPL v3) for code, used strictly as an external CLI, never imported — an
explicit licence-hygiene decision.

Stated economics: **no GPU training, ~$2–10 per optimization run.** Everything is API calls
mutating text and evaluating results.

### 14.1 The loop

```
  find skill (SKILL.md)
        │
        ▼
  build eval dataset ── synthetic | golden | sessiondb
        │                  50% train / 25% val / 25% holdout
        ▼
  validate BASELINE constraints  (proceeds with a warning if the baseline already violates)
        │
        ▼
  GEPA.compile(module, trainset, valset)      ← falls back to MIPROv2 if GEPA unavailable
        │   the skill BODY is the optimizable parameter;
        │   the YAML frontmatter is preserved verbatim and reattached
        ▼
  validate EVOLVED constraints  ── FAIL → save as evolved_FAILED.md, do not deploy
        │
        ▼
  score baseline vs evolved on HOLDOUT
        │
        ▼
  write evolved_skill.md + baseline_skill.md + metrics.json
        │
        ▼
  PR against hermes-agent  (never a direct commit)
```

### 14.2 Constraints as hard gates

`ConstraintValidator` runs before and after. Every candidate must pass **all**; a failure is
immediate rejection, and "GEPA/MIPROv2 never see them as successful."

| Constraint | Rule |
| :--- | :--- |
| Test suite | `pytest tests/ -q` must pass 100%, 300 s timeout, zero tolerance |
| Size | skills ≤ 15 KB · tool descriptions ≤ 500 chars · param descriptions ≤ 200 chars |
| Growth | ≤ +20% over baseline length |
| Non-empty | trivially, but checked |
| Structure | valid YAML frontmatter with `name` and `description` |
| Caching compatibility | no mid-conversation changes, ever — evolved content takes effect on the next fresh session |
| Semantic preservation | must not drift from the original purpose |

The caching constraint deserves its own note because it is stated as an absolute:

> "**Rule: No evolved content is ever hot-swapped into an active conversation.** All changes take
> effect on the next fresh session."

And for tool descriptions specifically: "Schema structure (parameter names, types) must NOT
change — only the description text."

### 14.3 Fitness, and the anti-bloat term

`FitnessScore` is multi-dimensional with declared weights:

```
composite = max(0, 0.5·correctness + 0.3·procedure_following + 0.2·conciseness − length_penalty)

length_penalty = 0                          when size/max ≤ 0.9
               = min(0.3, (ratio−0.9)·3.0)  above 90% of the size limit
```

The length penalty is the mechanism that stops the well-known failure mode of evolutionary prompt
search: variants get longer every generation because more instructions look locally better.
Ramping the penalty from 90% of budget rather than applying it at the cliff means the optimizer
feels the pressure before it hits the wall.

The `LLMJudge` also emits a **`feedback` string**, and this is the point of GEPA specifically:
"GEPA reads execution traces to understand *why* things fail (not just that they failed), then
proposes targeted improvements." The judge is not only a scalar — it is a channel back into the
mutation operator.

### 14.4 Evaluation data — three sources, and the cold-start solution

**Synthetic**: an LLM reads the artifact and generates `(task_input, expected_behavior, difficulty,
category)` tuples, where `expected_behavior` is explicitly "a rubric… NOT exact text."

**Golden**: hand-curated JSONL, auto-split if not pre-split.

**SessionDB**: mining real session history — and this is the clever one. It reads
`~/.claude/history.jsonl` (Claude Code, user inputs only), `~/.copilot/session-state/*/events.jsonl`
(full conversations), and `~/.hermes/sessions/*.json`. The stated motivation: "Solves the
cold-start problem: new Hermes users don't have golden datasets, but they do have session history
from tools they already use."

Two safeguards around that:

- **Secret detection before anything enters a dataset.** A compiled regex covering
  `sk-ant-api*`, `sk-or-v1-*`, generic `sk-` 20+, `ghp_`/`ghu_`, `xoxb-`/`xapp-`, `ntn_`,
  `AKIA[0-9A-Z]{16}`, `Bearer <20+>`, PEM private key headers, a list of known env var names, and
  `password=`/`secret=`/`token=` assignments. Anything matching is dropped, not redacted.
- **Two-stage relevance filtering**, cheapest first: a keyword-overlap heuristic pre-filter, then
  LLM scoring — with candidates capped at `3× max_examples` "to control LLM costs" and the LLM
  error rate reported to the user so they can tell when the judge is misbehaving.

### 14.5 Benchmarks as gates, not fitness

`PLAN.md` is explicit, and it is the right call:

> "**Benchmarks are GATES, not fitness functions.** The fitness function is task-specific (did the
> skill/tool/prompt do its job better?). Benchmarks ensure the improvement didn't break something
> else. A variant that improves skill quality by 20% but drops TBLite by 5% is REJECTED."

The tiering is cost-ordered:

| Benchmark | Tasks | Time | Cost | Role |
| :--- | ---: | :--- | :--- | :--- |
| TBLite | 100 | 1–2 h | $20–50 | primary regression gate; 20-task subset per candidate |
| TerminalBench2 | 89 | 2–4 h | $50–200 | thorough validation, final candidates only |
| YC-Bench | 100–500 turns | 3–6 h | $50–200 | long-horizon coherence check |

With the full ladder: pytest → TBLite fast subset (20 tasks) → task-specific fitness → *top 3
only* → full TBLite → YC-Bench.

> **P59 · Benchmarks gate; a task-specific metric drives.** Grade A, and it resolves a design
> question our measurement doc leaves implicit. Using SWE-bench score as the *objective* of a
> meta-loop invites overfitting to the benchmark. Using it as a *regression gate*, with a
> task-local metric as the objective, keeps the optimization honest and keeps the benchmark
> meaningful as an external check. The "top 3 only get the expensive gate" ordering is the same
> cost cascade we saw everywhere in Grok Build (P28).
>
> **P60 · The full constraint set as a template for our own.** Grade A. Test suite 100%, size
> ceiling, growth ceiling, structural validity, cache compatibility, semantic preservation,
> PR-not-commit. Six of the seven are mechanically checkable and cost nothing; the seventh
> (semantic preservation) is the one they hand-wave, and we should either define it or drop it
> rather than inherit the hand-wave.

---

## 15. Where the self-evolution methodology falls short — and why that matters to us

This is the most useful part of studying it, because the gap is precisely the gap our measurement
strategy exists to close, and here it is visible in a shipped competitor artifact.

**The optimization metric and the evaluation metric are the same function.** `skill_fitness_metric`
is passed to `dspy.GEPA(metric=...)`, and then the same function scores baseline versus evolved on
the holdout set. Whatever GEPA learns to exploit in that metric, the holdout evaluation will
reward. A held-out *split* does not give you an independent measurement when the *measure* is
shared.

**That metric is keyword overlap.** Its own comment is honest — "Quick heuristic scoring (for
speed during optimization)… Simple keyword overlap as a fast proxy" — but it is what the reported
improvement number is computed from. A skill that gets longer and repeats vocabulary from
`expected_behavior` scores higher without being better. The length penalty pushes back, but the
penalty lives in `FitnessScore.composite`, which the DSPy metric path does not use.

**The sample sizes are tiny.** Default `eval_dataset_size` is 20; at a 25% holdout ratio, the
reported improvement is an average over roughly **five examples**.

**There is no noise floor and no significance test.** The result is reported as
`improvement = avg_evolved − avg_baseline`, formatted with a green arrow when positive. Two runs
of the *same* configuration would differ by some amount, and that amount is never measured, so
there is no way to know whether a `+0.03` is a result.

**Baseline constraint violations are waived.** If the baseline skill already fails a constraint,
the run prints "proceeding anyway" — so the evolved variant can be compared against a baseline
that would itself have been rejected.

None of this makes the *architecture* wrong. GEPA with trace-based reflective mutation, hard
constraint gates, held-out splits, and benchmarks-as-gates is a sound design. The gap is entirely
in the measurement layer, and it is the same gap that left our own predecessor with zero
defensible numbers.

> **What I would take from this, stated plainly for the review.** Our M5 meta-loop should reuse
> this architecture and refuse to reuse this evaluation. Concretely, that means: the objective
> metric and the acceptance metric must be different functions; the acceptance metric must be the
> expensive, honest one (LLM-judge with the composite score, or a real task outcome) even though
> the objective can stay cheap; the A/A noise floor must be established for the acceptance metric
> before any evolved variant is accepted; and acceptance must be a significance test against that
> floor, not a positive delta. That is exactly the doctrine in
> [`rewrite_v300_measurement_strategy.md`](rewrite_v300_measurement_strategy.md), applied one
> level up — and being able to point at a competitor's shipped meta-loop as the negative example
> makes the argument concrete rather than pedantic.

---

# Part C — Hermes against Grok Build

Reading both in sequence surfaces where two well-resourced teams independently converged, and
where they went opposite ways. Convergence is evidence; divergence is a decision we have to make.

## 16.1 Where they agree — treat as strong evidence

| Mechanism | Hermes | Grok Build |
| :--- | :--- | :--- |
| Cost-ordered gate cascades | pytest → TBLite subset → fitness → full TBLite → YC-Bench | regex → cheap evaluator → skeptic panel |
| Offline memory/skill consolidation, gated and lock-protected | curator: idle-triggered, `interval_hours`, `.curator_state` | `dream`: config → hours → session count → lock |
| Auxiliary work must not disturb the main prompt cache | curator "never touches the main session's prompt cache"; review fork shares it | subagent panel spawned outside the `task` tool to keep the parent transcript clean |
| Pure decision controllers over recorded facts | `tool_guardrails`, `verification_stop` | `GateDecision` lattice, `AnchorScheme` |
| Never-destructive self-modification | archive, never delete; pinned skills exempt | plan is frozen; strategist edits to it are reverted |
| Hard byte budgets on model-visible text | 60-char descriptions, 15 KB skills, 500-char tool descriptions | skill listing budget %, 256 KB diff cap, 512 KB panel cap |
| Skills as `SKILL.md` with YAML frontmatter | `~/.hermes/skills/`, hub distribution | `.grok/skills/`, `.claude/skills/`, `.cursor/skills/` |
| Deferred activation of prompt-affecting changes | `--now` opt-in; default next session | `/coding` flip deferred; evolved content next session only |

Eight independent convergences. Any one of them could be coincidence; together they read as the
shape of the problem rather than the shape of either team.

## 16.2 Where they diverge — decisions we still owe

| Question | Hermes | Grok Build | Note for the review |
| :--- | :--- | :--- | :--- |
| **How is completion verified?** | Passive evidence ledger + policy nudge. Near-zero cost. Never blocks. | Adversarial skeptic panel, N subagents, majority vote. Expensive. Decides. | These compose rather than compete — the ledger makes the panel cheaper and the panel makes the ledger binding |
| **When is compaction paid for?** | Per turn (micro-compaction), **off by default because it breaks the cache prefix** | Background prefire before the threshold, prefix preserved | Grok Build's answer looks strictly better; Hermes documents why theirs is not the default |
| **Auxiliary model choice** | Same model, to reuse the prefix cache | Different models per skeptic, for judgement diversity | Task-dependent: transcript-replaying forks want the cache; independent judges want independence |
| **Security perimeter** | Command-shaped guards + approval flow + terminal blocks | Deep shell analysis (20k lines) + OS sandbox + folder trust | Our ADR-0006 sits closer to neither; see the Grok Build teardown §11 |
| **Self-improvement scope** | Skills and memories, provenance-scoped, human-pinnable | Not present — no self-modification loop at all | Grok Build's absence is itself a data point about where the frontier team spent its effort |
| **Language and shape** | Python, 779k lines, god-files at the core | Rust, 1.5M lines, god-crates at the core | Both cores unfactored. Neither language prevented it |

---

# Part D — what not to copy

**God-files.** `gateway/run.py` at 26,877 lines and `cli.py` at 18,485 are worse than Grok Build's
`xai-grok-shell` because Python offers no crate boundary to at least separate concerns. Both
projects arrived here, which suggests it is the default outcome absent a mechanical limit rather
than an enforced one. Our `docs_budget.py` ratchet is the existing precedent for a mechanical
limit in this repo, and the analogous check for source files is cheap to add at M0.

**`HERMES_*` environment variables.** `AGENTS.md` explicitly rejects them for non-secret config —
"`.env` is for secrets only… All behavioral settings go in `config.yaml`" — and the codebase is
full of them anyway (`HERMES_VERIFY_ON_STOP`, `HERMES_BACKGROUND_NOTIFICATIONS`, `HERMES_HOME`,
`HERMES_AGENT_REPO`, `GROK_*`'s counterparts). A stated policy without a CI check is a suggestion.
For a project whose central claim is reproducible measurement, the rule should be: *any knob that
can change a result appears in the run manifest, and a test proves it.*

**The `.env.example` at 24 KB and `cli-config.yaml.example` at 90 KB.** Configuration surface that
large is not configurable in any useful sense; it is a museum of options.

**Waiving the baseline gate.** The self-evolution runner prints "Baseline skill has constraint
violations — proceeding anyway" and continues. A gate that can be waived by a warning is not a
gate. Our loud-stub doctrine and "every gate ships with a test proving it can fail" both bear on
this.

**Reporting a delta as a result.** Covered in §15. It is the single most consequential thing to
*not* copy.

---

# Part E — open questions this teardown raises

1. **Do we build the evidence ledger, the gate, and the panel — or pick two?** §6.3 argues they
   compose at three price points. But three verification mechanisms is also three things to
   maintain and three places for a bug to hide the truth. My reading is that the ledger is close
   to free and makes the other two better, but that is an argument, not a measurement.
2. **What is our objective metric for the meta-loop, and how does it differ from our acceptance
   metric?** §15 says they must differ. Naming both is a real design task and it gates M5.
3. **Do we mine external session history for eval data?** The cold-start argument is strong and we
   have the same problem. The secret-detection and consent implications are real, and the answer
   probably differs between our own development traces and anything a user might run.
4. **Where does the profile seam live?** P46 proposes a resolved, immutable `RunProfile`. If we
   want one, it has to exist before the system-prompt assembler, the toolset selector and the
   model router are written — which is M0/M1a, not later.
5. **Is `--now` / deferred activation a per-command flag or a system-wide property?** Hermes makes
   it per-command. Making it a property of the *port* (any operation that mutates the stable
   prefix is deferred unless explicitly forced) is stricter and probably cheaper to enforce.

---

## 17. Provenance

Everything in this document was derived by reading `src/hermes_agent/` and
`src/hermes_self_evolution/`, both MIT-licensed, © Nous Research. No code was copied, adapted, or
transcribed. Quoted fragments are short excerpts from docstrings, `AGENTS.md`, `PLAN.md` and
`docs/micro-compaction.md`, reproduced to describe a mechanism and attributed inline. Where a
mechanism is recommended for consideration, the recommendation is of the *concept*; any AETHER
implementation would be written from the description.

Two dependency notes for the review: **DSPy and GEPA are MIT** and could be used directly if we
chose to; **Darwinian Evolver is AGPL v3**, and Hermes' own handling — external CLI only, never
imported — is the pattern to follow if it is ever considered.

**Cross-references:** [`rewrite_v300_grokbuild_teardown.md`](rewrite_v300_grokbuild_teardown.md) ·
[`rewrite_v300_grokbuild_proposals.md`](rewrite_v300_grokbuild_proposals.md) ·
[`rewrite_v300_reference_teardowns.md`](rewrite_v300_reference_teardowns.md) ·
[`rewrite_v300_measurement_strategy.md`](rewrite_v300_measurement_strategy.md) ·
[`rewrite_v300_autonomia_agi.md`](rewrite_v300_autonomia_agi.md) ·
[`rewrite_v300_contexto_memoria.md`](rewrite_v300_contexto_memoria.md) ·
[`rewrite_v300_mecanismo_edicao.md`](rewrite_v300_mecanismo_edicao.md) ·
[`rewrite_v300_seguranca_sandbox.md`](rewrite_v300_seguranca_sandbox.md) ·
[`rewrite_v300_decisoes_adr.md`](rewrite_v300_decisoes_adr.md)
