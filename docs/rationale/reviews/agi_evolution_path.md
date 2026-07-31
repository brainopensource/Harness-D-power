---
status: historical
retrieval: excluded
---
# AGI EVOLUTION PATH SPEC — The Conductor Layer over SAGIHA

**Status:** Proposed architecture. Builds on, and never restates, the accepted stack: `NEXT_GEN_HARNESS_ARCHITECTURE_SPEC.md` (v2 Spec), `further_improvements.md` (amendments A1–A3, R1–R3), and `CODEBASE_DELTA_AND_REFACTOR_PLAN.md` (delta plan, findings H1–H4). Cross-references use `(Spec §x)`, `(FI §x)`, `(Delta §x)`.
**Naming note:** the task brief expands SAGIHA as "Autonomous Evolvable Task Harness & Execution Runtime"; ADR-0001 binds it as **Super AGI Harness Agent**. This document follows the ADR. The new layer specified here is the **Conductor**.

---

## 1. Executive Vision & Architectural Philosophy

### 1.1 The claim, stated falsifiably

This document does not specify "an AGI." It specifies the layer that converts SAGIHA — a single-task, gate-verified execution engine — into a **long-horizon, multi-regime autonomy system**, and it inherits the tree's founding epistemics: every capability claim below is a benchmark with a threshold, or it does not ship. The measurable definition of success for the Conductor is:

> Given a *mission* (a multi-day, under-specified engineering or research objective), the system completes it at a measured **mission resolution rate**, with a measured **human-interventions-per-mission** count, at a measured **cost-per-resolved-story**, on a pinned mission suite, judged against an A/A noise floor.

Anything called "AGI-level" that cannot be phrased that way is marketing, and the tree already has a rule for numbers it cannot defend.

### 1.2 The one architectural sentence

**The Conductor is a pilot and a scheduler; it is never an executor.** It owns time (days, hibernation, resumption), attention (which story runs, in which regime, with which budget), and knowledge (the memory graph, the skill library, the distillation pipeline). It owns **no tools, no shell, no grants**. Every effect it wants performed is a `TaskSpec` submitted to a SAGIHA kernel through the `Orchestrator` port, executed under that kernel's `PolicyEngine`, choke point, gates, and taint discipline — unchanged, unbypassed, and unaware that anything sits above it. This is Integration Invariant 1 taken literally: SAGIHA remains a standalone engine, and the Conductor is structurally incapable of violating its security model because it holds none of the objects that could.

The corollary that shapes everything below: **the Conductor adds a third cognitive timescale, not a second cognitive engine.** SAGIHA already contains System 1 (ReAct) and System 2 (best-of-N + sequential repair). Area A of the brief, as written, would re-implement both one level up — evaluated and rejected in §4.1. What the stack lacks is **System 3**: strategic deliberation over missions, roadmaps, resource allocation, and knowledge consolidation, operating on the timescale of hours-to-weeks where S1/S2 operate on seconds-to-minutes.

### 1.3 What is deliberately not built

Consistent with boring-components-first and trigger-not-calendar doctrine: no swarm framework (Mode C is a *server* for external swarms, not a swarm engine); no learned mission planner before a hand-written one has generated labels; no continuous background cognition (every Conductor wake is a scheduled or event-driven, logged, budgeted act); no new database daemons (SQLite-WAL throughout, per the existing storage doctrine); no in-context "agent society" role-play — one Conductor, N kernels, typed contracts between them.

---

## 2. System Topology & Layer Decomposition

### 2.1 Topology

```
┌────────────────────────── PILOTS (thin, replaceable) ─────────────────────────┐
│  Mode B: TUI / IDE-MCP        Mode C: Clawdbot · Moltbot · A2A remote nodes   │
│  (streaming, interrupt)       (chat-ops / swarm delegation → A2A protocol)    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │ MissionSpec / steer / approve  │ A2A: TaskSpec + budget + grant-subset
                ▼                               ▼
┌───────────────────────────── CONDUCTOR (System 3) ────────────────────────────┐
│  MissionPlanner        → MissionSpec → EpicDAG → StoryDAG (Spec §3)           │
│  Scheduler             → wake/hibernate cadence, FrozenRunState (FI §A3)      │
│  FleetGovernor         → global admission over per-kernel ResourceGovernors   │
│  KnowledgeEngine       → A-MEM graph, consolidation, AGENTS.md gen  (§5)      │
│  SkillCompiler         → trace → tool candidate → gated registration (§6)     │
│  DistillationPipeline  → SFT/DPO export → Tier-4 promotion gate     (§6.3)    │
│  ── owns: time, attention, knowledge. owns NOT: tools, grants, shells ──      │
└───────────────┬───────────────────────────────────────────────────────────────┘
                │ Orchestrator port only:  execute(TaskSpec, RunContext)
                │ → AsyncIterator[Event] → GateReport          (identical local/A2A)
                ▼
┌──────────────── SAGIHA KERNEL POOL (one kernel per active story) ─────────────┐
│  Kernel · PolicyEngine · dispatch choke point · DMARTIC S1/S2 · Gates ·       │
│  Worktrees · Sandbox (B5a) · TrajectoryStore · taint (FI §R1) — UNCHANGED     │
└────────────────────────────────────────────────────────────────────────────────┘
```

Three structural facts carry the design:

1. **One port down.** The Conductor's entire downward surface is the existing `Orchestrator` Protocol (`execute(TaskSpec, RunContext) -> AsyncIterator[Event]` terminating in a `GateReport`). Local kernel and remote A2A node are the same contract over two transports (Spec §3.2) — which is what makes the kernel pool elastically hybrid: story 3 can run on the local machine while story 7 runs on a remote gVisor host, and the Conductor cannot tell the difference except through the `FleetGovernor`'s cost ledger.
2. **One kernel per active story.** Kernels are cheap (a composition-root call over a worktree) and disposable. Isolation between concurrent stories is therefore process/worktree isolation — the property Block 3's parallel candidates already require — not in-context juggling. A crashed or wedged kernel is killed and its story rescheduled from the last `FrozenRunState`; the Conductor's supervision model is Erlang-shaped (restart, don't repair) because every kernel is resumable by construction (Delta §2.10, `FrozenRunState`).
3. **Governance federates upward, authority never does.** The `FleetGovernor` allocates budget slices and concurrency to kernels and can *refuse to start* a run; it cannot authorize a tool call — only each kernel's own `PolicyEngine` can. Grant monotonicity (Integration Invariant 2) is thereby preserved without new mechanism: the Conductor never holds a grant, so there is nothing for it to widen, serialize, or leak. A2A-delegated missions arrive with a budget + grant-subset envelope that the *receiving* kernel's policy narrows further, exactly as Spec §3.2 fixed.

### 2.2 Mode decomposition — three regimes, one core

The Modes are pilots, not architectures ("One Core, Many Cockpits" extended one level). Every mode reduces to the same three verbs against the Conductor's API: `submit(MissionSpec) -> mission_id`, `steer(mission_id, SteerEvent)`, `observe(mission_id) -> AsyncIterator[Event]`.

**Mode A — Autonomous long-horizon worker.** A cron- or trigger-scheduled Conductor process. The mission loop (§4.2) runs stories through kernels, hibernates between scheduling quanta by freezing every active run (`FrozenRunState`, grants absent by design) and *exiting the process* — hibernation is not sleep, it is durable absence, which is what makes weeks-long missions survive host reboots, rate-limit droughts, and spot-instance preemption for free. Rate-limit handling composes from what exists: the kernel-level Provider Degradation Policy (FI §A2) handles per-call throttling; when a provider is exhausted beyond the retry budget, the kernel freezes and the Conductor's scheduler reschedules the story after the provider's stated recovery window — a calendar decision, hence System-3 property.

**Mode B — Human-piloted, interactive.** The B5c streaming TUI/IDE surface, piloting a Conductor with a one-story roadmap (degenerate mission). Interrupt-and-steer mechanics are specified in §4.3 because they are cognitive-engine mechanics, not UI; the pilot only renders events and transmits `SteerEvent`s.

**Mode C — AI-piloted (Clawdbot / Moltbot / A2A).** External orchestrators are *upward* A2A: they call the Conductor with the same contract the Conductor uses downward — `MissionSpec` (or bare `TaskSpec` for single-shot delegation) + budget + grant-subset, receiving the typed event stream. Chat-ops bots (Clawdbot/Moltbot) are adapters that translate conversational intent into `MissionSpec` and route `request_approval` events back to the originating channel — the durable, deny-on-timeout approval semantics (and the mandatory pre-transmission state freeze, FI §R3) apply identically whether the approver is a human in a TUI or a human behind a Telegram bot. **What Mode C is not:** the Conductor does not implement the external swarm's coordination logic, does not accept instructions from swarm *peers* mid-run (only from its delegator, on the authenticated channel the mission arrived on), and treats any tool-visible content from other agents as `EXTERNAL` provenance — swarm traffic is the injection surface T1 warned about, wearing a colleague's face.

---

## 3. Domain Model Extensions (additive, one file)

`src/sagiha_conductor/domain/mission.py` — the Conductor is a **separate package** depending on `sagiha`'s ports/domain only (enforced by a new import-linter contract: `sagiha_conductor` may import `sagiha.ports`, `sagiha.domain`, nothing else from the engine — the hot-swap seam made mechanical).

```python
class MissionSpec(BaseModel):        # frozen; amended by revision like TaskSpec
    mission_id: str
    revision: int = 0
    objective: str                    # the under-specified human intent, verbatim
    constraints: tuple[str, ...]      # budget ceilings, deadlines, non-goals
    acceptance: tuple[AcceptanceCriterion, ...]   # mission-level, machine-checkable where possible
    mode: Literal["autonomous", "piloted", "delegated"]
    budget: MissionBudget             # usd, wall-clock, max human interventions

class EpicDAG(BaseModel):             # MissionSpec → Epics; Epic → StoryDAG (Spec §3.1, unchanged)
    epics: dict[str, EpicSpec]
    deps: frozenset[tuple[str, str]]

class MissionState(BaseModel):        # the Conductor's FrozenRunState analogue
    mission_id: str
    roadmap: EpicDAG
    story_states: dict[str, StoryStatus]        # pending|frozen(run_id)|admitted|returned|abandoned
    ledger: CostSummary                          # aggregated from kernel GateReports/events
    interventions: tuple[InterventionRecord, ...]
    knowledge_writes: tuple[str, ...]            # memory ids produced this mission (§5.4 audit trail)
```

`StoryDAG`, `StorySpec`, `IntegrationStep`, `ResolveConflictTask` are inherited unchanged from Spec §3.1 / FI §R2 — the mission layer decomposes one level above them (`objective → epics → stories`) using the same protocol shape (`WorkflowStep[In, Out]`) and the same E0 gating discipline: **the mission-planning stage itself does not ship unless an ablation shows mission-level planning beats feeding epics directly**, the ADR-0018 rule applied recursively.

---

## 4. Cognitive Engine Specification

### 4.1 Area A adjudicated: no second dual-process engine

The brief's Area A mechanism — "freeze the active loop, generate a DAG of hypotheses, execute parallel candidate branches, rank via independent judge" — is evaluated and **rejected in its proposed placement, accepted in a narrowed form inside SAGIHA where its ancestors already live**:

- *Rejected:* a Conductor-resident S1/S2 duplicates DMARTIC, creates a second escalation authority with no access to the gate signals that drive escalation (they are kernel-internal events), and its "DAG of hypotheses" at depth >1 is MCTS re-entering through the side door — ADR-0005's cost analysis (one expansion = full agent run + test suite) is not voided by renaming the tree.
- *Rejected:* "triggered on high entropy." Token-level entropy is unavailable or non-comparable across the provider set the tiering config actually binds (OpenAI-compatible endpoints expose it inconsistently; cassette replay exposes it never). Triggers must be deterministic and replayable: the existing ladder inputs (stuck signatures, `EditRejected×k`, gate-failure counts, budget burn-rate) already are. This is the cold-start doctrine again — hand-written trigger first, learned trigger when labels exist.
- *Accepted, narrowed:* **diagnosis-conditioned best-of-N.** Today's S2 proposes N *patches* from one implicit diagnosis. The upgrade: on escalation, one planning-role call produces k distinct *diagnoses* (structured `Hypothesis` records: suspected cause, discriminating evidence, candidate approach); best-of-N candidates are then seeded one-per-hypothesis rather than N-per-vibe. Depth stays 1, cost stays N runs, ADR-0005 stays intact — but candidate *diversity* is bought at the price of a single frontier call, which is exactly where the model-economics doc says quality is cheapest. The hypotheses are logged as typed events, giving the eventual PRM (FI §A1, stage S-2) diagnosis-labeled training data as a byproduct. Gate to ship: hypothesis-seeded BoN beats unseeded BoN on the pinned suite beyond the A/A floor; if it does not, the Hypothesis record stays (it is free telemetry) and the seeding does not.

### 4.2 System 3 — the mission loop

The Conductor's deliberation cycle, deliberately isomorphic to DMARTIC so operators reason about one loop shape at two scales:

```
PLAN      MissionSpec → EpicDAG → StoryDAG          (frontier role; revised, never mutated)
SCHEDULE  pick runnable stories: deps satisfied ∧ disjoint closures ∧ FleetGovernor admits
DISPATCH  story → TaskSpec → kernel.execute()        (the only downward verb)
OBSERVE   consume event streams; ledger costs; detect kernel-level abort signals
INTEGRATE admitted stories → IntegrationStep → rebase/gate/ResolveConflictTask (FI §R2)
REPLAN    on: story returned-to-board ×k · mission acceptance drift · budget slope
          exceeding projection · operator SteerEvent  — REPLAN revises the DAG,
          never restarts it: admitted stories are sunk assets, not discarded state
CONSOLIDATE at mission checkpoints: KnowledgeEngine ingestion (§5.3), skill
          candidates (§6), distillation export — the System-3 analogue of Self-Reflect
HIBERNATE freeze all active runs + MissionState; exit; wake on schedule/event
```

**The escalation ladder extends upward, monotonic across layers.** SAGIHA's recovery ladder (Spec §2.1.A) terminates at rung 4, checkpoint-and-abort. That rung is now defined as a *signal, not a failure*: the kernel emits `RunFailed(disposition=ABORT)`, the Conductor catches it and continues the ladder at rungs 5–7: **(5)** re-scope the story (decomposer re-runs against the conflict/failure report — the FI §R2 path generalized); **(6)** re-plan the epic (the failure invalidates a decomposition assumption); **(7)** surface to the human/delegator with the mission parked in `input-required`. No rung repeats; every transition is a `RecoveryEscalated` event; interventions-per-mission — the honesty metric for "autonomous" — is computed directly from rung-7 counts.

**Error budgets are System-3 objects.** Each story carries a spend/step/wall-clock slice minted by the `FleetGovernor` from `MissionBudget`; the kernel's own `ResourceGovernor` enforces it (H2 fix, Delta §2.2, is a hard prerequisite — a Conductor scheduling against fictional zero-cost telemetry would be a random-walk allocator). Burn-rate exceeding the planner's projection by a configured factor is a REPLAN trigger, not merely a cap: running out of budget is a scheduling failure that should have been foreseen one layer up.

### 4.3 Interrupt-and-steer without cache destruction (Mode B)

The brief's requirement — redirect reasoning mid-execution "without destroying prefix cache history" — is satisfiable *because of*, not despite, the cache-stability layout, and the mechanics fall out of structures that already exist:

1. **Interrupts land at exchange boundaries.** The loop checks a steer flag exactly where it checks compaction headroom: pre-assembly, never mid-turn (a mid-stream abort discards only the in-flight completion — the most that can ever be lost is one model call). Worst-case latency to a steerable state is one exchange; the B5c exit gate (<2s round-trip) binds it.
2. **Steering is a tail append.** A `SteerEvent` becomes an operator-provenance user message appended to layer 8. Layers 1–7 remain byte-identical; the entire prior tail remains cached; the turn costs only its own tokens. This is the whole trick, and it is only available because retrieval was ruled seed-only (Spec §2.1.B) — a design that refreshed layer 6 on "new information from the operator" would forfeit the tail cache on every steer.
3. **Re-scoping is a revision, not a rewrite.** If the steer changes the goal (not just the approach), the Conductor mints `TaskSpec(revision=n+1)`; acceptance criteria live in semi-stable layer 5, so the cache resets once at the layer-5 breakpoint — the same cost class as a compaction, paid deliberately, logged as such. The frozen prior run remains in the trajectory store as a first-class ancestor (`StepId.parent` spans revisions), preserving replay and the distillation pipeline's view of the full causal history.
4. **Pause is freeze.** An operator "pause" is `FrozenRunState` + process-idle, identical to Mode A hibernation — one mechanism, four consumers (FI §A3), now five.

---

## 5. Memory & Knowledge Engine (Area B, adjudicated and specified)

### 5.1 Adjudication

Area B is **accepted in structure, constrained in mechanism**. The existing memory doctrine survives contact intact: split code-graph/episodic stores (ADR-0011), deterministic auto-links only (Spec §5 — `record→files_touched`, `record→task_id`, `record→superseder`; the brief independently converged on the same rule, which is confirming), no LLM edge extraction, provenance never inherited across links, bi-temporality reserved for facts that age. What Area B genuinely adds — and what the audit flagged as the tier's failure risk (empty-net, W11) — is the **write side at scale**: a mission produces hundreds of trajectory events and zero curated knowledge unless something distills them. That something is Active Consolidation, and it is the component that needs adversarial specification, because a consolidation job is an LLM writing durable "truths" the future agent will trust.

### 5.2 The three stores + one library (schema)

| Store | Content | Source of truth | Write path | Index |
| :--- | :--- | :--- | :--- | :--- |
| **Code Graph** | imports, calls, ownership, co-change | Tree-sitter + git (exact) | indexer only, rebuildable from HEAD | SQLite → Kùzu on measured trigger |
| **Episodic Graph (A-MEM)** | `MemoryRecord` atomic notes: decisions, failure paths, preferences, consolidated guidelines | genuinely contested; bi-temporal | `remember` tool (grant-gated) + Consolidator (§5.3) | FTS5 + link traversal; dense behind ADR-0014's trigger |
| **Mission Ledger** | `MissionState`, intervention records, budget history | Conductor | Conductor only | SQLite |
| **Skill Library** | compiled skills (§6) | E0 measurements | SkillCompiler + human sign-off | name/description FTS for progressive disclosure |

`MemoryRecord` gains two fields (S2 port bump on `Memory`, batched with the already-flagged `neighbors`/`backlinks` addition so the tier pays one version bump, not two): `kind` extended with `"guideline"` (consolidated) and `confidence: float` — set *only* by the Consolidator from evidence counts, never asserted by the model; and `evidence: tuple[str, ...]` — the memory/trajectory ids a guideline was distilled from, making every consolidated claim auditable back to gate-verified runs.

### 5.3 Active Consolidation — the adversarial spec

A scheduled Tier-B job (same cost class as trace mining, Spec §2.3), never inline with execution:

1. **Ingest:** episodic records + trajectory summaries since the last consolidation checkpoint, *filtered to `tainted == False` sources* — a guideline distilled from an injection-window run is a laundered instruction with a halo (the FI §R1 monotonic-taint rule reaching into the knowledge tier).
2. **Cluster deterministically** (shared file-closures, shared task lineage, shared failure class from the error taxonomy) before any model sees anything — the LLM synthesizes within clusters, it does not decide what relates to what.
3. **Synthesize** candidate guidelines with mandatory `evidence` citations; a candidate citing fewer than `min_evidence` (default 3) distinct admitted runs is dropped mechanically.
4. **Invalidate honestly:** a new guideline contradicting an old one does not overwrite it — it links `supersedes → old_id`, the old record's `valid_to` closes, and backlink traversal marks dependents stale (the Knowledge Net's invalidation semantics, now with a producer). Contradiction detection is lexical + link-structural in v1; "the model decides what contradicts" is deferred until a labeled set exists to measure it.
5. **Land through review:** guidelines carry `provenance=HARNESS`; those promoted into the repository's `AGENTS.md` / `docs/decisions/` go through the existing approval-gated write path as a diff a human can read — repository-resident memory stays a pull request, not a database side-effect.

**`sagiha init` / dynamic AGENTS.md** (Delta plan #8) is this pipeline's cold-start mode: with zero episodic history, it synthesizes the seed AGENTS.md from the code graph + toolchain detection alone; thereafter, regeneration is consolidation output. One generator, two regimes.

**Recall discipline** (the half of memory design usually left unstated): consolidated guidelines with `confidence ≥ θ` enter prompt **layer 4** (stable prefix — they change per consolidation checkpoint, which is rarer than per task, so they are cache-compatible); everything else is reachable only through the agentic `recall` tool in the tail. Nothing else auto-injects — auto-injected memory is the token-bloat and laundering channel simultaneously. **Ship gate:** an E0 ablation must show memory-on beats memory-off on the pinned suite beyond the A/A floor. If accumulated memory does not measurably help, the correct response is to fix consolidation, not to ship a knowledge graph on vibes.

## 6. Skill Compilation & Distillation (Areas C & D)

### 6.1 Area C adjudicated

**Accepted, with three constraints that the naive Voyager-style design violates.** The failure modes of auto-grown skill libraries are documented and predictable: near-duplicate proliferation, skill rot as the codebase drifts, prompt-real-estate erosion (every registered tool taxes every call — the 20-tool budget exists for measured reasons), and — decisive here — **auto-registered agent-authored code is self-modification of the capability surface**, RHI's threat model wearing a productivity feature's clothes. Hence:

1. **Skills are not core tools.** They register into a namespaced library behind progressive disclosure: one core tool, `use_skill(name, args)`, plus FTS over skill descriptions surfaced in retrieved context — the prompt pays for one schema, not N. The 20-tool cap stands.
2. **Registration is gated like an RHI mutation, because it is one.** Pipeline: candidate extraction from admitted, taint-free, replay-verified trajectories (the §6.2 selector reused) → parameterization by a frontier-role call → **sandboxed conformance run** (the skill re-solves ≥m historical task instances inside a Podman/WASM sandbox with no network and read-only fixtures) → **E0 admission**: skill-on must beat skill-off on the relevant task class beyond the A/A floor → **human sign-off** to enter the registry. A skill is a measured asset or it is not a skill.
3. **Skills expire.** Each carries `last_validated_at` and re-runs its conformance set on a schedule or on code-graph invalidation of its file-closure (deterministic staleness signal — the co-change graph earning its keep); failure quarantines it out of disclosure. Rot is handled by the same mechanism that admitted the skill, not by hope.

Execution placement: a skill is a `ToolRegistry` entry whose handler runs *inside the sandbox perimeter* under an ordinary grant — the choke point, taint stamping (`trusted_output=False` until the skill's own output provenance is analyzed), and effect classification apply with zero new security machinery. Invariant 1 holds by construction.

### 6.2 Distillation pipeline

Fully specified at Spec §6 and unchanged: eligibility (`admitted ∧ replay-verified ∧ ¬tainted ∧ within-budget`), exact request reconstruction via replay machinery, SFT from admitted runs, DPO pairs from best-of-N siblings on identical prefixes, secret-redaction and license gates, provider-policy flag on reasoning-block export. The Conductor adds only *cadence and ownership*: export runs at mission CONSOLIDATE checkpoints, and mission-level structure enriches the labels (story class, hypothesis id from §4.1, escalation rung) — the columns a future router and PRM train on.

### 6.3 Tier-4 promotion gate (closing the loop honestly)

The brief's "reduce reliance on closed-source APIs over time" becomes a mechanism, not an aspiration: a fine-tuned Tier-4 checkpoint is promoted to the default `local`/`execution` binding **only** when it beats the incumbent Tier-4 on the pinned suite beyond the A/A floor at equal-or-better cost-per-resolved-task, under paired evaluation with k ≥ 3 — the RHI Tier-3 statistical gauntlet applied to the one mutation class (model weights) whose evaluation it can actually afford, since inference is local and marginal-cost-zero. Promotion is a config change through the composition root; the TCB is untouched. **This is the system's only honest "self-improvement" claim, and it is falsifiable per checkpoint.**

---

## 7. Prioritized Engineering Roadmap

Ordered by `(risk retired × capability delta) ÷ cost`; every phase names its exit gate; hard dependencies on the delta plan are explicit. Phases C0–C2 are buildable against today's engine; C3+ interleave with SAGIHA Blocks 3–5.

| # | Phase | Contents | Hard deps | Exit gate |
| :- | :--- | :--- | :--- | :--- |
| C0 | **Conductor skeleton + Mode A minimal** | `sagiha_conductor` package, `MissionSpec/MissionState`, single-story mission loop, hibernate/wake via `FrozenRunState`, import-linter seam contract | Delta §2.1 (H1), §2.2 (H2) — *no scheduling over fictional gates/costs*; `FrozenRunState` (Delta §2.10) | A 3-story sequential mission survives `kill -9` mid-story ×3 and completes with identical final `GateReport`s; ledger within 5% of provider-billed cost |
| C1 | **Mode B: interrupt-and-steer** | SteerEvent, exchange-boundary interrupt, revision-based re-scope, pause=freeze; minimal streaming TUI (B5c fragment pulled forward) | Compactor (Spec plan #1) — steering long runs without compaction hits the window | Interrupt→steerable <2s; steer turn shows tail-cache hit (cache_read_tokens ≥ prior tail); resumed-after-steer run replays |
| C2 | **Multi-story scheduling + FleetGovernor** | StoryDAG parallel dispatch over kernel pool, IntegrationStep + ResolveConflictTask, budget slicing, burn-rate REPLAN trigger | SAGIHA Block 3 (worktrees, BoN); Spec plan #9 ablation | 2-way parallel mission: planning-beats-no-planning ablation positive incl. integration; zero cross-story worktree/DB interference |
| C3 | **KnowledgeEngine v1** | Memory port S2 bump (links + `guideline`/`confidence`/`evidence`), Consolidator with taint filter + evidence floor, `sagiha init` cold-start mode, layer-4 guideline injection | Block 4 (FTS5, code graph); TaintGate (Delta §2.6) | memory-on beats memory-off beyond A/A floor; every guideline traces to ≥3 admitted runs; zero tainted-source guidelines in a seeded-injection canary mission |
| C4 | **Distillation cadence + Tier-4 promotion** | CONSOLIDATE-checkpoint export, mission-enriched labels, promotion gauntlet, first fine-tune cycle | Spec plan #4 (exporter); accumulated bench cassettes | One full cycle: export → train → candidate beats incumbent Tier-4 beyond floor at ≤ cost → promoted via config; or an honest negative result published to the ledger |
| C5 | **Mode C: A2A server + chat-ops pilots** | Conductor A2A surface, Clawdbot/Moltbot adapters, delegated grant-subset envelopes, approval routing w/ mandatory pre-transmission freeze (FI §R3) | SAGIHA B5a (sandbox — *delegated autonomy without the perimeter is refused at config*, extending the existing subprocess/autonomous refusal) | Remote delegated mission completes under a budget envelope it cannot exceed; injection canary from a swarm-peer message produces zero unapproved effects |
| C6 | **SkillCompiler** | extraction → parameterization → sandboxed conformance → E0 admission → signed registration → expiry/quarantine | C3 (staleness signal needs the code graph), C4 selector, B5a/b sandbox | First skill admitted through the full gauntlet measurably beats skill-off on its task class; a deliberately-rotted skill auto-quarantines |
| C7 | **Learned routing & mission planning** | escalation/diagnosis router trained on C0–C6 labels; hypothesis-seeded BoN (§4.1) if its gate passed | label volume threshold, PRM stage S-2 | learned router beats the hand-written ladder beyond floor — else the ladder stays, permanently and without embarrassment |

**De-prioritized, with triggers:** swarm *coordination* logic (trigger: a paying multi-agent deployment); MCTS (unchanged: calibrated PRM prerequisite); cross-mission memory sharing between distinct repositories (trigger: measured guideline transfer value; isolation is the default because cross-project laundering is T1 with extra steps); any Conductor-side model call not attributable to PLAN/REPLAN/CONSOLIDATE (System 3 must not become an idle-chatter tax).

---

## 8. Closing Position

The evolution path adds exactly one new idea — a third timescale with its own loop, its own state, and its own falsifiable metrics — and refuses the tempting rest: no second cognitive engine, no unmeasured memory, no self-registering capabilities, no authority above the choke point. Every Area from the brief survives in the form that respects the invariants: A narrowed to diagnosis-seeded search inside the engine that owns search; B accepted with a consolidation pipeline whose every durable claim carries evidence ids and a taint-free pedigree; C accepted as gated, expiring, sandbox-confined skills behind one tool schema; D inherited and completed with the promotion gauntlet that makes "the system improves itself" a per-checkpoint measurement. The system earns the word *autonomous* the way SAGIHA earned the word *verified*: one number at a time, against a noise floor, on a suite it cannot edit.
