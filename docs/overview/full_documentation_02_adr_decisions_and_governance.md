---
status: rationale
updated: 2026-08-07
---

# AETHER Full Documentation — Part 2: Architectural Decisions & System Governance (ADRs 0001–0018)

> **Original Source Documents:** [`docs/decisions/README.md`](../decisions/README.md) and [`docs/decisions/0001-python-first-compiled-on-trigger.md`](../decisions/0001-python-first-compiled-on-trigger.md) through [`0018-agency-below-workflow.md`](../decisions/0018-agency-below-workflow.md), [`docs/concepts/rewrite_v300_decision_record.md`](../concepts/rewrite_v300_decision_record.md), and [`docs/concepts/rewrite_v300_decision_brief.md`](../concepts/rewrite_v300_decision_brief.md).

---

## 1. Governance Framework & Decision Taxonomy

In AETHER, **a decision without an explicit reversal condition is invalid.** Architectural Decision Records (ADRs) govern all structural, statistical, security, and execution boundaries in the system.

### Decision Classifications
* **Accepted**: Binding rule in full force.
* **Accepted (provisional)**: Binding rule in force, naming the exact empirical measurement required to confirm or overturn it.
* **Superseded**: Replaced by a revised ADR.
* **Proposed**: Pending formal acceptance.

---

## 2. Complete Reference Catalog of ADRs (0001 – 0018)

### ADR-0001: Python-First Implementation, Rust/Compiled Triggered on Performance Fork (F1)
* **Status**: Accepted (provisional)
* **Context**: AETHER core is implemented in pure Python (>=3.13) with stdlib `asyncio`. Rewrite debates frequently advocate Rust or C++ for performance.
* **Binding Decision Rule**: The harness is written in Python first. Rewrite of performance-critical components to compiled modules (Rust via PyO3) is triggered **only when empirical timers cross specific thresholds (F1 fork)**.
* **Operational Rationale**: Python maximizes iteration speed during architectural research. Premature optimization in Rust slows down DAG and protocol experimentation.
* **Reversal Condition (F1 Trigger)**: If worktree creation exceeds 100ms per candidate or AST parse-and-validate timers cross 200ms on a 1M-LOC repository in CI, the affected sub-component is promoted to Rust.

---

### ADR-0002: No Number Before the Floor
* **Status**: Accepted
* **Context**: Predecessor efforts attempted to report capability resolve rates before characterising instrument noise, resulting in uncalibrated numbers.
* **Binding Decision Rule**: **Instruments are built and verified before the capability they measure.** No benchmark number, win rate, or resolve rate is published or recorded until the A/A noise floor has been taken and derived $N$ established.
* **Operational Rationale**: Measuring capability on an uncalibrated instrument conflates harness failure with instrument flakiness.
* **Reversal Condition**: None. This is a foundational measurement doctrine rule.

---

### ADR-0003: Statistical Admission Protocol (rev. 2)
* **Status**: Accepted
* **Context**: Evaluating whether a harness feature (e.g., repair edge, context layer) is a true capability improvement requires statistical rigor to prevent noise admission.
* **Binding Decision Rule**:
  1. Admission requires exact McNemar test comparing paired candidate vs. baseline outcomes on identical tasks.
  2. Family-wise error rate ($\alpha = 0.05$) controlled via Holm–Bonferroni step-down correction.
  3. Sample size ($N$) is **derived from the A/A floor discordance rate** ($p_{01}, p_{10}$) via Monte Carlo simulation targeting $\text{power} \ge 0.80$.
  4. The statistics module (`measurement/statistics.py`) **refuses to compute corrected p-values for an undeclared family**.
* **Reversal Condition**: If derived $N$ exceeds 1,000 tasks due to extreme instrument variance, admission pauses until instrument noise is engineered down.

---

### ADR-0004: Dual-Metric Benchmark Targets
* **Status**: Accepted
* **Context**: Absolute benchmark resolve rates (Pass@1) vary widely depending on the underlying base model used (e.g., Sonnet vs. Qwen vs. Llama).
* **Binding Decision Rule**: Every publication MUST report both **Absolute Resolve Rate** and **Harness Lift ($\Delta$)**. The target is $\Delta \ge +10$ percentage points over unassisted bare-model performance.
* **Operational Rationale**: Lift isolates harness engineering quality from base model capabilities.
* **Reversal Condition**: If a base model achieves $\ge 95\%$ unassisted resolve rate (rendering $\Delta \ge +10$ mathematically impossible), the target transitions to error-margin reduction.

---

### ADR-0005: Eight Wire Ports, Adapter-First Architecture (rev. 2)
* **Status**: Accepted
* **Context**: Coupling code to external libraries or specific LLM APIs prevents modular testing and architectural substitutability.
* **Binding Decision Rule**: All I/O occurs behind 9 wire-serializable `Protocol` interfaces across 8 boundaries in `src/aether/ports/`. Every port lands with a mock adapter and a parametrized conformance suite (`tests/conformance/`).
* **Operational Rationale**: Ensures every port can be implemented over a wire (RPC/HTTP) and tested in memory.
* **Reversal Condition**: If a port boundary adds $>5\%$ wall-clock latency overhead across 10,000 turns, the interface may be refactored into direct zero-copy buffers.

---

### ADR-0006: TCB Boundary & Meta-Loop Authority
* **Status**: Accepted
* **Context**: Self-modifying meta-loops risk corrupting their own evaluation gates or bypassing security policies.
* **Binding Decision Rule**: The Trusted Computing Base (TCB) consists of `kernel/` (dispatch, bus, governor, policy), `measurement/` (evaluator, gates, statistics), task manifests, and CI workflows. Meta-loops and autonomous agents **can NEVER write to TCB paths**.
* **Operational Rationale**: Security and measurement integrity require an immutable judge.
* **Reversal Condition**: None. TCB isolation is a non-negotiable architectural invariant (I8).

---

### ADR-0007: Architect / Editor Seam
* **Status**: Accepted (provisional)
* **Context**: High-reasoning models (Architect) excel at planning but burn tokens on editing; fast models (Editor) excel at surgical diffs.
* **Binding Decision Rule**: Decouple planning (`ArchitectStep`) from code modification (`EditorStep`) via a composite `RoutingModelProvider`. Default configuration ships disabled (single-model baseline).
* **Operational Rationale**: Dual-model routing lowers cost per resolved task while improving reasoning quality.
* **Reversal Condition**: If the dual-model arm fails to clear the A/A noise floor at lower cost per resolved task under ADR-0003, the seam is deleted outright.

---

### ADR-0008: Shell AST Classifier Surface
* **Status**: Accepted
* **Context**: Shell tool execution poses command-injection security risks.
* **Binding Decision Rule**: A shell AST parser (`tree-sitter-bash`) classifies command risk (`Reject | AskRuleMatch | AskFailClosed`). **The parser is an optimization, NOT a security perimeter.** The container sandbox is the sole security boundary.
* **Operational Rationale**: Static analysis of shell scripts is undecidable; defense-in-depth requires container isolation.
* **Reversal Condition**: If container sandbox isolation is proven vulnerable to breakout without AST pre-filtering, AST classification is promoted to a hard TCB gate.

---

### ADR-0009: Gates Are the Schedule
* **Status**: Accepted
* **Context**: Fixed calendar deadlines cause teams to skip quality gates or ship uncalibrated code.
* **Binding Decision Rule**: A phase or milestone is complete **only when all its exit gates pass cleanly in CI**. Timeline estimates are tripwires for scope review, not deadlines for skipping gates.
* **Operational Rationale**: Preserves falsifiability and engineering integrity.
* **Reversal Condition**: If a tripwire fires repeatedly with zero scope adjustment, the tripwire policy itself is re-estimated or restructured.

---

### ADR-0010: Five-Layer Context Prefix Architecture
* **Status**: Accepted
* **Context**: LLM prompt caching (Anthropic / OpenAI) requires byte-identical prefix stability across turns.
* **Binding Decision Rule**: Prompts assemble into 5 fixed layers (L1 System, L2 Repo Structure, L3 Issue Brief, L4 History, L5 Scratchpad) with explicit `cache_breakpoint` pins. L1–L4 are append-only within a run.
* **Operational Rationale**: Maximizes prompt cache hit rates ($\ge 80\%$), reducing wall-clock time and token costs.
* **Reversal Condition**: If a provider API removes prefix-caching support or penalizes multi-layer breakpoint headers, assembly collapses to dynamic single-string formatting.

---

### ADR-0011: No LSP Adapter (Syntax Tier Only)
* **Status**: Accepted
* **Context**: Integrating Language Server Protocol (LSP) servers introduces heavy background processes, language-specific dependencies, and non-deterministic state.
* **Binding Decision Rule**: AETHER uses static `tree-sitter` AST parsers for symbol extraction, definition jumping, and call-graph analysis. No stateful LSP servers are permitted in the default execution path.
* **Operational Rationale**: Keeps worktree environments lightweight, deterministic, and fast.
* **Reversal Condition**: If static `tree-sitter` indexing fails to resolve symbol dependencies for $>15\%$ of SWE-bench tasks compared to LSP, an isolated LSP sidecar may be evaluated.

---

### ADR-0012: Intellectual Property Protection via Package Boundaries
* **Status**: Accepted
* **Context**: Protecting proprietary harness capabilities while maintaining open-source wire ports.
* **Binding Decision Rule**: Public wire protocols (`src/aether/ports/`) and domain models (`src/aether/domain/`) are open source. Specialized strategy implementations register via Python entry points or closed packages.
* **Operational Rationale**: Clean architectural decoupling between open specification and proprietary execution modules.
* **Reversal Condition**: None.

---

### ADR-0013: Workflow DAG Phased Rollout
* **Status**: Accepted
* **Context**: Monolithic execution loops are difficult to ablate, benchmark, and debug.
* **Binding Decision Rule**: Execution is structured as a declarative Workflow DAG (`WorkflowStep[In, Out]`), rolled out in phases: M0 (Domain) $\rightarrow$ M1a (Skeleton) $\rightarrow$ M1a+ (Repair) $\rightarrow$ M1a++ (Context Lift) $\rightarrow$ M1b (Composition) $\rightarrow$ M2 (Memoization) $\rightarrow$ M3 (Branching).
* **Operational Rationale**: Allows incremental validation and statistical ablation of each graph feature.
* **Reversal Condition**: None.

---

### ADR-0014: Workflow Topology Is Data
* **Status**: Accepted
* **Context**: Hardcoding workflow graphs in Python prevents meta-loop optimization and dynamic topology swappability.
* **Binding Decision Rule**: Workflow graphs are defined as declarative YAML topologies (`schema_version: 1.0.0`). The `TopologyValidator` enforces 5 static checks (socket compatibility, evaluator termination, bounded iteration, declared fan-out, budget annotations) before execution.
* **Operational Rationale**: Enables topological data validation and offline machine self-redesign without arbitrary Python code generation.
* **Reversal Condition**: If YAML graph validation introduces prohibitive runtime overhead ($>500\text{ms}$), pre-compiled binary topologies may be adopted.

---

### ADR-0015: TaintGate Provenance Model
* **Status**: Accepted
* **Context**: Indirect prompt injection via malicious code comments, issue descriptions, or tool outputs can manipulate agent behavior.
* **Binding Decision Rule**: All context spans carry explicit provenance labels. Any capability grant request that widens authority fails closed if any input span is `untrusted-external` or `untrusted-derived`.
* **Operational Rationale**: Mechanically blocks prompt-injection attacks from escalating capabilities.
* **Reversal Condition**: If TaintGate causes false-positive capability blocks on $>5\%$ of legitimate repair operations, policy rules must be refined against the adversarial injection corpus.

---

### ADR-0016: Model Context Protocol (MCP) Trust Model
* **Status**: Accepted
* **Context**: Integrating third-party MCP tool servers expands the attack surface.
* **Binding Decision Rule**: MCP servers execute in isolated sub-processes. Tools registered from external MCP servers are automatically assigned `untrusted-external` taint and require explicit capability leases.
* **Operational Rationale**: Prevents external tool integration from compromising TCB integrity.
* **Reversal Condition**: None.

---

### ADR-0017: Subagent Capability Attenuation
* **Status**: Accepted
* **Context**: Invoking subagents with full parent authority risks cascading failures or unconstrained side-effects.
* **Binding Decision Rule**: Subagents receive an **attenuated `DispatchFacade`** at construction. A subagent's capability set is strictly a subset of its parent's grant; capabilities can only narrow down the hierarchy.
* **Operational Rationale**: Enforces least-privilege security across agent execution trees.
* **Reversal Condition**: None.

---

### ADR-0018: Agency Below Workflow in Import Lattice
* **Status**: Accepted
* **Context**: `workflow/` nodes needed to instantiate `agency/` role capabilities (`RoleSpec`, `PromptAssembler`), but `.importlinter` treated them as independent siblings.
* **Binding Decision Rule**: Update `.importlinter` lattice to place `workflow` above `agency` (`engine > workflow > agency > kernel > adapters > ports > domain`). `agency` still cannot import `workflow`, `kernel`, `measurement`, or the evaluator.
* **Operational Rationale**: Cleans up node initialization while preserving TCB isolation.
* **Reversal Condition**: If an import path allows `agency/` to transitively import `measurement/evaluator.py`, this lattice update is immediately reverted.
