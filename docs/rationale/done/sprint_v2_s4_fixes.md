---
status: rationale
retrieval: excluded
updated: 2026-08-01
---
V2-S4 review — work-in-progress audit

State: S4.0–S4.3 + 4.4a are written; outer_loop/export/ is being authored right now. Signals: 188 pytest passed, ruff clean, lint-imports 5/5, event catalog in sync, pyright 6 errors — all 6 in the in-flight export/__init__.py (importing schema.py that doesn't exist yet), so that's your WIP, not a defect.

What's genuinely good

The architectural discipline held under pressure, which is the thing that usually breaks in a capability sprint:

- H5 is really dead. mcnemar_exact is a correct exact two-sided binomial — I verified all five committed fixture cases by hand against the implementation, including the n-k <= k overlap correction (b=5,c=5 → 1.0, b=8,c=0 → 0.0078125). The None-doctrine is mirrored faithfully from GateReport.
- The layering hairshirt was worn. adapters/search/protocols.py:24 declares a structural EventEmitter rather than importing kernel.bus; _parse_numstat is deliberately duplicated in composition.py:250 rather than importing the TCB's copy, with the reasoning written down. path_for() as a concrete-class-only escape hatch, justified by analogy to DefaultPolicyEngine.is_tainted, is exactly the right call.
- select() is rank-never-admit structurally, not by convention — it filters to the admitted subset before ranking and records which branch fired in selection_basis.
- ADR-0024's reasoning is correct and load-bearing: e0/runner.py imports agency, so the port's only legal adapter could never exist. Deleting the port rather than contorting the layers is the right resolution of open question §11.3.
- The finally + CancelScope(shield=True) around worktree release in best_of_n.py is the kind of thing that's usually found by a leaked-worktree incident, not written up front.

Defects worth fixing

1. k > 1 repetitions are silently discarded by every paired statistic. statistics.py:27 builds task_id -> resolved with last-write-wins, but runner.run_suite(k=3) appends k results per task_id into one flat tuple. So paired_deltas sees only the last repetition of each task, while compute_pass_rate (and therefore delta_pass_rate) averages all k. McNemar and the bootstrap CI are computed on a different sample than the headline delta they're used to judge. bench --runs 3 — the exact invocation your exit gate specifies — is the case that breaks. Either aggregate repetitions to a per-task rate before pairing, or key on (task_id, repetition).

2. An empty A/A run produces a floor everything beats. bootstrap_ci returns (0.0, 0.0) for empty deltas (statistics.py:86) and compute_noise_floor reports mean_delta=0.0. compare_runs then computes beats_noise_floor = delta > 0.0 and delta > 0.0 → True. That is H5's exact shape reintroduced through the back door: an unpairable calibration yields a verdict of "beats the floor" instead of None. NoiseFloor should carry an "uncomputable" state, and beats_floor should stay None when n_tasks == 0.

3. holm() is written, tested by fixture, and never called. Nothing in src/ sets adjusted_p_value — it is None on every path. Your exit gate says "Holm-corrected, k ≥ 3". As shipped, the correction exists as a function nobody invokes.

4. diversity_ratio is never reported. It's a method on BestOfNSearch (best_of_n.py:155) that no runner, reporter, or CLI path calls. It's a validity precondition on the exit gate; right now it can't be printed. Related: the denominator is len(branch_ids), but candidates cancelled by cancel_on_clean_admit never land in self._outcomes, so parallel mode will under-report diversity.

5. prune_on_first_gate_fail=True (the default) silently disables repair entirely. The repaequires not prune_on_first_gate_fail, so with shipped defaults max_repair_rounds=2 is deadcode. Worse, the flag doesn't do what its docstring claims — it says "releases worktree atease happens after the candidate finishes either way. It's currently a repair on/off switch
wearing a pruning name.

6. The escalation ladder caps repair at one round. should_escalate(failures=round_+1, …) with escalate_after_failures=2 and max_repair_rounds=2 stops after round 1. Also worth questioning conceptually: "escalate" in the corpus means widen the search, but here it's wired as a stop condition. ntended, say so in the docstring.

7. build_kernel now recursively constructs search machinery. composition.py:230 calls buillds a KernelCandidateExecutor, whose execute() calls build_kernel again — which builds
another BestOfNSearch and another GitWorktreeManager per candidate. Construction only, so ery candidate pays for a search stack it will never use, and you get N+1 worktree managers
pointed at one worktree_dir. Suggest the executor build its candidate kernel with search d

8. stagger_s sleeps inside the capacity limiter (best_of_n.py:238), holding a slot while iive (i * stagger_s). Move the sleep before async with limiter.

Process gaps (your stated remaining scope, sized)

- Zero tests reference any S4 code. grep across tests/ finds no hit for BestOfNSearch, Detlidate_task, GitWorktreeManager, mcnemar, bootstrap_ci, list_runs, ReplayVerified, ordiversity_ratio. The three tests/fixtures/statistics/*.json files are committed but no tesst first" standing rule was not followed for S4.0–S4.3 — worth knowing before the testpass, because writing tests after the fact is how #1 and #2 above survived.
- Test count moved 192 → 188. test_benchmark_scaffolding.py went 7 tests → 3 with the adapters/benchmark/ deletion. The deletion is right, but the monotonic-count rule in both plan documents is currently violated; the test pass needs to clear that and then some.
- bench-aa is a documented no-op. The guard on a missing s0-core.json is honest and well-ced-task suite, noise-floor.md, and RC-7's before-report are all still outstanding. Minor:the job installs with uv pip install --system then invokes uv run, which will likely miss
- RC-5 (ADR-0019/0020 → Accepted-Implemented) and RC-6 (0.60 re-execution threshold) are smplies.

Nothing here is architectural rework — #1 and #2 are the two that would put a false number'd fix those before the bench runs rather than during the test pass.