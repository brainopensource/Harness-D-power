---
status: rationale
retrieval: excluded
updated: 2026-08-02
---

# Tracking List — Sprint 7 (S7a→S8) → 80% SWE-bench → Conductor/AGI

## Done (committed, `3962c8d`)

- `scripts/bench_aa_smoke.py` — cheap CI gate for the bench/A-A pipeline, wired into `verify.sh`
- `BenchmarkRunner.sandbox` override + `sagiha bench --sandbox-runtime` CLI flag
- `SearchConfig.max_total_gate_evaluations` — bounds BoN × repair cost
- `verify.sh`: 10/10 gates green

## Done — R1a (repair loop) — committed

- `RepairContext`, `RepairConfig` (enabled=**False** default)
- `ContextAssembler.append_repair_turn` (tail-append, no 2nd system prompt)
- `RepairAttemptStarted` / `RepairAbandoned` events, `GateEvaluated.attempt`
- `_step_phase` extraction + repair wrapper in `RunLoop.run()`
- `max_steps` wiring fix across all 4 `RunLoop(...)` sites (was silently 20, not configured 200)
- Cost/latency stats in `e0/reporter.py` ($/task, wall-clock/task, calls/task — mean/p50/p95)
- Retrieval-seed wiring (AD-5) in `e0/runner.py` and `composition.py`'s BoN candidate path
- 13 new tests, all green (`test_repair_loop.py`, `test_composition_max_steps.py`, 2 in `test_bench_compare.py`)
- `verify.sh`: 10/10 gates green, 371 tests passing

## Todo — remaining waves

- [ ] **R1b** (TCB, needs your sign-off) — `PASS_TO_PASS` regression gate in `outer_loop/evaluator/gate_evaluator.py`. Must land with R1a before any score claim.
- [ ] **R1c** — re-measure A/A floor + 3 ablations after R1a+R1b (the real baseline)
- [ ] **R2** — `LocalOrchestrator` + `spawn_subagent` + 20-tool cap
- [ ] **R3** — streaming + steerable TUI (independent, anytime)
- [ ] **R4** — MCP client driver (currently a 37-line stub)
- [ ] **R5** — Terminal-Bench: shell-session persistence, per-task step budget
- [ ] **R6** — Story-DAG macro layer (descope if 80% reached without it)
- [ ] **R7** (S8) — `check_port_rent.py`, extend conformance to remaining ports
- [ ] **Defect #11** — `ContainerSandbox` never mounts a worktree's `.git` dir → every real container-sandboxed bench run silently reports gates as `None`. Blocks any real (non-subprocess) measurement.
- [ ] Real A/A floor itself — blocked today: Ollama context fixed (32k) but slow (~4.5 tok/s); OpenRouter free tier hit its 50-req/day cap. Deferred.

## Downstream (past S8)

- [ ] **R8** — delete 868MB vendored trees under `src/`, drop pyright/ruff exclusions
- [ ] **R9** (S9) — OTel spans, DuckDB trajectory mining, RHI Tier-B taxonomy
- [ ] **R10** (S10) — Promptfoo injection-regression CI
- [ ] **R11** — publication run: full SWE-bench Verified (500) + Terminal-Bench, N/CI/Holm-corrected
- [ ] **S11+** — Conductor (System 3), `FrozenRunState` hibernation, A-MEM memory graph, skill compiler, Tier-4 model-promotion gauntlet (`docs/implementation/planning_future_sprints.md`, `agi_evolution_path.md`)

**Critical path:** finish + commit R1a → land R1b (your sign-off) → re-measure (R1c). Everything else, including the AGI/Conductor track, is downstream of an honest repair-capable baseline.
