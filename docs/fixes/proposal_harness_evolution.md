---
status: rationale
retrieval: excluded
updated: 2026-08-06
---

# PROPOSAL — Harness Evolution Blueprint

**Question answered**: does the Phase 0/1 foundation (`spec.md`, `vision.md`, ADRs) evolve into an advanced autonomous system — knowledge graphs, long-term memory, MCP, multi-agent orchestration, self-modification — without a rewrite and without stalling execution now?

**Answer**: yes, with one architectural amendment. The seams already ratified (I3 wire-serializable ports, growth-tier port rule, ADR-0006 mutable-surface model, workflow-DAG-as-execution-structure, headless event stream) carry almost the entire end-state. The single missing load-bearing element is that **workflow topology is currently code**, which caps both human loop-engineering cadence now and machine self-redesign later. Everything else is additive.

---

## 1. Mapping the end-state onto existing seams

The discipline throughout: **every future capability is an adapter behind an existing or growth-tier port, a node in the workflow graph, or data in the mutable surface — never a new privileged pathway.** Anything that cannot be expressed in one of those three forms is a signal the architecture is wrong, not that a fourth form is needed.

| Future capability | Lands as | Seam already ratified | New decisions needed |
|:--|:--|:--|:--|
| **Long-term memory** | Adapter behind growth-tier `Memory` port | ADR-0005 growth tier | Memory *content* is meta-loop-mutable (it is learned state) → must be classified in the ADR-0006 table; memory writes route through dispatch like any effect; retrieved memories carry `untrusted-derived` provenance through the TaintGate (a memory poisoned by injected content must not launder into instruction authority) |
| **Knowledge graph (code)** | Adapter behind growth-tier `CodeGraph` port | ADR-0005; ADR-0011 already positions tree-sitter as the syntax substrate feeding it | None — enters with its first adapter, admitted only if its retrieval ablation clears the floor (same bar as everything) |
| **MCP tools** | One adapter: `McpToolRegistry` implementing the existing `ToolRegistry` port; each MCP server's tools become dispatchable tool descriptors | I5 single choke point; I3 (MCP is already wire-serialized JSON-RPC — the impedance match with wire-serializable ports is exact) | ADR: MCP tool *outputs* are untrusted content (TaintGate); MCP tool *invocation* requires per-tool capability grants; tool schema changes at runtime vs I6 frozen-resolution → resolve as "MCP catalog snapshotted at composition; refresh = recomposition" |
| **Sensors / environment watchers** | Adapters emitting typed events onto the existing bus | spec §8 append-only stream | Guard: events never drive node scheduling (ADR-0013). A sensor that must trigger work does so by *enqueueing a task* through the engine API, not by scheduling nodes — preserves the observation/execution separation |
| **Short-term working memory** | Already correctly placed: `agency/context/` (assembler, compactor) — explicitly *not* a port per ADR-0005 | spec §3 | The compaction design itself (currently absent — audit D7) |
| **Multi-agent orchestration** | Sub-agent = a workflow *subgraph* whose nodes call `ModelProvider` with a role-scoped context and a role-scoped capability policy. `Orchestrator` correctly stays a non-port (ADR-0005): orchestration is domain logic over the graph, not an I/O boundary | ADR-0013 fan-out (M3) is the primitive; Best-of-N is already the degenerate case of multi-agent | ADR: per-sub-agent capability scoping (an "Editor" sub-agent's grants ⊂ parent grants — capability attenuation, never amplification); budget sub-division through the existing reserve/commit/release governor |
| **Skill libraries** | Data in the ADR-0006 mutable surface (already listed: "skills") | ADR-0006 | Storage/versioning convention only |
| **Self-redesign of workflows** | **The gap.** Requires workflow-as-data (§2) | — | **ADR-0014** |
| **Self-modification of code** | Meta-loop-authored PRs, human-merged (Deliverable 2, M6) | ADR-0006 commit policy | Provenance labeling of agent commits |

Two conclusions from the table. First, the foundation is genuinely evolution-ready: seven of nine capabilities need zero architectural change. Second, the two that need decisions (MCP trust model, workflow-as-data) should be decided *now as ADRs* but *built later* — deciding costs a page; building prematurely costs velocity. That is exactly the pattern ADR-0007 already established (build the seam, ship it off), applied at the roadmap scale.

---

## 2. The load-bearing amendment: ADR-0014 — Workflow topology is data

### 2.1 The problem, precisely

The stated goal is harness engineering and loop engineering as routine activities: try loop variants, measure, keep winners — eventually letting AETHER do this to itself. Under ADR-0013 as ratified, a topology variant is a code change: written in Python, reviewed, merged, redeployed. Consequences:

- **Now**: experiment cadence is throttled to PR cadence. The M2 memoization machinery exists to make ablations cheap to *run*; topology-as-code keeps them expensive to *define*.
- **Later**: ADR-0006's mutable surface (prompts, skills, instructions, retrieval parameters) excludes topology. A meta-loop that wants to try "add a plan node before generate" must open a code PR — correct for safety today, but it means the self-redesign goal has no mechanical path that doesn't route through arbitrary code modification, which is the *most* dangerous grant to hand out first. The safe intermediate rung is missing.

### 2.2 The decision

Workflow topologies are **declarative, versioned data artifacts** (`workflows/*.yaml` or typed-Python-as-config, hash-pinned) validated against a schema and executed by the (code, TCB-adjacent) executor. Node *implementations* remain code; node *composition* becomes data.

Constraints the schema must enforce statically (executor refuses on violation):

1. Socket type compatibility across every edge (the `WorkflowStep[In, Out]` types already ratified in M0 are exactly the validation substrate — this is why the amendment is cheap now).
2. Every path terminates in an `Evaluator` node; no topology can route around the judge (structural I7 — a graph-level invariant, checkable in milliseconds).
3. Iteration constructs carry static budget bounds (repair loops become first-class and bounded, resolving audit D7 inside the same amendment).
4. Fan-out nodes carry declared N and cache-sequencing hints (ADR-0010's Best-of-N consequence becomes schema-visible).

### 2.3 Governance

- Topology definitions enter the **ADR-0006 mutable surface** as a new row: mutable by the meta-loop, **admitted only through the ADR-0003 (rev.2) statistical gate** — a topology is a mechanism, and no mechanism promotes without an ablation clearing the floor. Human loop-engineers use the identical admission path; the meta-loop is just another proposer.
- The executor, the schema validator, and the schema itself are **TCB** (immutable). The meta-loop can propose any graph the schema admits; it cannot change what the schema admits.
- Rollback is structural: topologies are hash-pinned data, so reverting an admitted topology is a one-line pin change, and the M5 regression tripwire (Deliverable 2 §3) automates it.

### 2.4 Sequencing — zero momentum cost

Nothing about M0–M1a changes: `WorkflowStep[In, Out]` types land as planned; the M1a walking skeleton's four-node linear graph simply *is* the first data-defined topology (one trivial YAML instead of one trivial Python composition — same afternoon). M2 memoization keys on node-input digests exactly as ratified. The schema grows constraints as constructs land (iteration at M1a+/M2 per the repair amendment, fan-out at M3). The ADR-0013 reversal condition survives intact: if the abstraction isn't carrying weight at M2, a four-node YAML is even cheaper to un-abstract than four-node Python.

This is the same shape as I3: nearly free on day one, impossible to retrofit at forty nodes, and it is the single decision that makes the AGI-direction goals *mechanically* rather than aspirationally reachable.

---

## 3. The autonomy ladder

Each rung widens the meta-loop's authority only after the previous rung's gates (Deliverable 2 §3) have demonstrably *rejected a bad change* — authority is earned by the judge proving it can say no, never by the proposer proving it can say yes.

| Rung | Meta-loop may mutate | Admission | Commit | Ratified by |
|:--|:--|:--|:--|:--|
| **R0** (now) | Nothing (offline analysis only) | — | — | ADR-0006 |
| **R1** (M4) | Prompts · skills · instructions · retrieval params | ADR-0003 rev.2 on HOLDOUT | Auto-commit in surface | ADR-0006 (as-is) |
| **R2** (M5) | + workflow topology (data) · + memory content | Same + schema validation + regression tripwire | Auto-commit in surface | **ADR-0014** |
| **R3** (M6) | + non-TCB code, via PR | Same + full CI + human merge | Human merge, always | ADR-0006 commit policy (unchanged — only authorship changes) |
| **Never** | Policy engine · evaluator · gates · benchmark manifests · CI · schema/executor · `.importlinter` | — | — | I8, permanently |

The "Never" row is what makes the rest safe to climb, and it is already ratified. The project's genuine long-term differentiator versus every self-improving competitor teardown in the Phase 0 corpus (including the one whose significance gate turned out to be fabricated — register C6) is precisely that its recursion has an incorruptible fixed point: the judge. Recursive self-improvement measured by an unbreakable instrument is a publishable, diligence-proof claim; recursive self-improvement measured by a mutable one is the failure mode ADR-0006 exists to name.

### Generality beyond coding

The stated end-state includes general tasks — explanation, chat, review, research. Structurally this costs nothing new: a "task" is already an abstract domain object; chat is a topology (`assemble-context → generate → respond`) with no evaluator-gated patch; review is a topology ending in a report artifact. What changes is that **non-benchmarkable topologies cannot pass through the ADR-0003 gate** (no binary paired outcome). The honest resolution, consistent with I9: general-task topologies are admitted by hard functional gates only (schema validity, safety invariants, cost ceilings) and are *ranked* by learned/proxy scorers, never "admitted" as improvements — i.e., the harness may host general capabilities immediately, but performance *claims* remain reserved for instrumented domains. Extending instrumented admission to new domains means building each domain's instrument first, which is the governing rule applied recursively, and correctly.

---

## 4. What to do this week vs. what to merely decide

**Do**: TASK-000 (TCB path migration), B4 reorder, ADR-0003 rev.2 pre-registration, repair-edge amendment to ADR-0013, ADR-0014 written and ratified (one page).
**Decide only** (build later, per growth-tier rule): MCP trust ADR, sub-agent capability-attenuation ADR, memory-provenance rule.
**Refuse for now**: any port, package, or dependency for KG/memory/multi-agent ahead of its adapter — ADR-0005 already forbids it, and the predecessor's seventeen-ports corpse is the standing reason why.
