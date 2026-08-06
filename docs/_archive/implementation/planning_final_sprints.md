---
status: rationale
retrieval: excluded
updated: 2026-08-01
---

# Planning: Final Sprints (S7 → S10) and SWE-bench/Terminal-Bench Parity

> Source prompt, preserved verbatim below (§1), plus the feature checklist needed to make
> SAGIHA/AETHER a fair, scoreable competitor against Hermes/OpenHands/Claude Code CLI on
> SWE-bench and Terminal-Bench (§2). This file is planning input, not a decisions register —
> `sprints_0_to_6_fix_plan.md`'s successor (see `Harness_LLM_orchestrator_aether_project_review_v210.md`
> §"Sub-Sprint Plan") is the executable checklist; this file is why it looks the way it does.

## 1. Execution Prompt (as given)

Next steps, in dependency order:

### 1. Close W9 (blocking everything empirical)

The staged work needs to actually land and be green first:
- Fix **N-C2** — `_repo_root_for` routes local tmp task paths through `resolve_task_root`,
  breaking `test_benchmark_runner_single_task` and `test_benchmark_runner_suite_run` with
  `git init failed`. Only remote/upstream tasks should hit the cache.
- Fix **N-C1** — gitignore and ruff-exclude `.sagiha/repo-cache/`, and make `DEFAULT_CACHE_DIR`
  absolute rather than CWD-relative so tests stop writing pytest temp dirs into the working
  tree. This is 343 of the 344 ruff errors.
- Run `scripts/verify.sh` and commit the wave properly; mark W9 done in the fix plan's §4 with
  the real commit SHA (**N-C3**: W8's `0b7804b` landed without the gate, and the plan row is
  still empty).

### 2. Produce the honest baseline

With repo-cache working and the model flags wired, run the A/A noise floor and the three
ablations against Ollama or OpenRouter. Rewrite `noise-floor.md` with real numbers. Until this
exists, every "did it help?" gate in S7 and beyond is unmeasurable — this is the single
highest-leverage item on the list.

### 3. Build the Orchestrator adapter

`ports/orchestrator.py` has zero implementations. It's the Conductor's entire downward surface
per `agi_evolution_path.md` §2.1, so C0 is blocked on a prerequisite nobody scheduled. It also
unblocks sub-agents, and MCP tool-budget work depends on it.

### 4. Split S7

It currently bundles Story-DAG + MCP + streaming behind one exit gate, which is the Block 5
mega-scope pattern the plan's own Standing Rule 2 forbids. Ship S7c (streaming/steer) first
since it's independent of the benchmark; sequence S7b → S7d → S7e behind steps 2 and 3.

### 5. Contract surface truth-up (S8)

Extend conformance from 7 of 17 ports to all of them, then actually execute ADR-0023 port
rent — advisory, meta_improver, toolchain have zero importers across two closed blocks and
should be demoted or deleted. Add `check_port_rent.py` so the rule enforces itself.

### 6. Repo hygiene

Delete the 868 MB of untracked vendored trees under `src/` (`hermes_agent`, `grok_build`,
`claude_code`, `open_code`). They are the sole reason both pyright and ruff carry exclusion
lists; removing them deletes both lists and makes the gates mean what they say.

Steps 1 and 2 are the real critical path — everything downstream is either gated on honest
numbers or is cleanup that can happen in parallel.

**Sprint 7 Series (v2-S7a → v2-S7e) — Near-Term V2 Engine Completion:**
- **v2-S7a**: Measurement Closeout (Noise floor calibration & SWE-bench Lite ablations).
- **v2-S7b**: `LocalOrchestrator` adapter (`RunLoop` → `AsyncIterator[Event]`) & `spawn_subagent` delegation.
- **v2-S7c**: Streaming completions & real-time TUI steer (<2s boundary interrupts).
- **v2-S7d**: MCP Client Driver (`sagiha/adapters/mcp/driver.py`).
- **v2-S7e**: Story-DAG macro layer (`WorkflowStep`, integration rebasing, conflict repair).
- **v2-S8 – v2-S10**: Contract truth-up, DuckDB trace mining, and prompt regression CI.

### Senior Developer Execution & Planning Prompt

**SENIOR DEVELOPER TASK: Sprint 7 Execution & V3 Master Roadmap Planning**

You are a Senior Systems Architect & Principal Developer tasked with completing SAGIHA V2
(Sprint 7 series) and authoring `docs/implementation/development_plan_v3.md` for the future
AETHER V3 System 3 Conductor milestone.

**Primary Authority & Source Documents** — inspect and strictly obey before writing code or
documentation:
- Single Source of Truth: `docs/STATUS.md`
- CAR Security & Port Invariants: `AGENTS.md`
- V2 Sprint Sequence: `docs/implementation/development_plan_v2.md`
- V2 Remediation Audit: the sprints-0-to-6 fix plan and its successor,
  `docs/rationale/reviews/Harness_LLM_orchestrator_aether_project_review_v210.md`
- System 3 Evolution Vision: `docs/rationale/reviews/agi_evolution_path.md`
- Reference Architecture: `docs/rationale/reference/ai_coding_agents_references_swe_terminal-benchs.md`

**Immediate Execution Objective: Sprint 7 Sub-Sprint Breakdown (`v2-S7a` → `v2-S7e`)**

Execute in strict sequential order. Run `bash scripts/verify.sh` after every step to confirm
0 type errors (pyright), 5/5 import contracts (lint-imports), and 0 dead links (`check_links.py`).

1. **`v2-S7a` — Measurement Closeout & Noise Floor (Wave W9)**
   - Run `sagiha bench --suite benchmarks/definitions/s0-core.json --aa` on SWE-bench Lite.
   - Publish noise floor and empirical ablations (Best-of-N, retrieval ON/OFF, cold-start `init` ON/OFF).
   - Unguard `bench-aa` in CI (`scripts/verify.sh`).
2. **`v2-S7b` — `LocalOrchestrator` & Sub-Agent Delegation**
   - Build `LocalOrchestrator` adapter under `src/sagiha/adapters/orchestrator/local.py` implementing
     `sagiha.ports.orchestrator.Orchestrator` (`RunLoop` → `AsyncIterator[Event]`).
   - Wire `spawn_subagent` tool in `src/sagiha/adapters/tools/builtins.py` with grant-subset and
     budget envelopes.
   - Enforce the 20-tool per-kernel registry cap.
3. **`v2-S7c` — Real-Time Streaming & Steerable TUI**
   - Wire streaming completions in `OpenAIAdapter`.
   - Support sub-2-second exchange-boundary interrupts via Layer 8 `SteerEvent` tail-appending.
4. **`v2-S7d` — MCP Client Driver**
   - Implement stdio transport and grant-gated untrusted tool registration in
     `src/sagiha/adapters/mcp/driver.py`.
5. **`v2-S7e` — Story-DAG Macro Layer**
   - Implement `WorkflowStep`, integration rebasing over worktrees, and automated
     `ResolveConflictTask` inner-loop repair.

**Planning Objective: Create `docs/implementation/development_plan_v3.md`**

After Sprint 7 implementation is complete, create `docs/implementation/development_plan_v3.md`
specifying the AETHER V3 System 3 Conductor Architecture:

1. **System 3 Strategic Conductor** — `MissionSpec` roadmap scheduler, operating on the
   hours-to-weeks timescale. Strict separation: the Conductor is a pilot/scheduler; it holds no
   tools, shell handles, or grants. Downward interactions pass strictly through the
   `Orchestrator` port.
2. **Process Hibernation** — durable `FrozenRunState` process-exit hibernation across host
   reboots, rate-limit droughts, and spot preemption.
3. **A-MEM Active Memory Graph** — cross-session memory graph consolidation, linking execution
   traces into long-term structured knowledge.
4. **Skill Compiler** — automatic compilation of verified execution traces into reusable
   tools/skills (inspired by DSPy / GEPA and Hermes Agent).
5. **Tier-4 Model Promotion Gauntlet** — automated SFT/DPO dataset curation (`sagiha export`) and
   local model fine-tuning evaluation pipeline (Kimi K3 / DeepSeek V4).

**Verification Invariants**
- CAR Model: tool execution MUST route through `PolicyEngine.authorize()`. Never modify TCB files.
- Remoteable Ports: every port in `src/sagiha/ports/` MUST remain `async`, Pydantic-serializable,
  with zero live objects crossing boundaries.
- Docs Budget: keep normative word count ≤ 15,000 (`python3 scripts/docs_budget.py --max 15000`).
  Tag all non-normative docs with `status: rationale` and `retrieval: excluded`.

---

## 2. Feature Parity: What SAGIHA Needs to Be SWE-bench/Terminal-Bench Scoreable

The prompt above closes the engineering roadmap. It does not by itself guarantee a competitive
score. Hermes, OpenHands, and Claude Code CLI all clear ~70-80%+ on SWE-bench Verified by
combining a capable model with a small set of *harness-level* mechanisms SAGIHA currently lacks
or has only partially. These are additive to S7-S10, not a replacement for them — most slot into
S7b/S7c or a new S7f/S9 line item.

### 2.1 Already present (verify, don't rebuild)
- Sandbox perimeter (rootless Podman, ADR-0006/0016) — matches OpenHands' container isolation.
- TaintGate v1 — prompt-injection defense competitors mostly lack; a differentiator, not a gap.
- E0 harness with exact McNemar + Holm correction — more statistically honest than most published
  SWE-bench leaderboards, which is a selling point once numbers exist (S7a).
- `adapters/mcp/driver.py` scaffold exists (37 lines, stdio/HTTP stub) — S7d fills it in, doesn't
  start from zero.

### 2.2 Missing and load-bearing for score

1. **Iterative repair loop with test feedback.** Top scorers (Claude Code, OpenHands CodeAct)
   don't one-shot a patch — they run the repo's test command, read the failure, and retry inside
   the same run. Check whether `RunLoop` currently re-enters on a failing `run_command` gate
   result or terminates after one edit pass. If it terminates, this is the single biggest score
   lever available and belongs in S7b alongside `LocalOrchestrator` (the retry is itself a
   sub-loop the orchestrator should drive).
2. **Best-of-N / multi-sample selection at submission time**, not just as an ablation. The
   ablation in S7a measures *whether* BoN helps; if it does, production `bench`/`run` paths need
   a candidate-selection policy wired in by default, not just measured once and left in a report.
3. **Repo-scale context**: `Indexer.search` (ADR-0026) plus `CodeGraph.impacted_by` cover
   retrieval, but confirm the default agent loop actually calls them before editing — Claude
   Code's and OpenHands' edge over naive baselines is almost entirely "look at the right 5 files
   before touching any," not model quality.
4. **Patch validation before submission**: apply the diff to a clean checkout, re-run
   `FAIL_TO_PASS` (and ideally `PASS_TO_PASS`) tests in the sandbox, and only report success if
   green. Confirm this exists in `evaluator/` for the *harness's own* runs, not only in the
   imported SWE-bench task metadata — self-validation before submission is what turns "the model
   thinks it's done" into "it's done."
5. **Terminal-Bench-specific**: multi-command shell sessions with state (cwd, env vars,
   background processes) persisting across tool calls, and a generous but bounded turn/time
   budget per task. Check `ResourceGovernor` exposes a per-task budget knob, not just global
   concurrency limits — Terminal-Bench tasks are long-horizon (dozens of commands) in a way
   single-file SWE-bench patches are not.
6. **Cost/latency accounting per task** — both benchmarks' leaderboards increasingly report
   $/task and time/task alongside pass rate. `sagiha export` should already have the trace data;
   confirm the bench report surfaces cost, not just pass/fail, so a SAGIHA+free-model number is
   comparable to a Kimi K2/K3+Hermes number on more than one axis.
7. **Sub-agent delegation for parallel exploration** (S7b's `spawn_subagent`) — Hermes' edge on
   harder tasks comes partly from splitting "find the bug" and "write the fix" across
   sub-invocations with separate context. This is already scheduled in S7b; call it out here so
   it isn't scoped down to "just the port" during implementation.

### 2.3 Suggested new checklist item: S7f — Benchmark-Competitive Agent Loop

Insert after S7a (needs the noise floor to know if changes help) and before the S8 truth-up:
- Wire test-feedback retry into the default run loop (2.2.1).
- Wire retrieval-before-edit as a default step, not opt-in (2.2.3).
- Wire self-validation (apply diff → rerun tests → gate) into the evaluator path the harness
  uses for its own submissions (2.2.4).
- Add cost/time-per-task to the bench report (2.2.6).
- Re-run the S7a ablation suite once S7f lands to confirm the score moved, and publish a
  side-by-side against published Kimi K2/K3 + Hermes / OpenHands / Claude Code SWE-bench numbers
  in `docs/rationale/benchmarks/`.

Target: SWE-bench Lite/Verified pass rate ≥ 80% to sit alongside top-tier competitors, with the
honest-measurement discipline (S7a's McNemar/Holm machinery) as the differentiator — a claimed
80% with a real confidence interval outranks a claimed 80% without one.
