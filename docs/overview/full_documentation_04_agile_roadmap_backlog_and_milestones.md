# AETHER Full Documentation — Part 4: Agile Execution Roadmap, Backlog & Milestones

> **Original Source Documents:** [`docs/agile/roadmap.md`](../agile/roadmap.md), [`docs/agile/backlog.md`](../agile/backlog.md), [`docs/agile/milestones.md`](../agile/milestones.md), and [`docs/agile/sprints/`](../agile/sprints/).  
> **Purpose:** A complete, condensed reference manual for AETHER's phased development roadmap, technical backlog, milestone exit gates, and sprint execution history.

---

## 1. Phased Execution Roadmap

AETHER development is governed by a **two-track normative roadmap** ([ADR-0013](../decisions/0013-workflow-dag-phased.md) and [`measurement.md`](../measurement.md)):

```
TRACK 1: EXECUTION ARCHITECTURE
M0 (Pure Domain) -> M1a (Skeleton) -> M1a+ (Bounded Repair) -> M1a++ (Context Lift)
                  -> M1a++R (Instrument Restoration) -> M1b (Capability Composition)
                  -> M2 (Memoization) -> M3 (Dynamic Branching)

TRACK 2: MEASUREMENT & INSTRUMENTATION
B1 (Repo Cache) + B2 (Local Endpoint) -> B4 (Typed Instrument Error)
                                       -> M1a++R (I7 Gate & Test Injection Removal)
                                       -> A/A Noise Floor Run -> B3 (Sandbox Container)
```

---

## 2. Track 1: Execution Architecture Milestones

| Milestone | Scope & Core Features | Verification Exit Gate | Status |
| :--- | :--- | :--- | :--- |
| **M0** | Pure domain models, 9 wire protocols, TCB path migration. | All core interfaces moved to `src/aether/ports/` and `src/aether/domain/`. CI green. | **Complete** |
| **M1a** | Walking Skeleton: 4-node linear workflow (`retrieve -> architect -> generate -> apply`). | End-to-end task execution passing through single dispatch choke point (`dispatch.py`). | **Complete** |
| **M1a+** | Bounded Repair Edge: unrolled repair loop (`evaluate -> (fail, k) -> repair -> apply`, $k \le 3$). | Unit tests proving repair loop retries failing candidate patches up to max $k$. | **Complete** |
| **M1a++** | Inner Loop Context Lift: AST codeblock auto-normalizer, traceback trimmer, entry file auto-discovery. | Local Ollama (`qwen2.5-coder:32b`) run resolving tasks without context window overflow. | **Complete** |
| **M1a++R** | **Instrument Restoration**: Enforce I7 (`tests_unmodified`), demote test-source injection to named ablation arm. | CI green on I7 gate; test-source injection removed from default baseline run. | **Active (Sprint 4)** |
| **M1b** | **Capability & Composition Layer**: Create `agency/`, generic `ModelNode`, `RoleSpec` catalog, `RunConfig`. | All node classes refactored to `ModelNode`; `workflow` placed above `agency` in `.importlinter`. | **Next** |
| **M2** | Per-Node Memoization (`sha256` input digests) & Ablation Execution Engine. | Duplicate node inputs skip LLM calls; ablation runner computes paired McNemar statistics. | Planned |
| **M3** | Dynamic Branching, Best-of-N Fan-out, & Statistical Admission Protocol. | Best-of-N parallel candidate branching with exact McNemar statistical gate admission. | Planned |

---

## 3. Track 2: Measurement & Instrument Blockers

| Blocker | Scope & Definition | Prerequisite For | Status |
| :--- | :--- | :--- | :--- |
| **B1** | Upstream repository caching to prevent network timeouts during benchmark runs. | Milestone M1a | **Complete** |
| **B2a/b** | Local LLM endpoint reachability & `ModelProvider` adapter conformance tests. | Milestone M1a | **Complete** |
| **B4** | Typed Instrument Error vs. Test Failure: `GateReport` returns `PASSED`, `FAILED`, or `NONE`. | A/A Noise Floor | **Complete** |
| **A/A Floor** | Statistical variance run estimating baseline instrument noise; derives sample size $N$. | Public Claims (ADR-0002) | **Active (Sprint 4)** |
| **B3** | Isolated Evaluation Container: Podman `--network none` rootless container with canary gate. | Milestone M3 | Planned |

---

## 4. Technical Backlog Summary (`TASK-000` – `TASK-061`)

Key active and upcoming tasks from [`docs/agile/backlog.md`](../agile/backlog.md):

* **`TASK-000`**: Migrate predecessor paths to `src/aether/` and update `.importlinter` rules (Owner: Lead Architect, Complexity: 1).
* **`TASK-022`**: Implement `EventBus` with dual drop policies (`never` vs `drop_oldest`) (Owner: Backend Eng, Complexity: 2).
* **`TASK-024`**: Structural Context Compactor for long-horizon task execution (Owner: AI Eng, Complexity: 3).
* **`TASK-026`**: SQLite Trajectory Store adapter for durable append-only event logging (Owner: Backend Eng, Complexity: 2).
* **`TASK-042`**: Implement `RoutingModelProvider` adapter for per-node LLM cost routing (Owner: Infrastructure Eng, Complexity: 3).
* **`TASK-050`**: Move payload models (`ReadArgs`, `WriteArgs`, `ShellArgs`) to `domain/effects.py` to fix A1 (Owner: Core Eng, Complexity: 1).
* **`TASK-051`**: Consolidate `_worktree_path` into single `WorktreeRef` method to fix A2 (Owner: Core Eng, Complexity: 1).
* **`TASK-053`**: Submit ADR-0018 and update `.importlinter` to place `workflow` above `agency` (Owner: Lead Architect, Complexity: 1).
* **`TASK-054`**: Implement generic 20-line `ModelNode` class replacing monolithic nodes (Owner: AI Eng, Complexity: 3).
* **`TASK-055`**: Create 6 Core Capability Protocols under `src/aether/agency/capabilities/` (Owner: Core Eng, Complexity: 3).
* **`TASK-056`**: Implement `LayeredAssembler` enforcing L1–L5 prompt layers and cache pins (Owner: AI Eng, Complexity: 2).
* **`TASK-057`**: Implement frozen `RunConfig` domain model and autogenerated schemas (Owner: Backend Eng, Complexity: 2).
* **`TASK-058`**: Implement Topology Fragments (`fragment_id`) in `workflow/schema.py` and expander (Owner: Core Eng, Complexity: 3).

---

## 5. Tripwire & Schedule Governance Policy ([ADR-0009](../decisions/0009-gates-are-the-schedule.md))

1. **Gates are the Schedule**: Phase completion and milestone advancement are strictly governed by passing verification exit gates.
2. **Durations are Tripwires**: Listed phase durations are monitoring tripwires, not fixed calendar deadlines.
3. **Scope-Review Trigger**: If a phase exceeds its tripwire duration by **$>50\%$**, an immediate scope-review meeting is triggered to trim non-essential features. **Exit gates are never skipped or lowered.**
