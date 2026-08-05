---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Long-Horizon Autonomy and the Path to Self-Improvement

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Answers RFP [§4-E](../reviews/review_project_rewrite_v300.md).

---

## 0. The ladder, and where the discipline lives

| Level | Name | Phase |
| :--- | :--- | :--- |
| L0 | Raw model call | Baseline for lift measurement |
| L1 | **Harness engineering** — tools, sandbox, retrieval, gates | 1 |
| L2 | **Loop engineering** — plan → generate → verify → repair; S1/S2 escalation | 1–2 |
| L3 | **Meta-loop (RHI)** — the harness optimizes itself against a noise floor | 3 |
| L4 | **Multi-agent swarm** — harnesses delegating to harnesses | 4, gated on L1–L3 measured |

Two rules govern the whole ladder, and everything below is an application of them:

- **Bounded self-improvement.** The meta-loop may optimize prompts, routing, skills, and tool
  schemas. It may never touch the [TCB](./rewrite_v300_seguranca_sandbox.md) — policy, evaluator,
  gates, benchmark definitions, CI. Without that boundary, the loop's most efficient strategy is to
  weaken the thing that judges it.
- **Triggers, not calendars.** Every `research`-tier capability here is gated on an empirical
  condition. A learned component starved of data underperforms the heuristic it replaced, and
  shipping it on a date guarantees exactly that.

---

## 1. Durable hibernation

**Target T5: ≥ 8 hours unattended, resumable across process death.**

The distinction that makes this achievable is small and easy to miss: hibernation is **durable
absence**, not a long-running process. The correct behavior on a rate-limit drought, a spot
preemption, or a machine reboot is to freeze every run and *exit the process*. A design that keeps a
process alive for eight hours has not solved the problem — it has narrowed the failure window.

### What `FrozenRunState` carries

| Carried | Not carried |
| :--- | :--- |
| Transcript position, plan, open files, taint state | **Grants** — re-minted on thaw under current policy |
| Worktree ref and base commit | Live objects, file handles, sockets |
| Cost and budget consumed so far | Anything non-serializable |
| Repair attempt count and progress signature | |

The grant exclusion is enforced by reflection
(`test_port_shape.py::test_no_grant_in_frozen_run_state`), not by review. A frozen run is inert data;
it cannot carry authority across a reboot.

### Erlang-shaped supervision

`agi_evolution_path.md` gets this right: **restart, don't repair**. One kernel per story. A run that
fails is frozen and restarted from a known state rather than patched in place, because in-place
recovery requires enumerating failure modes and freeze/thaw requires only that state be serializable.

### The failure-disposition ladder

`next_gen_architecture_specs.md` §2.1, carried forward. Each rung consumes budget:

```
rehydrate → replan → escalate (S1 → S2) → checkpoint + abort
```

A repair that fails the same gate twice should not attempt a third identical repair — it should change
strategy. Which rung fires is config; the ladder itself is an ablation target. Detail in
[the edit mechanism §1.2](./rewrite_v300_mecanismo_edicao.md).

### Budget: the supported channel, and the trap

Long-horizon runs need budget awareness, and there are two ways to give it — one supported, one
harmful.

**Supported:** the provider-native task budget — a token ceiling for a full agentic loop that the
model is *aware of* and paces against, distinct from `max_tokens` (an enforced per-response cap the
model never sees). Minimum 20,000 tokens.

**Harmful:** rendering a remaining-token countdown into the prompt yourself. Frontier models can
respond to a visible budget countdown with premature wrap-up — suggesting a fresh session, trimming
their own work, declaring done early. The harness therefore **does not** put budget counters in the
context; it uses the native mechanism or nothing.

This distinction is the kind of thing that costs a week to rediscover, so it is recorded here rather
than left as folklore.

---

## 2. Skills — the closed learning loop

Hermes' differentiating capability, and the one AETHER most wants: agent-authored, versioned procedure
files, created after complex tasks and refined during use (`skills/`, `agent/skill_bundles.py`,
`skill_preprocessing.py`, `learn_prompt.py`).

| Property | Decision |
| :--- | :--- |
| Format | Open `agentskills.io`-compatible; a skill is a directory with a description plus files |
| Loading | Progressive disclosure — the description sits in context; the body is read when the task calls for it |
| Authorship | Agent-authored, human-reviewable, versioned in git |
| Placement | The memory/skills layer of the [cache-stable prefix](./rewrite_v300_contexto_memoria.md) — resolved at composition, frozen for the run |
| Acceptance | A new or edited skill is accepted only when an ablation shows it beats the noise floor |

**The acceptance gate is what separates this from prompt accretion.** An agent that writes a skill
after every task produces a corpus that grows monotonically and helps unmeasurably. The gate makes
skills a measured mechanism rather than a hopeful one, and it is the reason skills sit at `growth`
rather than `core`.

### 2.1 The corpus needs a curator, not just a gate

An acceptance gate controls what *enters*. It does nothing about what is already in and has gone
stale — and [context & memory §5.3](./rewrite_v300_contexto_memoria.md) shows why that matters: past
roughly 150 always-on rules, adherence to *all* of them degrades. A growing skill corpus does not just
waste tokens; it quietly erodes compliance with everything else in the prefix.

`agent/curator.py` in `src/hermes_agent` supplies the missing half, and AETHER adopts its shape:

| Property | Mechanism |
| :--- | :--- |
| **Inactivity-triggered, no daemon** | Runs when the agent is idle *and* the last run is older than an interval. Maintenance costs nothing during active work and needs no separate scheduler to supervise — which, per [security §3.4](./rewrite_v300_seguranca_sandbox.md), is also one fewer scheduler to guard |
| **Runs as a forked review agent** | Same fork-and-review pattern as §2.2, on the skill store rather than one turn |
| **Lifecycle states, derived** | Skills auto-transition on activity timestamps — active, stale, archived — rather than being managed by hand |
| **Consolidation is a first-class outcome** | Alongside pin, archive, and patch. The corpus can get **smaller and denser**, not merely shorter, and a consolidated skill records where its content went |

Consolidation is the row that matters. Archival alone produces a corpus that oscillates — write, archive,
re-write the same lesson next month. Merging two overlapping skills into one preserves the knowledge
while reducing the always-on surface, which is the only move that improves both axes at once.

### 2.2 Writing memory without paying for it — the cache-sharing fork

**When** an agent writes memory is an unsolved question in AETHER's design so far. In-loop writes cost
tokens on the critical path and pollute the transcript; never writing means no learning.

`agent/background_review.py` answers it: after a turn, fork the agent into a background thread, replay
a conversation snapshot, and ask *"should any skill or memory be saved or updated?"*. Writes go
straight to the memory and skill stores.

Two properties make it nearly free, and both are load-bearing:

- **The main conversation and the prompt cache are never touched.** The review is a side branch; the
  primary transcript does not carry it.
- **The fork inherits the parent's live runtime** — provider, model, base URL, credentials, and the
  cached system prompt — **so it hits the same prefix cache.** The review pays a cheap tail on an
  already-warm prefix instead of a cold write.

That second point is the "fork operations must reuse the parent's exact prefix" rule from
[context & cache §1](./rewrite_v300_contexto_memoria.md), and it generalizes past memory: **any
auxiliary model call AETHER makes about a run — the compaction summarizer, the Best-of-N judge, a
review pass — should be built on the parent's prefix rather than assembling its own.** Stated as a
design rule, that is one of the higher-leverage cost decisions in the system, and it is invisible
unless cache hit rate is a tracked metric.

---

## 3. Code-mode tool orchestration

The agent writes a script that calls tools via RPC, collapsing an N-round-trip pipeline into one
context-cheap turn. Both primary references implement it — Hermes as RPC tool scripts, Codex as four
crates (`code-mode`, `code-mode-host`, `code-mode-protocol`, `code-mode-runtime`) — which is strong
evidence the pattern is real rather than a local optimization.

Why it matters here specifically: each tool round-trip appends blocks to the transcript, consumes
cache-lookback budget, and costs a full model turn. A ten-call pipeline collapsed to one script is
roughly a tenfold reduction in that overhead, and the intermediate results never enter the context at
all.

**Security posture is unchanged.** The script runs inside the perimeter; every RPC it makes is an
effect and goes through the same choke point with the same grants. Code mode changes *who composes*
the calls, not *what authorizes* them. Anything else would be a bypass, which is precisely what §1
of the security spec exists to prevent.

**Tool synthesis** — the agent detecting a repeated pattern and generating its own tool — is the
natural extension and stays `research`. Trigger: a measurable rate of repeated call sequences in the
trajectory corpus. Any synthesized tool enters through the same registry, with an effect class and a
grant requirement; it is not a new authority path.

---

## 4. Trajectory export (SFT / DPO)

SAGIHA's `outer_loop/export/` (411 LOC) ports directly, and the parts worth keeping are the parts
people skip:

| Stage | Purpose |
| :--- | :--- |
| Eligibility | Only trajectories meeting quality and provenance criteria |
| Redaction | Secrets and PII removed before anything leaves the boundary |
| License check | Repository licenses permit derivative dataset use |
| Schema | Stable, versioned export format |

DPO pairs come free from the architecture: Best-of-N already produces a scored set of candidates over
an identical prompt, which is the exact shape a preference dataset needs. The mechanism that exists to
improve resolve rate also produces the training data — worth noting because it means the exporter is
nearly zero marginal cost once BoN exists.

The corpus is also the **trigger source** for several `research` items: the learned candidate scorer
(§6) and tool synthesis (§3) both wait on it being large enough to beat their heuristic baselines.

**A caveat on what the corpus is good for.** Exporting trajectories invites the assumption that
fine-tuning is the destination. For *teaching a model facts*, it frequently is not: fine-tuning runs
into the **reversal curse** — a model tuned on "A is B" often cannot answer "what is B", despite the
logical symmetry — while keeping the fact as retrievable text sidesteps the problem entirely. Two
independent Stanford courses converge on this when advising teams choosing between the approaches.

The consequence for AETHER: the trajectory corpus's primary value is **behavioral** — preference data
for how to act, ablation evidence, and the trigger source above — not as a substitute for retrieval.
Knowledge belongs in the index and the memory store, where it can be updated, invalidated, and
audited. That is also why [long-term memory](./rewrite_v300_contexto_memoria.md) is bi-temporal: a
fact that goes stale needs to be correctable, and a weight update is not.

---

## 5. The meta-loop (RHI)

Offline optimization of the harness from its own trajectory corpus.

### The mutable surface

Hermes' self-evolution repo partitions this well —
`evolution/{prompts, skills, code, tools, core, monitor}`, four separately evolvable targets rather
than one "improve the agent" objective. AETHER adopts the partition with one addition Hermes does not
appear to enforce: **the evolvable surface is defined by exclusion from the TCB.**

| Mutable | Immutable |
| :--- | :--- |
| System prompts and tool descriptions | Policy engine, dispatch |
| Model routing (role → tier bindings) | Evaluator and gate definitions |
| Skills | Benchmark definitions |
| Tool schemas (not effect classes) | `.importlinter`, CI workflows |
| Retrieval and compaction parameters | Effect classes and grant requirements |

### Acceptance

A mutation is accepted only when its lift **beats a measured A/A noise floor** with a confidence
interval that excludes it. `e0/statistics.py` — exact McNemar, Holm–Bonferroni correction, seeded
bootstrap, pure stdlib — is the machinery, and it ports verbatim. Rejected mutations are recorded;
the rejection log is as much a product as the acceptance log, because it is what prevents the same
idea being re-proposed every cycle.

Target **T9**: more than zero accepted mutations that beat the noise floor, with **zero TCB
modifications admitted**. The second half is the real test.

DSPy/GEPA (per `hermes-agent-self-evolution`) is the candidate optimizer, deferred — `planning_future_sprints.md`
§3 already places prompt evolution at S13, and it needs a corpus that does not yet exist.

---

## 6. Learned candidate scoring

A surrogate reward model ranking rollouts before expensive verification. `research` tier.

**Trigger:** a labeled rollout corpus large enough that the learned scorer beats
rank-by-tests-passed on held-out data. Not a date.

**Hard constraint:** a learned scorer may `rank()`; it may never `admit()`. Type-level separation,
invariant I9. A proxy that can admit is a gate, and a learned gate is an unmeasurable one.

SAGIHA's `aoi/` package — a docstring and nothing else — is the cautionary artifact here. It was
listed as a capability in planning documents while being an empty directory. AETHER's `research` tier
exists so that a capability's status is honest: not started, trigger not fired, no pretense otherwise.

---

## 7. Multi-agent topology

Delegation is the capability most likely to be built on a wrong assumption, so the constraints are
stated before the mechanism.

### 7.1 Sub-agents: depth 1, and context is never inherited

**Depth is capped at one level.** Production systems that ship sub-agents enforce this rather than
recommend it, for four reasons that all compound: recursive spawning has no natural bound; each level
accumulates its own context; multi-level agent chains are effectively undebuggable; and nested
delegation makes token cost unpredictable — which is fatal for a system with a
[budget governor](#1-durable-hibernation). AETHER enforces depth 1 at the registry: a sub-agent's tool
set does not include the delegation tool.

**Context is never inherited automatically — and this is the most common multi-agent design error.**
The dominant production topology is hub-and-spoke: one coordinator holds the full picture, N workers
each receive *only their task string*. Worker B knows nothing of Worker A's findings unless the
coordinator puts them in B's task description.

```
              COORDINATOR  ── decomposes · passes context explicitly
              ·  aggregates results · resolves conflicts
               │        │        │
          WORKER A  WORKER B  WORKER C      ← isolated; task string only
               └────────┴────────┘
                results flow back to the coordinator only
```

The design consequence is that **the coordinator's context-passing is a first-class mechanism**, not
an implementation detail — what it forwards, and how it compresses A's findings into B's task, is
where multi-agent runs succeed or fail. It is also an ablation target, because "pass more" and "pass
less" both have failure modes.

This interacts with [§1](#1-durable-hibernation)'s security posture: a sub-agent gets a **scoped tool
registry and its own budget**, and delegation must never widen authority. Isolation of context and
isolation of capability are the same boundary seen twice.

### 7.2 Team size is a context-pressure decision, not a parallelism decision

Reported field experience converges on **>5 concurrent agents costing more in coordination than they
return in throughput** — with a large exception that explains the whole tradeoff.

A single agent on a 50K+ LOC codebase can spend 80–90% of its window merely loading relevant files,
leaving almost nothing for reasoning. Splitting across agents keeps each near ~40% utilization and
restores headroom. So the real question is **not "how many agents?" but "is coordination overhead
cheaper than context overflow?"**

| Situation | Reading |
| :--- | :--- |
| Independent modules, zero shared state | More agents are close to free — there is no coordination to pay for |
| Agents repeatedly reading each other's output or touching shared files | More agents actively hurt — merge conflicts and coordination messages consume the context the split was meant to save |
| Codebase cannot fit one agent's window with room to reason | Split regardless of coordination cost |

For AETHER this maps onto an existing distinction rather than a new one: Best-of-N candidates are the
*zero-shared-state* case (isolated worktrees, no cross-talk, results compared by the evaluator), while
collaborative decomposition is the *shared-state* case and carries the coordination tax. The two
should not share a concurrency setting.

Two further field observations, recorded because they cut against the intuitive design:

- Reported adoption data shows success rates climbing with **process maturity** (pilot 60–70% →
  production 85–90%), gated on modular architecture and strong test coverage. Weak tests are named as
  a blocker, which is consistent with this project's position that the evaluator is load-bearing.
- The anti-pattern list is short and specific: too many agents, over-delegation, and **automating a
  workflow that was never mastered manually**. The last one is the one a harness project is most
  likely to commit.

---

## 8. Scheduling and the Conductor (System 3)

### Scheduling — `growth`

Cron-driven autonomous missions with delivery to external channels. Hermes'
`cron/{scheduler,jobs,executions,lifecycle_guard}.py` is the reference; the lifecycle guard is the
part that matters, because an unsupervised scheduler that can start runs faster than they finish is
a budget incinerator with a clock.

### The Conductor — Phase 4, and deliberately constrained

`agi_evolution_path.md` contains the single best sentence in the corpus on this subject:

> *"The Conductor is a pilot and a scheduler; it is never an executor."*

It owns **time, attention and knowledge**. It owns **no tools, no shell, no grants**. Every effect it
causes is a `TaskSpec` submitted through the `Orchestrator` port. It is structurally incapable of
violating the security model because it holds none of the objects the security model protects.

Three structural facts carried forward:

1. **One port down.** The Conductor reaches the kernel through exactly one interface.
2. **One kernel per story.** Erlang-shaped supervision; restart via `FrozenRunState`.
3. **Governance federates upward, authority never does.** A fleet governor may refuse to *start* a
   run; it can never authorize a tool call.

And one **rejection** worth preserving: the same document declines a Conductor-resident dual-process
engine, on the grounds that *"a DAG of hypotheses at depth >1 is MCTS re-entering through the side
door — ADR-0005's cost analysis is not voided by renaming the tree."* System 1 (ReAct) and System 2
(Best-of-N + repair) already live in the kernel. The Conductor adds a third **timescale**, not a
second engine.

Lives in a separate package with an import-linter contract restricting it to ports and domain only —
so the constraint is mechanical, not aspirational.

---

## 9. Summary

| Capability | Tier | Trigger / gate |
| :--- | :--- | :--- |
| Durable hibernation | core | T5: ≥8h unattended, resumable across process death |
| Grants re-minted, never restored | core | Reflection contract |
| Disposition ladder | core | Per-rung ablation |
| Native task budget; **no countdown in the prompt** | core | — |
| Agent-authored skills | growth | Ablation beating the noise floor |
| Skill curator (archive / consolidate) | growth | Corpus size tracked against adherence |
| Background review fork on the parent's prefix | growth | Cache hit rate confirms the fork is warm |
| Code-mode RPC orchestration | growth | Round-trip cost measured on real traces |
| Trajectory export (SFT/DPO) | growth | Behavioral data, not a knowledge substitute (reversal curse) |
| Sub-agent delegation, depth 1 | growth | Enforced at the registry — no delegation tool in a sub-agent's set |
| Explicit coordinator context passing | growth | Ablation: what to forward, and how compressed |
| Concurrency: BoN vs. collaborative | core / growth | Separate settings — zero-shared-state vs. coordination-taxed |
| Meta-loop (RHI) | growth | T9: >0 accepted mutations, **zero** TCB modifications |
| Tool synthesis | research | Measurable rate of repeated call sequences |
| Learned candidate scorer | research | Beats rank-by-tests-passed on held-out data |
| Scheduling | growth | — |
| Conductor (System 3) | Phase 4 | L1–L3 measured first |

The ordering is the argument. Every row above the `research` line has a mechanism that can be built
and measured today; every row below it has a trigger instead of a date. A project that inverts this —
building the learned components first because they are the interesting ones — produces components
whose value cannot be established, which is the failure the predecessor documented at its own expense.
