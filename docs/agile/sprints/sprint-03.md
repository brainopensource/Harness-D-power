---
status: rationale
updated: 2026-08-06
---

# Sprint 03 Plan — The Repair Edge and the Floor

* **Goal**: Land the repair edge, containerise the judge, pin the first task manifest, and **take the A/A variance floor** — the number that unblocks every other number this project will ever publish.
* **Target Milestone**: [M1a+](../milestones.md#milestone-m1a--bounded-repair-edge) · [B3](../milestones.md#blocker-b3--isolated-evaluation-container--canary-test) · **A/A floor**
* **Tripwire Window**: 5 Business Days
* **Entry condition**: Sprint-02 complete. B1, B2b and B4 green — the floor's three preconditions.
* **Position in the plan**: [`sprints/README.md`](./README.md) — **this is the last sprint planned in full.** Sprint-04 onward is sized by what Task 5 measures.

> **This sprint is the hinge.** Before it, [ADR-0002](../../decisions/0002-no-number-before-the-floor.md) means the project reports no capability number. After it, admission sample sizes become derivable and the M2 ablations become schedulable. Nothing downstream can be planned honestly until Task 5 lands a real number.

---

## Sprint Backlog Items

### Task 1: Evaluation Container & B3 Canary (`TASK-016`) — closes B3
* **Target Seam**: `src/aether/adapters/sandbox/podman.py`, `containers/eval/`
* **Specification Pointer**: [`measurement.md` §2 (B3)](../../measurement.md#2-instrument-blockers), [`tech_stack_and_infra.md` §3.1](../../development/tech_stack_and_infra.md)
* **Acceptance Criteria**:
  1. Rootless Podman. `--network none`, `--cap-drop all`, `--security-opt no-new-privileges`, read-only root, `--pids-limit`, memory and CPU limits from the governor lease.
  2. **Two mounts only**: the task worktree (RW) and the pinned image layers (RO). No home, no sockets — **the `.pth` leak is fixed by construction**, not by remembering to avoid it.
  3. Container created **from image digest, never from tag**.
  4. **Canary: a deliberately broken candidate must fail evaluation.** This is the one instrument defect that *produced numbers*; the canary is what proves it is gone.

### Task 2: Task-Manifest Tooling & Validity Canary (`TASK-014`)
* **Target Seam**: `src/aether/measurement/manifest.py`, `src/aether/measurement/schemas/manifest_schema.yaml`
* **Specification Pointer**: [`measurement.md` §4.2–4.3](../../measurement.md#42-splits-and-why-they-are-pinned), [`schemas_and_contracts.md` §2](../../development/schemas_and_contracts.md)
* **Acceptance Criteria**:
  1. A task enters the manifest only if **the gold patch passes and the empty patch fails on our instrument** — bidirectional, per task.
  2. **Exclusions are published with a typed reason.** Silent exclusion is the overfitting vector, and roughly 30% of public Pro tasks were estimated broken in a mid-2026 audit.
  3. DEV / HOLDOUT / SEALED split assignment is pinned **in the manifest** (TCB), so it cannot drift per run.
  4. Manifest identity is the canonical-JSON sha256. A change is a new manifest with a new hash — never an edit.

### Task 3: Repair Node & Bounded Iteration (`TASK-023`) — closes M1a+
* **Target Seam**: `src/aether/workflow/nodes/repair.py`, `src/aether/agency/repair.py`, `workflows/linear_repair_v1.yaml`
* **Specification Pointer**: [ADR-0013 rev. 2](../../decisions/0013-workflow-dag-phased.md), [`milestones.md` M1a+](../milestones.md#milestone-m1a--bounded-repair-edge)
* **Acceptance Criteria**:
  1. `evaluate →(fail, k)→ repair → apply → evaluate`, statically unrolled to `max_iterations`.
  2. **The validator rejects a repair block with no `max_iterations`**, and one above the bound. Negative test required.
  3. **A `GateStatus.NONE` never routes into repair.** An instrument failure is not a repair candidate; repairing against one teaches the loop to fix our bugs instead of the task's.
  4. Each iteration reserves its own budget; exhausting it ends the loop, not the run.
  5. Test output enters context tail-biased — **the repair edge needs the traceback, not the pass list**.
* **Why it matters**: [`vision.md`](../../vision.md) §2 calls this *"the single largest lever on score in the entire system."* It ships here; whether it stays is decided by its ablation at M2.

### Task 4: Statistics Engine & Comparative Rig (`TASK-012`, `TASK-015`)
* **Target Seam**: `src/aether/measurement/{statistics,runner}.py`, `src/aether/measurement/families/`
* **Specification Pointer**: [ADR-0003 rev. 2](../../decisions/0003-statistical-admission-protocol.md), [`schemas_and_contracts.md` §3](../../development/schemas_and_contracts.md)
* **Acceptance Criteria**:
  1. `e0/statistics.py` ported **verbatim** — exact McNemar, Holm–Bonferroni, seeded bootstrap — with **provenance in the module docstring** ([`spec.md` §9](../../spec.md#9-standing-rules)). Pinned JSON fixtures pass.
  2. Derived-N power simulation is seeded and **re-runnable from a family file alone**.
  3. **The module refuses to compute corrected p-values for an undeclared family.** Enforcement, not discipline.
  4. `HarnessUnderTest` seam exists with the bare-model arm implemented. OpenHands as a second arm is *not* in this sprint.

### Task 5: Run the A/A Variance Floor — **the sprint's reason to exist**
* **Target Seam**: `docs/rationale/benchmarks/noise-floor.md`
* **Specification Pointer**: [`measurement.md` §3](../../measurement.md#3-the-aa-variance-floor), [ADR-0002](../../decisions/0002-no-number-before-the-floor.md)
* **Acceptance Criteria**:
  1. **Precondition, blocking**: Task 1's B3 canary executes **in the floor environment** and a deliberately broken candidate fails there. If it passes, the floor is blocked regardless of anything else in this plan.
  2. Two identical configurations, paired: same tasks, same order, same seeds. N ≥ 50 at the smoke floor, DEV split.
  3. **The run reports its discordance rates (p₀₁, p₁₀).** These are the input to every derived N under [ADR-0003](../../decisions/0003-statistical-admission-protocol.md) rev. 2 — without them no later admission run can be sized.
  4. Per-task wall-clock recorded. **This is what sizes M2-abl**, currently unsized in [`roadmap.md`](../roadmap.md).
  5. The run names its instrument: manifest hash, split, model fingerprint, topology hash, container digests, lockfile hash, seed.
* **On the result**: a floor that is *wide* is not a failure of this sprint. It is a measurement, and it changes N rather than invalidating the work. **A run that shows nothing is recorded as showing nothing** — that rule is the one that would have saved the predecessor.

---

## Milestone Gates Closed

| Gate | Closed by |
| :--- | :--- |
| B3 · 1–3 | Task 1 (Gate 3 jointly with Task 5) |
| M1a+ · 1–4 | Task 3 |
| A/A floor | Task 5 |

---

## What this sprint unblocks

| Blocked today | Unblocked by |
| :--- | :--- |
| Publishing **any** capability number ([ADR-0002](../../decisions/0002-no-number-before-the-floor.md)) | Task 5 |
| Sizing any admission run (derived N needs measured discordance) | Task 5 criterion 3 |
| Sizing M2-abl, and therefore counting the remaining sprints | Task 5 criterion 4 |
| The repair ablation — the first capability measurement this project takes | Tasks 3 + 5 |

## Explicitly not in this sprint

- **No ablations.** The floor is the denominator; running an ablation before it exists means "significant" has nothing to be significant against.
- **No OpenHands arm.** `TASK-015` builds the seam; the comparative run is scheduled after the floor and before any public claim.
- **No M2 memoization.** `TASK-032` is the first task of the next sprint, and it is the one M2 item whose 5-day tripwire is already sized.

## Daily Sprint Definition of Done

Unchanged from [Sprint-02](./sprint-02.md), plus:

10. **No number leaves this sprint without its instrument tuple.** A result without manifest hash, model fingerprint, topology hash and seed is not a result.
