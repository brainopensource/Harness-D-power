---
status: rationale
retrieval: excluded
updated: 2026-08-01
---

# Planning: Future Sprints (S8 → S16) — Benchmark Parity, Self-Improvement, and the Conductor

> Companion to `planning_final_sprint_rev2.md`, which closes v2-S1 → v2-S7. This document covers
> **everything after S7**: the harness mechanisms competitors have that we do not, the honest path
> to a top-tier benchmark number, and the architecture of the autonomous self-improving orchestrator
> the project exists to become.
>
> Sources adjudicated: `conceptual-design.md`, `harness_research_2026_briefing.md`,
> `ai_coding_agents_references_swe_terminal-benchs.md`. Where those documents recommend something
> we should *not* build, §3 says so and why — a plan that adopts every reference recommendation is
> not a plan.

---

## 1. Calibration: What "80%" Actually Means

This is the most important section in the document, because the target as stated is ambiguous
across three benchmarks that differ by ~25 points, and building toward the wrong one wastes a year.

From `ai_coding_agents_references_swe_terminal-benchs.md` §5:

| Benchmark | Top score | Who | 80% would rank us |
|---|---|---|---|
| **SWE-bench Verified** (500 tasks) | 92.4% | Claude Code CLI + Opus 5 | **~5th**, at DeepSeek V4 Pro / OpenHands level (80.6%) |
| **SWE-bench Pro** (2026, uncontaminated) | 79.2% | Claude Code CLI + Opus 5 | **#1 in the world** |
| **Terminal-Bench 2.1** | 83.4% | Codex CLI + GPT-5.5 | **~2nd**, just past Hermes+Kimi K3 (80.9%) |

Three consequences that shape every sprint below:

1. **80% on SWE-bench Verified is a realistic engineering target.** It is achievable with a
   frontier model plus the mechanisms in §2. It is also a *saturated* benchmark, contaminated
   across frontier models, and the reference doc explicitly recommends against it as a primary
   screen. Hitting 80% there proves the harness is competent; it does not prove it is good.

2. **80% on SWE-bench Pro would beat Anthropic's own flagship.** Treat this as a north star, not
   a sprint exit gate. Anyone planning to "hit 80% on Pro by S10" is planning to fail.

3. **Beating Hermes means Terminal-Bench, not SWE-bench.** Hermes' headline result is 80.9% on
   Terminal-Bench 2.1 with Kimi K3. Beating it requires the long-horizon shell mechanisms in
   S7g/S9, not better patch generation.

**Decided target set:**

| Sprint | Benchmark | Target | Rationale |
|---|---|---|---|
| S7 close | SWE-bench Lite (30) | ≥ 80% | Cheap signal that the loop converges |
| S9 | SWE-bench Verified (500) | ≥ 80% | The headline number, honestly measured |
| S11 | Terminal-Bench 2.1 | ≥ 80% | The Hermes comparison |
| S14 | SWE-bench Pro | ≥ 55% | Parity with top open-source (OpenHands+DeepSeek V4) |
| S16+ | SWE-bench Pro | ≥ 70% | Stretch; a genuine SOTA claim |

Every number published with N, k ≥ 3 repetitions, the A/A noise floor, a Holm-corrected p-value,
and the model id. **The measurement discipline is the moat.** Per the reference doc's own finding,
harness infrastructure accounts for 30-40% of resolution rate on identical models — which means an
honest ablation showing *our* harness delta is a more defensible claim than any leaderboard rank.

---

## 2. The Capability Gap: What Competitors Have That We Do Not

Derived from the reference docs, cross-checked against the tree. Ordered by score impact per unit
of effort.

| # | Mechanism | Who does it | Our state | Sprint |
|---|---|---|---|---|
| **1** | Test-feedback repair loop | Claude Code, OpenHands | **Missing** — gate is terminal | S7f (rev2) |
| **2** | Hierarchical localization before edit | Agentless, AutoCodeRover | Missing | **S8** |
| **3** | Repo map in prompt (Tree-sitter skeletons) | Aider | `get_skeleton` exists, unused in prompt | **S8** |
| **4** | Architect/Editor dual-model split | Aider (94.8% HumanEval) | Missing | **S8** |
| **5** | Spectrum-Based Fault Localization | AutoCodeRover | Missing | **S10** |
| **6** | Typed EventStream Action/Observation | OpenHands | Partial — bus exists, not a replayable stream | **S9** |
| **7** | Background/long-running shell jobs | Claude Code, Codex CLI | Missing | **S11** |
| **8** | LSP diagnostics in the loop | Cursor, Claude Code | **Port exists, zero adapters** | **S10** |
| **9** | Long-term memory across sessions | Hermes (A-MEM) | **Port exists, zero adapters** | **S12** |
| **10** | Skill compilation from traces | Hermes | Missing | **S13** |
| **11** | Prompt evolution (DSPy/GEPA) | Hermes | Missing | **S13** |
| **12** | Process Reward Model / step scoring | Cognition, research SOTA | Missing | **S14** |
| **13** | Statistical control plane (AOI) | — (our differentiator) | **`aoi/` is an empty package** | **S14** |
| **14** | Mission scheduling over days/weeks | — (our differentiator) | Missing | **S15** |

Two entries deserve emphasis because they are *cheap and large*:

**Localization (#2/#3) is the highest score-per-line item in this document.** Agentless reaches
45% on SWE-bench Verified with **no agent loop at all** — just localize → generate → validate, at
one tenth the cost of a ReAct agent. AutoCodeRover reaches 52% the same way. Their entire edge is
picking the right five files before touching any. We have `Indexer.search`, `CodeGraph.impacted_by`,
and `get_skeleton` already built and currently feeding nothing.

**The Architect/Editor split (#4) is a prompt-level change with an outsized measured effect.** Aider
tops HumanEval at 94.8% by having one model *reason* about the change in prose and a second model
*apply* it as a diff. We already have a multi-role `ModelConfig` (`execution`, `judge`); adding an
`architect` role is configuration plus one loop branch.

---

## 3. Reference Recommendations We Decline

Recorded so nobody re-proposes them mid-sprint. Each restates or extends the `concept_review.md`
Chapter 3 reassessment.

| Recommendation | Source | Decision | Reason |
|---|---|---|---|
| LangGraph as the orchestration engine | briefing Ch.8 | **Decline** | Our native async kernel is better-typed and already has the choke point, taint, and grants LangGraph would sit awkwardly beside. Keep `Orchestrator` as an optional adapter seam. |
| Temporal.io for durable execution | briefing Ch.8 | **Decline** | `FrozenRunState` already does durable suspension with grants absent. Temporal adds a server, a worker model, and a second failure domain to solve a solved problem. |
| Ray for parallel outer-loop runs | briefing Ch.8 | **Defer** | Single-host `asyncio` + process pool covers N ≤ 8 candidates. Revisit only if outer-loop wall-clock becomes the binding constraint. |
| Neo4j / NetworkX knowledge graph | briefing Ch.2 | **Decline** | SQLite tables from Tree-sitter + git are deterministic, boring, and already shipped. ADR-0014's reasoning holds. |
| LanceDB / sqlite-vec dense tier | briefing, conceptual §6 | **Defer behind trigger** | ADR-0014. Adopt only when recall@10 on a labelled query set demonstrably fails. |
| Redis for short-term memory | briefing Ch.2 | **Decline** | `conceptual-design.md` §6 already rejected this correctly: STM is per-session and small, and SQLite-WAL co-locates it with the trajectory. |
| DI container + dynamic plugin discovery | briefing Ch.2 | **Decline** | ADR-0004. Static navigability is a first-class requirement when the maintainer is an LLM with a language server. |
| MCTS / tree search | conceptual §4.1 | **Defer** | ADR-0005. One expansion costs a full agent run plus a test suite. Requires a calibrated PRM first (S14). |
| **DuckDB for trajectory analytics** | briefing Ch.8 | **Adopt (S9)** | Read-only, offline, in-process. Genuine fit for feature extraction over trace logs. |
| **Promptfoo for injection CI** | briefing Ch.4 | **Adopt (S13)** | The one clear gap in our defensive posture. Declarative YAML, cheap to run in CI. |
| **Inspect AI as an eval adapter** | briefing Ch.8 | **Adopt (S9)** | Behind the existing `Evaluator` port. Gives sandboxed agent evaluation without rewriting `e0/`. |
| **SWE-bench Pro as primary screen** | references §4.2 | **Adopt (S14)** | Verified is saturated and contaminated. Pro is the honest benchmark. |

---

## 4. Architecture: Where the New Work Attaches

### 4.1 The three planes

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  CONDUCTOR (System 3) — S15+                                             │
│  MissionSpec scheduling, hours→weeks. No tools. No grants. No shell.     │
│  Downward surface: the Orchestrator port, and nothing else.              │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │ Orchestrator.execute() → AsyncIterator[Event]
┌─────────────────────────────────▼────────────────────────────────────────┐
│  SYMBOLIC PLANE — the agent loop (S7f/S8/S10)                            │
│  Localize → Architect → Edit → Test → Repair. Frontier LLMs.             │
│  High latency, high cost, creative.                                      │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │ telemetry ↓        control signals ↑
┌─────────────────────────────────▼────────────────────────────────────────┐
│  STATISTICAL PLANE — AOI (S14)                                           │
│  f_θ surrogate reward · g_φ failure risk · UCB ranker                    │
│  Sub-ms, zero token cost, local GBDT/ONNX. ADVISORY ONLY — never admits. │
│  Feature store: DuckDB over the trajectory log.                          │
└──────────────────────────────────────────────────────────────────────────┘
```

The invariant that makes this safe: **the statistical plane ranks and filters; it never admits or
rejects.** Hard gates stay deterministic and stay in the TCB. An AOI model that could admit a
candidate is an evaluator the improver can train, which is the trivial-optimum failure the whole
design exists to prevent.

### 4.2 The agent loop, target shape (post-S8)

Current (post-S7f) is `assemble → model → tools → gate → repair`. Target:

```text
  ┌─ LOCALIZE ──────────────────────────────────────────────┐
  │ Indexer.search(goal) → CodeGraph.impacted_by → skeletons│  cheap, no model
  │ → ranked file list + repo map                            │
  └───────────────────────┬──────────────────────────────────┘
                          ▼
  ┌─ ARCHITECT (role: architect) ───────────────────────────┐
  │ reasons in prose over the repo map; emits a change plan  │  1 model call
  │ NO tool access — cannot edit, cannot run                 │
  └───────────────────────┬──────────────────────────────────┘
                          ▼
  ┌─ EDIT (role: execution) ────────────────────────────────┐
  │ existing RunLoop: apply_edit / run_command under grants  │  N model calls
  └───────────────────────┬──────────────────────────────────┘
                          ▼
  ┌─ VALIDATE ──────────────────────────────────────────────┐
  │ FAIL_TO_PASS + PASS_TO_PASS + LSP diagnostics + gates    │  no model
  └───────────────────────┬──────────────────────────────────┘
                          ▼
              admitted? ──no──► REPAIR (S7f) ──┐
                  │yes                          │ (bounded)
                  ▼                             └──► back to EDIT
               submit
```

Every stage is independently disableable by config, which is what makes the ablation suite able to
attribute the score to a mechanism rather than to a vibe.

### 4.3 Config-driven by construction

The stated requirement is a decoupled, parametrized, config-driven system. Concretely, every
mechanism below lands as a frozen Pydantic block under `Config`, defaulting to the honest-negative
(`enabled: False`) until its ablation earns the flip:

```python
class LocalizationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    enabled: bool = False
    max_files: int = 10
    graph_hops: int = 2
    include_skeletons: bool = True
    strategy: Literal["search", "search+graph", "sbfl"] = "search+graph"


class ArchitectConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    enabled: bool = False
    role: str = "architect"  # resolves through ModelConfig tiers
    max_plan_tokens: int = 2048


class SkillConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    enabled: bool = False
    compile_from_traces: bool = False
    min_trace_successes: int = 3  # promotions require repeated success
    require_human_signoff: bool = True
```

**Rule (binding): no mechanism in S8-S16 may default to `True` before its ablation is published.**
This is the honest-negative doctrine that already governs `search.enabled` and `retrieval.enabled`.

---

## 5. Sprint Specifications

### S8 — Localization and the Architect/Editor Split

**Why first:** highest score-per-line in the plan; Agentless gets 45% with *only* this.

#### 5.1 `LocalizationEngine`

New module `agency/localize.py`. Not a port — it composes existing ports and holds no I/O of its own.

```python
@dataclass(frozen=True)
class LocalizationResult:
    files: tuple[str, ...]  # ranked, most-suspicious first
    repo_map: str  # Tree-sitter skeletons, token-bounded
    rationale: tuple[str, ...]  # why each file was picked — goes in the trace


class LocalizationEngine:
    def __init__(self, indexer: Indexer, graph: CodeGraph, cfg: LocalizationConfig) -> None: ...

    async def localize(self, task: TaskSpec) -> LocalizationResult:
        # 1. sparse retrieval over the goal text
        hits = await self._indexer.search(task.goal, limit=self._cfg.max_files * 3)
        seeds = _dedupe_paths(hits)

        # 2. graph expansion — the step naive BM25 baselines skip
        expanded: dict[str, float] = {p: 1.0 for p in seeds}
        for path in seeds[: self._cfg.max_files]:
            for neighbor in await self._graph.impacted_by(path, hops=self._cfg.graph_hops):
                expanded.setdefault(neighbor, 0.0)
                expanded[neighbor] += 0.3  # weaker than a direct hit

        # 3. rank, truncate, build the map
        ranked = sorted(expanded, key=lambda p: -expanded[p])[: self._cfg.max_files]
        skeletons = (
            [await self._indexer.get_skeleton(p) for p in ranked] if self._cfg.include_skeletons else []
        )
        return LocalizationResult(
            files=tuple(ranked),
            repo_map=_pack_within_budget(skeletons, MAX_REPO_MAP_TOKENS),
            rationale=tuple(f"{p}: score={expanded[p]:.2f}" for p in ranked),
        )
```

The repo map is passed as `retrieval_seed`, preserving ADR-0021 seed-only-by-shape exactly.

#### 5.2 Architect role

```python
# In composition, when ArchitectConfig.enabled:
async def architect_pass(task, loc: LocalizationResult, model: ModelProvider) -> str:
    request = ModelRequest(
        role="architect",
        messages=[
            Message(
                role="user",
                content=[
                    TextBlock(
                        text=ARCHITECT_PROMPT.format(
                            goal=task.goal, repo_map=loc.repo_map, files="\n".join(loc.files)
                        )
                    )
                ],
            )
        ],
        tools=(),  # ← no tools. The architect cannot act.
    )
    return _text_of((await model.complete(request)).message)
```

The plan text becomes the first anchored entry in `ContextAssembler.set_plan()`, which already
exists for freeze/thaw. **The architect having no tools is a security property, not a style
choice** — it is a model call that cannot reach the dispatch choke point at all.

#### 5.3 Tasks

- S8.1 `LocalizationConfig` + `ArchitectConfig`; both default `False`.
- S8.2 `agency/localize.py` + unit tests with a fake indexer/graph.
- S8.3 Wire localization into `composition.py` as the `retrieval_seed` producer.
- S8.4 `architect` tier in `ModelConfig`; `ARCHITECT_PROMPT` in `agency/context/system_prompt.py`.
- S8.5 Architect pass in `RunLoop.run` behind the config flag.
- S8.6 Ablation: localization ON/OFF × architect ON/OFF (4 cells), Holm-corrected.
- S8.7 Flip defaults for whichever cells win; publish the table.

**Exit gate:** SWE-bench Lite ≥ 80%, and the ablation attributes the delta to a named mechanism.

---

### S9 — Observability, EventStream, and the Verified Run

#### 5.4 Replayable EventStream

OpenHands' architectural edge is a typed `Action`/`Observation` stream that is the *single* source
of run state. We have `EventBus` + `TrajectoryStore` but the bus is fire-and-forget. Make the
trajectory the authoritative replayable stream:

- Every `Event` persists with a monotonic `(run_id, seq)`.
- `replay(run_id) -> AsyncIterator[Event]` reconstructs a run without model calls.
- Replay honors `EffectClass`: PURE re-executes, DESTRUCTIVE serves from recorded observation. (The
  `conceptual-design.md` §12.5 point — without this, "time-travel debugging" re-runs `rm`.)

#### 5.5 DuckDB trajectory mining (read-only)

```python
# adapters/telemetry/duck.py — read-only by construction, no writer path.
class DuckTrajectoryAnalytics:
    def __init__(self, trajectory_db: Path) -> None:
        self._con = duckdb.connect(":memory:")
        self._con.execute(f"ATTACH '{trajectory_db}' AS traj (TYPE SQLITE, READ_ONLY)")

    def failure_taxonomy(self, since: datetime) -> list[FailureBucket]: ...
    def cost_attribution(self, run_ids: Sequence[str]) -> CostBreakdown: ...
    def feature_frame(self, run_ids: Sequence[str]) -> pa.Table:  # feeds AOI in S14
        ...
```

#### 5.6 Tasks

- S9.1 OTel GenAI spans across dispatch, model calls, gates.
- S9.2 Persist all events; add `replay()`; effect-aware replay semantics.
- S9.3 DuckDB read-only analytics adapter + failure taxonomy.
- S9.4 Cost/latency attribution per task, per mechanism.
- S9.5 `Evaluator` adapter wrapping Inspect AI.
- S9.6 **Full SWE-bench Verified run (500 tasks), k=3, published with CI.**

**Exit gate:** SWE-bench Verified ≥ 80% with a published confidence interval.

---

### S10 — Diagnostics, Fault Localization, and Feedback Latency

#### 5.7 LSP adapter (the port has zero implementations today)

`conceptual-design.md` §6 is right that no sidecar is needed — language servers are already
daemons. What is needed is a **warm supervisor with a bounded pool**, because N worktrees × M
languages exhausts memory.

```python
class WarmLspSupervisor:
    """Bounded pool of warm language servers with document overlays.

    One server per (language, repo-root) — NOT per worktree. Unsaved edits are pushed as
    `didChange` overlays so diagnostics reflect the agent's in-flight state without a write.
    """

    def __init__(self, max_servers: int = 4, idle_timeout_s: float = 300.0) -> None: ...
    async def get_diagnostics(self, file_path: str) -> list[DiagnosticItem]: ...
```

Diagnostics enter the loop as a **post-edit observation**, not a gate: a type error after
`apply_edit` returns to the model immediately rather than after a full test cycle. This is the
"feedback latency" lever `conceptual-design.md` §11 names as one of the things that actually
determines whether a coding agent works.

#### 5.8 SBFL (AutoCodeRover's mechanism)

```python
async def suspiciousness(test_cmd: str, ctx: RunContext) -> dict[str, float]:
    """Ochiai coefficient per file from coverage of passing vs failing tests.

        ochiai(e) = failed(e) / sqrt(total_failed * (failed(e) + passed(e)))

    Requires one instrumented test run (`coverage run`). Costs one extra suite execution
    and buys a ranked suspect list that localization alone cannot produce.
    """
```

Feeds `LocalizationConfig.strategy = "sbfl"` as a third ranking source.

#### 5.9 Tasks

- S10.1 `WarmLspSupervisor` + pool bounds + overlay sync.
- S10.2 Diagnostics as post-edit observation; measure feedback-latency delta.
- S10.3 Coverage-instrumented run + Ochiai SBFL scoring.
- S10.4 `strategy="sbfl"` wired into `LocalizationEngine`.
- S10.5 Ablation: SBFL vs search+graph.

---

### S11 — Terminal-Bench: Long-Horizon Shell Autonomy

This is the Hermes comparison, and it is a different engineering problem from patch generation.

- **Background jobs.** `run_command(background=True)` returns a handle; `poll_job` / `read_output` /
  `kill_job` as separate tools. Claude Code and Codex CLI both have this; long-horizon tasks
  (start a server, then test against it) are impossible without it.
- **Session state.** `cwd`, exported env, and background PIDs persist per `run_id` (rev2 AD-10).
- **Interactive/TTY handling.** Bounded `expect`-style interaction for tools that prompt.
- **Generous bounded budgets.** `max_steps_per_task = 150` for the terminal profile.
- **Recovery.** A failed command must not abort the run; Terminal-Bench tasks are mostly recovery.

**Exit gate:** Terminal-Bench 2.1 ≥ 80% (passes Hermes' 80.9% within CI, or states honestly that it
does not).

---

### S12 — Long-Term Memory (A-MEM)

The `Memory` port exists with **zero adapters**; only `short_term.py` is implemented.

Split by epistemics, per `conceptual-design.md` §6 — this is the decision that keeps it cheap:

- **Deterministic code structure** → already in SQLite from Tree-sitter + git. Never LLM-extracted.
  (Charging tokens for facts the parser knows, and admitting hallucinated edges into dependency
  analysis, is the failure mode to avoid.)
- **Episodic / decision memory** → genuinely unstructured, loses validity over time. This is where
  a bi-temporal store earns its cost.

```python
class SqliteMemory:
    async def remember(self, episode: Episode) -> str: ...
    async def recall(self, query: str, *, as_of: datetime | None = None) -> list[Episode]: ...
    async def invalidate(self, episode_id: str, reason: str) -> None: ...
```

Domain-shaped (`remember`/`recall`), never storage-shaped (`store_vector`) — the seam that lets a
temporal graph engine substitute later without touching a caller.

Cross-session recall enters the prompt through the **same seed-only path** as retrieval. Memory
does not get a privileged channel.

---

### S13 — Skills, Prompt Evolution, and Injection CI

#### 5.10 Skill compiler (Hermes' mechanism)

A verified execution trace that solved a task N times becomes a reusable skill.

```python
@dataclass(frozen=True)
class Skill:
    skill_id: str
    trigger: str  # when to consider it
    instructions: str  # what worked
    tool_sequence: tuple[str, ...]
    provenance: tuple[str, ...]  # the run_ids it was compiled from
    successes: int


async def compile_skills(analytics: DuckTrajectoryAnalytics, cfg: SkillConfig) -> list[Skill]:
    """Mine repeated successful tool sequences; emit candidate skills.

    Promotion requires `min_trace_successes` independent successes AND human sign-off
    (`require_human_signoff`). A skill is harness behaviour; auto-promoting one is the
    outer loop editing itself without validation.
    """
```

**Constraint:** skills are *instructions and tool sequences*, never new authority. A skill cannot
grant a capability the run did not already hold.

#### 5.11 Prompt evolution

DSPy/GEPA-style optimization over the **mutable surface only** — system prompts, tool descriptions,
compaction parameters. Path-allowlisted away from the TCB (`kernel/policy/`, `outer_loop/evaluator/`,
`.github/workflows/`), exactly as `MetaImprover` already is.

#### 5.12 Promptfoo injection CI

The one clear defensive gap. Declarative YAML red-team suite in CI covering OWASP LLM Top 10, run
on every change to a prompt or tool description. This is RHI Tier A: roughly 90% of
self-improvement's defensive value at CI cost, and it is what lets S13's prompt evolution be
trusted at all.

---

### S14 — AOI: The Statistical Control Plane

`aoi/` is currently an empty package with one `__init__.py`. It becomes real here, and **only
here**, because it needs the trajectory corpus S9 produces.

Three models, all local CPU, all advisory:

| Model | Signature | Acts on |
|---|---|---|
| `f_θ` surrogate reward | `features → E[score]` | Ranks outer-loop mutation candidates before expensive evaluation |
| `g_φ` failure risk | `partial trajectory → P(fail)` | Early-stop recommendation |
| UCB ranker | `μ̂(c) + α√(ln N / (N_c+1)) − λ·E[cost]` | Exploration/exploitation over configs |

**The censored-outcome trap is mandatory to handle** (`conceptual-design.md` §14.5). A failure
predictor that halts runs it expects to fail destroys its own training signal: halted runs never
produce success labels, so its false positives are never observed and it confirms itself forever.
Three countermeasures, non-optional:

1. **Shadow mode first.** Predict and log; do not act until a reliability diagram and Brier score
   on held-out runs justify promotion. A threshold picked before calibration data exists is an
   arbitrary number wearing a decimal point.
2. **Fixed exploration fraction always runs to completion**, regardless of predicted risk.
3. **Censored outcomes are never trained as negatives**; correct with inverse-propensity weighting.

Deterministic circuit breakers ship *first* and stay as the fallback — they need no training data:

- **AST hash ring:** if `H(AST_t) ∈ {H(AST_{t-1})…H(AST_{t-k})}`, halt on oscillation.
- **Test stagnation:** pass ratio flat over K iterations ⇒ halt.
- **Consecutive error limit:** 3 non-zero exits with no code change ⇒ halt.

Also lands here: **PRM (process reward model)** for step-level scoring, which is the hard
prerequisite for tree search ever being reconsidered (ADR-0005).

---

### S15 — The Conductor (System 3)

The mission layer. Timescale: hours to weeks.

```python
class MissionSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    mission_id: str
    goal: str
    stories: tuple[StorySpec, ...]  # a DAG, not a list
    budget_usd: float
    deadline: datetime | None


class Conductor:
    """Schedules stories onto the Orchestrator port. Holds no tools, no grants, no shell.

    Its entire downward surface is `Orchestrator.execute()`. This is the invariant that
    keeps a long-lived scheduler from accumulating authority.
    """

    async def run_mission(self, mission: MissionSpec) -> AsyncIterator[Event]:
        budget = BudgetTree(mission.budget_usd)  # mission → story → run
        for story in _topological(mission.stories):
            if not budget.can_afford(story):
                yield MissionParked(mission_id=mission.mission_id, reason="budget")
                return
            async for event in self._orchestrator.execute(story.to_task(), ctx):
                yield event
```

Identity becomes `(mission_id, story_id, run_id)` — **introduce this triple early**, in S7b's
orchestrator work, because retrofitting an identity scheme through a trajectory store is
expensive.

**Process hibernation:** `FrozenRunState` extends to survive host reboots, rate-limit droughts, and
spot preemption. A three-week mission crosses all three.

Phases C0-C7 from `agi_evolution_path.md` sequence inside this sprint band.

---

### S16 — Model Promotion Gauntlet

The loop closes: the harness generates its own training data.

1. `sagiha export` curates SFT/DPO pairs from verified trajectories (the `outer_loop/export/`
   machinery already exists — `sft.py`, `dpo.py`, `eligibility.py`, `license.py`, `redaction.py`).
2. Fine-tune a local open-weights model (DeepSeek V4 / Kimi K3 class).
3. Evaluate the tuned model against the held-out suite through the same E0 statistics.
4. Promote only on a Holm-corrected win over the base model, with human sign-off.

This is the "ability to generate and maintain its own subsequent versions" success metric from
`conceptual-design.md` §10 — and it is last for a reason: it is worthless without S9's honest
measurement and S14's calibration.

---

## 6. Performance and Code Quality Requirements

Stated requirement: high-performance code, world-class quality. Concretely and measurably:

| Requirement | Mechanism | Gate |
|---|---|---|
| No blocking I/O on the event loop | `asyncio.to_thread` for CPU/FS; no sync calls in async paths | Lint rule + review |
| Indexing throughput | `py-tree-sitter` + multiprocessing across files | Measured baseline before any Rust sidecar is considered |
| Prompt cache hit rate | Stable prefix preserved across repair turns (rev2 AD-2) | Reported per bench run |
| Token efficiency | Repo map + skeletons instead of whole files (Aider's edge) | Tokens-per-task in the report |
| Type safety | pyright strict, 0 errors | `verify.sh` |
| Architectural boundaries | `lint-imports` contracts, 5/5 | `verify.sh` |
| Port hygiene | Every port has an adapter + conformance test, or is deleted | `check_port_rent.py` |
| Honest instrumentation | No gate reports `True` unless it ran | AST lint for fabricated constants |
| Docs discipline | ≤ 15,000 normative words, 0 dead links | `verify.sh` |

**No compiled sidecar is written before a Python baseline is measured.** `conceptual-design.md` §6
is right: `py-tree-sitter` binds the same C library, and multiprocessing typically recovers most of
the available gain. A sidecar is justified only when a process must stay warm holding large
in-memory state, and the boundary must be drawn at the *query*, never at parsing — a sidecar
returning ASTs serializes the whole structure back into Python objects and reintroduces exactly the
cost it existed to avoid.

---

## 7. Risk Register

| # | Risk | Mitigation |
|---|---|---|
| R-1 | Chasing 80% on the wrong benchmark | §1 fixes a target per benchmark per sprint |
| R-2 | S14 AOI trained on too little data | Gated behind S9's corpus; deterministic breakers ship first and remain the fallback |
| R-3 | Failure predictor confirms itself (censored outcomes) | Shadow mode + fixed exploration fraction + IPW. Non-optional |
| R-4 | Skill compiler promotes a lucky trace | `min_trace_successes ≥ 3` + human sign-off; skills carry no authority |
| R-5 | Prompt evolution edits the TCB | Path allowlist, already enforced for `MetaImprover`; Promptfoo CI on every prompt change |
| R-6 | Conductor accumulates authority over a long mission | AD: no tools, no grants, no shell; `Orchestrator` is the only downward surface |
| R-7 | Mechanism sprawl — 14 flags nobody can reason about | Every flag defaults `False` and must earn its flip with a published ablation |
| R-8 | Benchmark contamination invalidates the headline | Move to SWE-bench Pro (S14); keep commit-replay harvesting as the uncontaminated primary |
| R-9 | Frontier-model cost makes k≥3 × 500 tasks unaffordable | Publish local/open-weights numbers as primary, frontier as a single reference run |

---

## 8. Proposed Sprint Plan

| Sprint | Theme | Tasks | Exit gate |
|---|---|---|---|
| **S8** | Localization + Architect | S8.1 configs · S8.2 `LocalizationEngine` · S8.3 wire as seed · S8.4 architect role + prompt · S8.5 architect pass · S8.6 4-cell ablation · S8.7 flip winners | SWE-bench Lite ≥ 80%; delta attributed |
| **S9** | Observability + Verified run | S9.1 OTel spans · S9.2 event persistence + effect-aware replay · S9.3 DuckDB analytics · S9.4 cost attribution · S9.5 Inspect AI adapter · S9.6 Verified 500 × k=3 | **Verified ≥ 80% with CI** |
| **S10** | Diagnostics + SBFL | S10.1 warm LSP pool · S10.2 diagnostics as observation · S10.3 Ochiai SBFL · S10.4 `strategy="sbfl"` · S10.5 ablation | Feedback-latency delta measured |
| **S11** | Terminal autonomy | S11.1 background jobs · S11.2 session state · S11.3 TTY interaction · S11.4 terminal budgets · S11.5 recovery semantics · S11.6 Terminal-Bench run | **Terminal-Bench ≥ 80%** |
| **S12** | Long-term memory | S12.1 `SqliteMemory` adapter · S12.2 episodic schema + bi-temporal reads · S12.3 invalidation · S12.4 seed-path integration · S12.5 recall@k eval | Memory recall measured separately from task success |
| **S13** | Skills + prompt evolution + injection CI | S13.1 `Skill` model · S13.2 trace mining · S13.3 promotion w/ sign-off · S13.4 DSPy/GEPA over mutable surface · S13.5 Promptfoo CI | Zero injection regressions; skills carry no new authority |
| **S14** | AOI + PRM + SWE-bench Pro | S14.1 feature store · S14.2 deterministic breakers · S14.3 `f_θ` shadow · S14.4 `g_φ` shadow + IPW · S14.5 UCB ranker · S14.6 PRM · S14.7 Pro suite | Calibration published (Brier + reliability diagram); **Pro ≥ 55%** |
| **S15** | Conductor (System 3) | S15.1 `MissionSpec`/`StorySpec` · S15.2 `(mission,story,run)` identity · S15.3 budget tree · S15.4 story DAG scheduling · S15.5 hibernation across reboots · S15.6 multi-day mission trial | A 72-hour mission survives a reboot and completes |
| **S16** | Model promotion gauntlet | S16.1 SFT/DPO curation · S16.2 local fine-tune pipeline · S16.3 held-out eval · S16.4 promotion gate + sign-off | Tuned model beats base, Holm-corrected |
| **S17+** | SOTA push | Re-ablate everything; tree search **iff** PRM calibrated; Pro ≥ 70% | Defensible SOTA claim |

### 8.1 Dependency graph

```text
S7f (repair loop) ──┬──► S8 (localize+architect) ──► S9 (observability + Verified) ──┐
                    │                                        │                       │
                    └──► S11 (terminal) ◄────────────────────┘                       │
                                                             ├──► S10 (LSP+SBFL)     │
                                                             ├──► S12 (memory) ──────┤
                                                             └──► S13 (skills) ──────┤
                                                                                     ▼
                                                                          S14 (AOI+PRM+Pro)
                                                                                     │
                                                                                     ▼
                                                                          S15 (Conductor)
                                                                                     │
                                                                                     ▼
                                                                          S16 (promotion)
```

S9 is the hinge: everything statistical downstream needs its trajectory corpus, and everything
empirical needs its honest number.

### 8.2 Standing rules

1. **One mechanism per sprint exit gate.** No sprint bundles two unmeasured mechanisms behind one
   gate — the Block 5 mega-scope pattern that S7 repeated.
2. **Every mechanism defaults `False` until its ablation publishes.**
3. **`scripts/verify.sh` green before every commit.** One commit per wave. Never push without asking.
4. **The TCB is never edited by the harness:** `kernel/policy/`, `outer_loop/evaluator/`,
   `.github/workflows/`. Human-authored only.
5. **Advisory never admits.** Statistical models rank and filter; hard gates stay deterministic.
6. **No published number without N, k, noise floor, and correction.**

---

## 9. Closing

The gap between where SAGIHA is and a top-tier benchmark number is not model quality and not
architectural sophistication — the hexagon, the choke point, the sandbox, and the statistics are
already better than most of the field. It is a short list of unglamorous feedback mechanisms:
read the right files before editing, run the tests, read the failure, edit again, and check you
did not break anything else.

S7f and S8 are that list. Everything from S9 onward is the harder and more interesting project —
a system that measures itself honestly enough to improve itself safely — and none of it is worth
building until the number underneath it is real.

The discipline that makes this achievable is restraint. The failure mode for a plan like this one
is not insufficient ambition; it is building the exotic components first. Tree search, temporal
graphs, compiled sidecars, and quantization are legible and satisfying to design. What actually
determines whether a coding agent works is the model port, context and cache layout, chunking,
edit application, feedback latency, and error recovery. Correct seams are what make deferral free:
a query-shaped `Indexer` accepts a compiled sidecar later without touching a consumer, and a
domain-shaped `Memory` accepts a temporal graph without a caller noticing. That is the return on
drawing the hexagon properly, and it is why this roadmap trades scheduled sophistication for
triggered sophistication.
