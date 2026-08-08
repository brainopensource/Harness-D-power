---
status: rationale
retrieval: excluded
updated: 2026-08-06
---

# Exploratory Architectural Specs for System Evolution

**To**: Project Lead, Lead Architect, AI/ML Lead, and Core Engine Tech Leads  
**From**: Executive Leadership  
**Subject**: Authoring Pre-Phase 1 Specifications for Metaprogramming, Meta-Learning, and Telemetry

---

### Executive Context

Our Phase 0 architecture locks a clean, decoupled foundation: Hexagonal Ports and Adapters, Declarative Workflow Topologies (DAGs), an incorruptible TCB Evaluator, and gate-driven scheduling. 

As we prepare for Sprint-01 and foundational milestones, we must ensure that our system design accommodates long-term evolution into an autonomous, self-improving AGI task solver. We must design our interfaces today so that advanced capabilities can be plugged in later without requiring disruptive refactorings or breaking core abstractions.

We direct the technical leadership to author three high-level, exploratory Markdown specifications in `docs/`. You are free to propose the specific algorithms, paradigms, and design patterns that best fit our architectural constraints.

---

### Required Deliverables

#### 1. `docs/concepts/METAPROGRAMMING_STRATEGY.md`
*Goal*: Explore how metaprogramming and dynamic runtime inspection can enhance both task-solving and harness/loop engineering.
*Key Areas to Consider*:
- How AST-level inspection and dynamic transformations can complement or replace raw text-diff generation.
- How runtime tracing, dynamic frame inspection, or step decoration can provide rich execution context during task failures.
- How declarative workflow DAGs might leverage dynamic compilation or reflection while strictly maintaining TCB security boundaries.
- Recommendations for keeping core interfaces pure today so metaprogramming adapters can be introduced seamlessly in later phases.

#### 2. `docs/concepts/SELF_IMPROVEMENT_AND_AI_FLYWHEEL.md`
*Goal*: Define the high-level paradigm for transforming task execution history into continuous system self-improvement and meta-learning.
*Key Areas to Consider*:
- How verified task outcomes from the TCB Evaluator can act as ground-truth reward signals for model fine-tuning (SFT, DPO, RL).
- How successful tool usage and interaction patterns can be mined to synthesize new, reusable skills in the mutable surface.
- How Machine Learning or statistical models can be applied to optimize harness execution steps (e.g., dynamic model routing, RAG context selection, error log clustering).
- Alignment with our statistical admission protocols to guarantee that learned models or skills clear quality baselines before deployment.

#### 3. `docs/concepts/LOGGING_STATISTICS_TELEMETRY.md`
*Goal*: Design the data collection, trajectory logging, and statistical measurement infrastructure.
*Key Areas to Consider*:
- Schema principles for non-blocking capture of full execution trajectories (State, Action, Observation, Reward).
- Clear separation between *System Telemetry* (AETHER engine execution metrics, costs, latencies) and *Subject Telemetry* (codebase patches, test outputs, execution coverage).
- Statistical baselines and measurement standards for tracking performance gains, cost efficiency, and flakiness across benchmark sweeps.
- Data privacy, credential redaction, and offline storage formats suitable for data science and downstream ML pipelines.

---

### Guidance
Keep these documents concise, conceptual, and focused on **architectural extensibility**. Focus on defining clean boundaries, hooks, and contracts that allow these features to be developed as modular additions rather than core rewrites.



---

## Implementation Schedule: When Do These Land?

Writing and approving these three Markdown documents happens **now in Pre-Phase 1 (before Sprint-01 code execution)** to lock in the non-breaking interfaces.

The actual code implementation of these features is phased across our milestone DAG:


Pre-Phase 1         Sprint 01 / M0–M1a       Milestone M2–M3         Milestones M4–M6+
(Now)               (Immediate Code)         (Foundation Extensions)  (Autonomous Evolution)
+-----------------+ +-------------------+    +--------------------+  +-----------------------+
| Author 3 Specs  | | Clean Hexagonal   |    | • Initial Dual     |  | • M4: Meta-Loop v1    |
| Lock Interfaces | |   Engine Core     |    |   Telemetry Stream |  |   (Skill Mining/SFT)  |
| Zero Drift Gate | | • Basic Ports     |    | • Repair-Loop      |  | • M5: Workflow Self-  |
+-----------------+ | • Linear Pipeline |    |   Ablation         |  |   Redesign (YAML DAG) |
                    +-------------------+    | • Task Manifests   |  | • M6: AST Metaprogram.|
                                             +--------------------+  |   Safety & Auto-PRs   |
                                                                     +-----------------------+

### Breakdown by Phase:

1. **Pre-Phase 1 (Current Step)**:
* **Action**: Tech Leads write the 3 Markdown documents (`METAPROGRAMMING_STRATEGY.md`, `SELF_IMPROVEMENT_AND_AI_FLYWHEEL.md`, `LOGGING_STATISTICS_TELEMETRY.md`).
* **Goal**: Lock backend interfaces, event schemas, and boundary rules on paper so developers write zero redundant code during initial sprints.


2. **Sprint-01 through Milestone M1a (Immediate Core Development)**:
* **Focus**: Build the clean, minimal engine (`src/aether/`), migrate TCB paths, implement the 8 core ports, and run the linear `retrieve → generate → apply → evaluate` execution pipeline.
* **Metaprogramming/ML Status**: Stubs and interfaces only (zero complex ML overhead).


3. **Milestone M2 – M3 (Post-Baseline Extensions)**:
* **Focus**: Enable non-blocking event-bus telemetry logging (`LOGGING_STATISTICS_TELEMETRY.md`), run the first repair-loop ablation, build the SWE-bench paired-arm runner, and log execution trajectories into Parquet format.


4. **Milestone M4 – M6+ (Autonomous AGI & Meta-Learning Execution)**:
* **M4**: Deploy automated skill extraction and prompt/instruction mutation using logged trajectories (`SELF_IMPROVEMENT_AND_AI_FLYWHEEL.md`).
* **M5**: Enable autonomous workflow topology self-redesign using declarative YAML graph mutation under ADR-0014.
* **M6+**: Enable AST-driven metaprogramming safety checks (`METAPROGRAMMING_STRATEGY.md`) and automated agent PR generation with statistical gate validation.



---

## Reference

PHD Reference for Meta Harness and Meta Loop Engineering, AGI AETHER Evolution Path references https://lilianweng.github.io/posts/2026-07-04-harness/ 

Below some suggestions we can use from the references. It validates that our Phase 0 architectural decisions—specifically Hexagonal isolation (ADR-0005), declarative YAML DAGs (ADR-0014), and an immutable TCB judge (spec.md §4)—are perfectly aligned with state-of-the-art research (such as AHE, Self-Harness, and MCE). However, you should not change anything in our planned project right now. Our M0–M3 roadmap intentionally focuses on building the clean, deterministic engine and event bus substrate that these algorithms require; attempting to integrate meta-learning loops earlier would introduce premature complexity and break our execution gates. Keep the current plan locked for Sprint-01 through M3, and use this research as the explicit design specification for Milestones M4 through M6+, where AHE's evidence-grounded mutation rules and Self-Harness's failure-clustering loops will plug cleanly into our pre-designed evolution/ surface as outer adapters without requiring any core refactoring.

### PHD White Paper About Self-Improvement and Meta Harness or Meta Engineering

# Executive Briefing: Harness Engineering for Self-Improvement

**Source**: *Harness Engineering for Self-Improvement* (Lilian Weng, Jul 2026)

**Core Thesis**: Near-term Recursive Self-Improvement (RSI) will not begin with LLMs directly rewriting their own weights. Instead, it will be driven by **Harness Engineering**—optimizing the deployment runtime, context management, workflow DAGs, and evaluation machinery surrounding base models.

---

## 1. Fundamental Concepts & Design Patterns

A **harness** is the orchestration layer surrounding a base model (planning, state management, tool execution, context assembly, and evaluation).

### Core Design Patterns

* **Workflow Automation**: Goal-oriented loops (`plan → execute → observe/test → repair → execute`). Emphasizes analyzing execution trajectories via an agent runtime rather than static prompts.
* **File System as Persistent Memory**: Storing experiment logs, code diffs, error traces, and long-horizon artifacts directly in standard files (accessed via `bash`/`glob`/`grep`) to avoid overflowing model context windows.
* **Sub-agents & Backend Jobs**: Spawns parallel, inspectable worker processes with explicit log tracking and status files to explore multiple hypotheses concurrently without context contamination.

---

## 2. Taxonomy of Harness Optimization Paradigms

The target of optimization moves up the abstraction stack:

`Instruction Prompts` $\rightarrow$ `Structured Context` $\rightarrow$ `Workflow Graphs` $\rightarrow$ `Harness Source Code` $\rightarrow$ `Meta-Optimizers`

```
   +-----------------------------------------------------------------+
   |                       Meta-Harness / AHE                        |
   |              (Outer Loop: Code & Skill Mutation)                |
   +-----------------------------------------------------------------+
                                    |
                                    v
   +-----------------------------------------------------------------+
   |                  Declarative Workflow DAGs                      |
   |               (ADAS / AFlow / Graph Search)                     |
   +-----------------------------------------------------------------+
                                    |
                                    v
   +-----------------------------------------------------------------+
   |                     Base Harness & Engine                       |
   |           (ACE / MCE Context Playbooks + Sandboxes)             |
   +-----------------------------------------------------------------+

```

### Key Optimization Frameworks

| Optimization Level | Paradigm / Paper | Core Mechanism |
| --- | --- | --- |
| **Context Level** | **ACE** *(Zhang et al. 2026)* | Maintains an evolving playbook of itemized `(id, description)` bullet points via generator, reflector, and curator roles. |
| **Context Level** | **MCE** *(Ye et al. 2026)* | Bi-level optimization: outer loop evolves context skills (`skill.md`), inner loop optimizes dynamic context functions. |
| **Workflow Level** | **ADAS** *(Hu et al. 2025)* | Meta-agent programs new agent workflows in raw code and evaluates them against an archive of historical designs. |
| **Workflow Level** | **AFlow** *(Zhang et al. 2025)* | Formulates workflows as graphs (nodes = LLM actions, edges = code logic) optimized via Monte Carlo Tree Search (MCTS). |
| **Harness Code** | **STOP** *(Zelikman et al. 2024)* | Recursively improves the optimizer program itself using downstream task utility scores. |
| **Harness Code** | **Self-Harness** *(Zhang et al. 2026)* | Loop of *weakness mining* (error pattern clustering) $\rightarrow$ *bounded proposal* $\rightarrow$ *held-in/held-out regression validation*. |
| **Harness Code** | **AHE** *(Lin et al. 2026)* | Enforces 3 observability pillars (Component, Experience, Decision) where every edit is an evidence-grounded, falsifiable claim. |
| **Evolutionary** | **AlphaEvolve / DGM** *(2025)* | Uses evolutionary search, code diff generation, and fitness tracking over pools of harness code and meta-prompts. |
| **Joint Weights/Harness** | **SIA** *(Hebbar et al. 2026)* | Feedback agent dynamically decides whether to update the non-parametric harness or fine-tune model parameters. |

---

## 3. Critical Failure Modes & Open Bottlenecks

1. **Weak / Fuzzy Evaluators**: Objective verifiers (unit tests, math checks) work well; research taste, long-term maintainability, and open-ended discovery lack fast, non-hackable evaluators.
2. **Reward Hacking & Overfitting**: Self-improving loops overfit to specific benchmark unit tests or judge quirks. Mitigated by keeping verifiers/solvers read-only outside the mutation boundary (as in AHE).
3. **Implementation Drift**: Under complex execution pressure, agents tend to abandon original novel designs and collapse into standard training-data defaults or shortcuts ("numerical duct tape").
4. **Diversity Collapse**: Evolutionary loops exploit known high-reward patterns, discarding exploratory paths that initially look worse under current evaluators.

---

## 4. Benchmark Index

* **PaperBench** *(Starace et al. 2025)*: Replicating 20 ICML oral papers from scratch (8,316 fine-grained rubrics).
* **CORE-Bench** *(Siegel et al. 2024)*: Computational reproducibility across 90 scientific papers.
* **ScienceAgentBench** *(Chen et al. 2025)*: Data-driven scientific discovery tasks (chemistry, biology, math, geography).
* **RE-Bench** *(Wijk et al. 2025)*: 7 open-ended ML research-engineering environments (kernel optimization, scaling laws).
* **MLE-bench** *(Chan et al. 2024)*: 75 Kaggle machine learning engineering competitions.
* **KernelBench** *(Ouyang et al. 2025)*: Writing correct, high-performance GPU kernels in PyTorch.

---

## 5. Primary References

* **ACE**: `arXiv:2601.07432` — Agentic Context Engineering
* **MCE**: `arXiv:2601.21557` — Meta Context Engineering via Skill Evolution
* **Meta-Harness**: `arXiv:2603.28052` — End-to-End Optimization of Model Harnesses
* **AFlow**: `ICLR 2025` — Automating Agentic Workflow Generation via MCTS
* **Self-Harness**: `arXiv:2606.09498` — Harnesses That Improve Themselves
* **AHE**: `arXiv:2604.25850` — Observability-Driven Automatic Evolution of Coding-Agent Harnesses
* **Darwin Gödel Machine (DGM)**: `arXiv:2505.22954` — Open-Ended Evolution of Self-Improving Agents
* **Primary Publication Link**: [Lilian Weng — Harness Engineering for Self-Improvement (2026)](https://lilianweng.github.io/posts/2026-07-04-harness/)

