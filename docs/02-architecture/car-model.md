---
status: normative
updated: 2026-07-29
---

# **Control-Agency-Runtime (CAR) Architecture**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Architectural Layering**

CAR isolates responsibilities into **three** layers:

1. **Control Layer**: security policy, token and spend budgets, context allocation, verification gates. Authorizes every effect before it happens and mints the capability tokens that permit it.
2. **Agency Layer**: deliberation, reasoning loops, context synthesis, sub-task decomposition, delegation. Holds **no reference to Runtime objects** and emits intents only.
3. **Runtime Layer**: sandboxed execution, worktree management, terminal capture, MCP tool drivers. Returns structured observations without touching agent memory or policy state.

```mermaid
graph TD
    subgraph AgencyLayer ["Agency Layer: Deliberation & Reasoning"]
        DMARTIC["DMARTIC Engine: System 1 / System 2"]
        Agency["Orchestrator & CandidateSearch"]
    end

    subgraph ControlLayer ["Control Layer: Policy & Security Gate"]
        PolicyEngine["PolicyEngine: authorize()"]
        Governor["ResourceGovernor: acquire_lease()"]
        ChokePoint["Single Dispatch Choke Point"]
    end

    subgraph RuntimeLayer ["Runtime Layer: Sandboxed Execution"]
        Workspace["Workspace: read / write / run"]
        Worktree["WorktreeManager: Git Worktrees"]
        MCP["MCP Tool Drivers"]
    end

    DMARTIC -->|Emits ToolCall Intent| ChokePoint
    ChokePoint --> PolicyEngine
    PolicyEngine -->|Mints Capability Grant| ChokePoint
    ChokePoint --> Governor
    ChokePoint -->|Dispatches with Grant| Workspace
    Workspace --> Worktree
    Workspace --> MCP
    Workspace -->|Returns Structured Observation| DMARTIC
```

**Native sidecars are not a fourth layer.** They are a deployment topology — an implementation detail of where a port's adapter happens to run — available to the Indexer and Runtime layers once measurement justifies them. Listing them as a peer of Control, Agency, and Runtime conflates logical architecture with physical process placement and obscures both.

## **Why Prose Is Not Enough**

Control must evaluate every agent tool request against a security policy before authorizing execution. An interception point must exist in the type system; a boundary that exists only in a document is bypassed by the first contributor in a hurry, and by the outer loop the moment it starts editing adapters.

## **Three Enforcement Mechanisms**

### 1. Capability Grants

Every side-effecting Runtime method executes only if backed by a `Grant` — minted only by `PolicyEngine.authorize()` and re-checked at the point of effect via `verify_grant`, never passed across a port signature. The contracts live in **`src/sagiha/ports/policy.py`** and **`src/sagiha/ports/workspace.py`**; the `Grant` model in **`src/sagiha/domain/control.py`**.

Grants are scoped to specific paths and tools, and they expire. Policy becomes non-bypassable by construction rather than by review.

### 2. Import-Graph Contracts

CI enforces that `agency/` cannot import `runtime/` or `adapters/`, via `import-linter` layer contracts. A violation fails the build. Architectural boundaries that are not mechanically checked erode silently, and this one is load-bearing for the entire security model.

### 3. A Single Dispatch Choke Point

Agency emits a `ToolCall`. The kernel resolves authorization, acquires a lease from the `ResourceGovernor`, dispatches, records the outcome, and returns an observation. There is exactly one path from intent to effect, which is also the single place where audit logging, budget accounting, effect classification, and secret redaction attach.

Grants never escape this dispatch choke point. The authoritative implementation is
**`src/sagiha/kernel/dispatch.py`**: authorize → verify a `grant_id` was minted → acquire lease →
`registry.dispatch(call)` → release lease → `record_outcome(grant_id, result)`. Note the registry
**never receives the `Grant`** — only the kernel-internal choke point correlates it by id
(supersedes the earlier `registry.dispatch(call, decision.grant)` sketch; see 2026-07-28 review
finding D1 and `src/sagiha/ports/tool_registry.py`).

## **Admission Control**

The `ResourceGovernor` bounds concurrency, spend, and sandbox count globally. Without it, parallel candidate exploration against a frontier API exhausts provider rate limits and spends wall-clock in retries — a budget stated in a document but never enforced at a call site is not a budget.

## **Cross-References**

* [Security & Threat Model](./security-and-threat-model.md) — what the sandbox boundary must actually stop.
* [Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md) — `PolicyEngine`, `Grant`, `ResourceGovernor` definitions.
* [Microkernel & Bus](./microkernel-and-bus.md) — where dispatch and replay live.
