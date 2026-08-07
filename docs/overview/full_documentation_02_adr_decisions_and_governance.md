# AETHER Full Documentation — Part 2: Architectural Decisions & System Governance (ADRs 0001–0018)

> **Original Source Documents:** [`docs/decisions/README.md`](../decisions/README.md) and [`docs/decisions/0001-python-first-compiled-on-trigger.md`](../decisions/0001-python-first-compiled-on-trigger.md) through [`0018-agency-below-workflow.md`](../decisions/0018-agency-below-workflow.md).  
> **Purpose:** A complete, condensed reference catalog of AETHER's 18 Architectural Decision Records (ADRs). Every decision includes its binding rule, operational rationale, and explicit **reversal condition**.

---

## 1. Governance Rule: Decisions & Reversal Conditions

In AETHER, **a decision without an explicit reversal condition is invalid.** Decisions are classified into 4 statuses:
* **Accepted**: Binding rule in full force.
* **Accepted (provisional)**: Binding rule in force, naming the exact empirical measurement required to confirm or overturn it.
* **Superseded**: Replaced by a revised ADR.
* **Proposed**: Pending formal acceptance.

---

## 2. Complete Catalog of Architectural Decision Records (ADRs 0001 – 0018)

### [ADR-0001]: Python-First; Compiled Sidecars Only on a Measured Trigger
* **Status**: Accepted (provisional).
* **Decision**: AETHER is implemented in Python 3.13. Compiled sidecars (Rust/Go) are introduced only when an isolated benchmark timer proves Python execution is a bottleneck.
* **Reversal Condition**: If an adapter benchmark proves Python execution latency or memory overhead exceeds $+15\%$ of total step time, the adapter moves out-of-process to a compiled Rust/Go binary using wire-serializable JSON-RPC ([ADR-0005](../decisions/0005-eight-ports-adapter-first.md)).

---

### [ADR-0002]: No Number Before the Floor
* **Status**: Accepted.
* **Decision**: **No capability resolve rate or cost reduction claim may be published** before the A/A noise floor variance run is executed and cleared.
* **Rationale**: Eliminates false claims generated on uncalibrated instruments.
* **Reversal Condition**: None. This is a permanent measurement doctrine.

---

### [ADR-0003 (rev. 2)]: Statistical Admission Protocol & Derived $N$
* **Status**: Accepted (rev. 2).
* **Decision**: Candidate harness mutations are admitted only via **Exact McNemar paired testing** and **Holm–Bonferroni family-wise error adjustment** ($\alpha = 0.05$). Sample size $N$ is **dynamically derived for power $\ge 0.80$** (never fixed at $N=50$). Aggregation primary metric is Pass@1 on the first seeded pass. Cost per resolved task must be non-inferior ($\le +20\%$).
* **Reversal Condition**: Disproven only if a non-parametric test demonstrates equal statistical power with fewer required task runs.

---

### [ADR-0004]: Benchmark Targets: Lift is Committed; Absolutes are Provisional
* **Status**: Accepted (provisional).
* **Decision**: **Harness Lift ($\Delta$)** is the primary engineering target. Absolute resolve rates are provisional baselines tied to specific base models.
* **Reversal Condition**: Overturned if independent re-verification demonstrates absolute scores correlate perfectly with lift across all model families.

---

### [ADR-0005 (rev. 2)]: Eight Ports; Adapter-First Implementation
* **Status**: Accepted (rev. 2).
* **Decision**: System architecture is bounded by 8 wire ports (9 protocols). A port enters `src/aether/ports/` only in the same pull request as its first real adapter and its conformance test suite.
* **Reversal Condition**: Overturned if a new system capability cannot be modeled behind any existing port or growth-tier protocol without violating Invariant I2.

---

### [ADR-0006]: TCB Boundary & Meta-Loop Authority
* **Status**: Accepted.
* **Decision**: The Trusted Computing Base (TCB) consists of `kernel/`, `measurement/`, `workflow/`, benchmark task manifests, and CI workflows. The meta-loop may auto-commit mutations *only* within the mutable surface (`agency/`, prompts, topologies as data). TCB modifications require an explicit human-reviewed pull request.
* **Reversal Condition**: None. Fundamental security perimeter.

---

### [ADR-0007]: Architect/Editor Seam Built and Shipped Off
* **Status**: Accepted.
* **Decision**: Planning (`Architect`) and Code Generation (`Editor`) are decoupled into separate nodes. Highly expensive reasoning models are used for planning, while fast, low-cost local models perform code edits.
* **Reversal Condition**: Overturned if unified single-node generation achieves lower overall cost per resolved task than the decoupled seam.

---

### [ADR-0008]: Shell AST Classifies; Container Sandbox Contains
* **Status**: Accepted.
* **Decision**: Shell AST parsing classifies tool command risks and escalates permissions; it never acts as security containment. All execution containment is enforced by Podman `--network none` rootless containers.
* **Reversal Condition**: Overturned if container sandboxing can be bypassed without host OS privilege escalation.

---

### [ADR-0009]: Exit Gates Are the Schedule; Durations Are Tripwires
* **Status**: Accepted.
* **Decision**: Sprint completion and milestone advancement are governed strictly by passing verification exit gates, never by calendar elapsed time.
* **Reversal Condition**: None. Ensures quality over arbitrary calendar deadlines.

---

### [ADR-0010 (revised)]: 5 Context Prefix Layers & Cache Breakpoint Pinning
* **Status**: Accepted (provisional).
* **Decision**: Context prefixes are structured into 5 static layers (L1: System, L2: Tool Schemas, L3: Repo Brief, L4: Task Spec, L5: Dynamic History). Up to 4 provider `cache_breakpoint` pins are placed at layer transitions.
* **Reversal Condition**: Overturned if M2 ablation proves layer splitting produces lower prefix cache hit rates than single-block prompt formatting.

---

### [ADR-0011]: No LSP Adapter
* **Status**: Accepted.
* **Decision**: AETHER will not maintain a Language Server Protocol (LSP) adapter. Symbol indexing and AST lookups are handled via `TreeSitterIndexer` and native project toolchains.
* **Reversal Condition**: Overturned if an LSP server adapter demonstrates higher symbol resolution accuracy with lower token overhead than Tree-sitter.

---

### [ADR-0012]: Intellectual Property Protection via Packaging
* **Status**: Accepted.
* **Decision**: IP protection and code obfuscation are build/packaging concerns (`pyarmor` / compiled wheels), not architectural design constraints.
* **Reversal Condition**: None. Keeps application code clean and unpolluted.

---

### [ADR-0013 (rev. 2)]: Phased Workflow DAG & Bounded Repair Edge
* **Status**: Accepted (rev. 2).
* **Decision**: Workflow execution uses a phased DAG (`WorkflowStep[In, Out]`). Includes an explicit unrolled **Bounded Repair Edge** (`evaluate -> (fail, k) -> repair -> apply`, $k \le 3$).
* **Reversal Condition**: Overturned if cyclic graph execution models are proven to satisfy static termination verification without risking infinite loops.

---

### [ADR-0014]: Workflow Topology is Hash-Pinned Data
* **Status**: Accepted.
* **Decision**: Workflow topologies are declarative YAML/JSON data files validated against a static JSON schema and content-addressed via `sha256` hashes, not executable Python code.
* **Reversal Condition**: None. Ensures safe meta-loop topology mutations.

---

### [ADR-0015]: TaintGate Provenance Model & Closed Capability Policy
* **Status**: Accepted.
* **Decision**: All context spans carry provenance labels (`trusted-system`, `operator`, `agent`, `untrusted-external`, `untrusted-derived`). Tool execution requests widening capability fail closed if any input span is `untrusted-external` or `untrusted-derived`.
* **Reversal Condition**: None. Enforces prompt injection defense (Invariant I11).

---

### [ADR-0016]: MCP Integration Trust Model
* **Status**: Accepted.
* **Decision**: Model Context Protocol (MCP) servers register as adapters under `ToolRegistry`. All outputs returned from MCP tools are labeled `untrusted-external` at birth.
* **Reversal Condition**: None. Prevents third-party MCP tool responses from escalating security permissions.

---

### [ADR-0017]: Sub-Agent Capability Attenuation
* **Status**: Accepted.
* **Decision**: Sub-agents run as nested subgraph topologies. Capability permissions assigned to a sub-agent can only be equal to or narrower than its parent agent.
* **Reversal Condition**: None. Prevents sub-agents from acquiring unauthorized privileges.

---

### [ADR-0018]: Import Lattice Ordering (`agency` below `workflow`)
* **Status**: Proposed / Accepted in Composition Refactoring.
* **Decision**: In `.importlinter`, `workflow` sits above `agency`. Workflow nodes can import role specifications, context sources, and prompt assemblers from `agency/`. `agency/` can never import `workflow/`.
* **Reversal Condition**: Overturned if placing `agency` above `workflow` causes circular import dependencies with `kernel/`.
