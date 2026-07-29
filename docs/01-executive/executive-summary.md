# **Executive Summary: SAGIHA Meta-Harness**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Overview**
SAGIHA (Super AGI Harness Agent) is a meta-harness that turns frontier LLMs into an autonomous software engineering agent, operating independently or with a human in the loop. It is scoped and measured as a coding harness: every capability claim is stated as a benchmark with a threshold.

## **Key Architectural Pillars**

* **CAR with structural enforcement**: Control (policy, budget, gates), Agency (deliberation, no shell access), Runtime (sandboxed execution). Agency holds no reference to Runtime objects; every effect passes through one dispatch choke point where the Policy Engine mints a capability `Grant` that Runtime methods require. Enforced by construction and by CI import contracts, not by convention. Sidecars are a deployment topology, not a layer.
* **Dual-Process Execution**:
  * **System 1 (Fast):** direct ReAct for localized, low-complexity tasks.
  * **System 2 (Deliberate):** verifier-guided **best-of-N with sequential repair** across parallel worktrees. Deliberately not MCTS — tree search with backpropagation is deferred until a calibrated value model exists, since each expansion costs a full agent run plus a test suite.
* **Memory split by epistemics**: deterministic code structure (imports, calls, ownership, co-change) derived exactly from Tree-sitter and git; episodic and decision memory, where facts genuinely age, modelled bi-temporally. SQLite baseline throughout.
* **Protocol standardized**: MCP for vertical tool integration; A2A adopted when a genuinely remote peer agent exists.
* **Bounded self-improvement (RHI)**: the outer loop optimizes prompts, retrieval parameters, and non-Control adapters — never the evaluator, policy engine, gates, or benchmark definitions. Deployment requires human sign-off.

## **Non-Negotiable Invariants**

1. **The sandbox is the security perimeter.** Command-string blocklisting is a usability guardrail; if the agent has a shell, it has whatever the sandbox grants that shell.
2. **Repository and web content is data, never instruction.** Indirect prompt injection is the primary threat to an autonomous agent holding a shell and credentials.
3. **A candidate never scores itself.** Evaluation runs against a pristine, read-only injected copy of the test suite; modifying test files is a hard gate failure.
4. **No `Dict[str, Any]` crosses a port**, and no port speaks storage language. Contracts are verified by per-port conformance suites parametrized over every adapter.
5. **Measure before replacing.** Every advanced component carries a trigger condition, not a calendar slot.

## **What This Revision Corrected**

The prior specification's ports were storage drivers rather than domain contracts, and would have broken at the first adapter migration its own roadmap called for. Its Control layer existed only in prose, with no interception point in the type system. Its self-improvement loop could edit its own grader and deploy without review. And its complexity was front-loaded onto quantization, tree search, compiled sidecars, and temporal graphs for facts a parser already knows — while the components that actually determine whether a coding agent works went unspecified: the model port, context and cache layout, chunking strategy, edit application, and error recovery.

See [Phased Migration Matrix](../07-roadmap/phased-migration-matrix.md) for the vertical slice plan and [Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md) for the corrected contracts.
