---
status: historical
retrieval: excluded
date: 2026-07-30
title: Sprint 0 Decision Record: The Path from Specification to a Measurable SOTA Harness
---
# **SAGIHA — Sprint 0 Decision Record**

> [!NOTE]
> **Status: advisory.** This document records what Sprint 0 decided and what it owes. It defines no
> contracts and overrides no ADR — a recommendation here becomes real only when it lands in
> [`03-contracts-and-models/`](../../03-contracts-and-models/), an ADR, or a sprint checklist. Its
> companion is the Harness vs. SAGIHA comparative analysis,
> which supplies the evidence; this document supplies the decisions.

> **Purpose.** Sprint 0 is a documentation sprint. Its job is to make the specification honest,
> resolve the contradictions between competing internal reviews, and hand Sprint 3 a checklist that a
> developer can execute without re-litigating architecture. This document is the output.
>
> **SOTA, defined operationally.** Not a prompt wrapper and not a feature count. A harness is SOTA
> when it can (1) **prove** a change helped — A/A noise floor, pristine injected tests,
> `tests_unmodified` as a hard gate; (2) **replay** any run byte-for-byte with zero network I/O;
> (3) **contain** the agent structurally — unforgeable grants verified at one dispatch choke point,
> not a permission prompt; (4) **plan** as a first-class artifact — PRD → stories → task → gate, each
> step replayable and measurable; and (5) **run for six hours** on an ordinary developer machine
> without a `SIGBUS`. SAGIHA specifies all five. It currently does none of them.

---

## 1. 📊 **The Honest Scorecard**

The blueprint that prompted this document scored ten dimensions 80–98 and set every target to 100.
Those numbers describe the **specification**, and reporting them as a single figure is the exact
over-claiming both internal reviews warn against — §4 of the comparative
analysis states the baseline flatly: *SAGIHA is unbuilt.* So the
scorecard is kept, because the dimensions are the right ten, and split into two columns, because the
gap between them **is** the Sprint 0 finding.

*Spec* = how completely the dimension is designed. *Impl* = how much of it runs today, per
[STATUS.md](../../STATUS.md). Both are coarse judgments, not measurements; the only number in this
project that will ever be a measurement comes out of E0.

| # | Dimension | Spec | Impl | What closes the gap | Owed to |
| :-- | :--- | :--: | :--: | :--- | :--- |
| 1 | Architecture & decoupling | 95 | 40 | Give `agency/` and `runtime/` real code, then flip `.importlinter`'s `unmatched_ignore_imports_alerting` to `error` — the CAR contract is inert while its subject is empty (U1); generate the port-tier table from `STABILITY` | Sprint 3 B2/B4 |
| 2 | Capability security | 92 | **15** | A9 (verify the grant, not its id) + A10 (schema-declared path scoping). Until these land, the security claim is false in code | Sprint 3 C, Block 3 |
| 3 | Evaluation & benchmark moat | 98 | **0** | E0-lite: commit-replay harvester, task runner, A/A noise floor, `tests_unmodified` gate | Block 2 / Sprint 4 |
| 4 | Replayability & determinism | 90 | 25 | `ModelRequest` v2 (D10) then canonical digest matching (D2). Order matters — cassettes embed the shape | Sprint 3 A2/A3 |
| 5 | Code quality & maintainability | 95 | 70 | Highest today. `pyright` strict, `import-linter`, ~500 LOC/file already enforced; coverage gate missing | Sprint 3 D1 |
| 6 | Prompt economics & caching | 90 | **0** | Prompt assembly does not exist (G7/D18 — every step is memoryless). Prefix layout is specified and unexercised | Sprint 3 B2 |
| 7 | Code intelligence | 90 | 0 | Tree-sitter graph + LSP diagnostics delta folded into `EditResult` (A1) | Block 4 |
| 8 | **Macro-workflow flexibility** | **60** | **0** | The genuine gap. `WorkflowStep`/`PipelineRunner`, `PRDSpec` → `StoryBoard` → `TaskSpec` — [ADR-0018](../../08-decisions/0018-native-workflow-dag.md) | Block 4 / Sprint 5 |
| 9 | Resilience & production hardening | **55** | 10 | A2 (journal-mode probe), A3 (loop-stuck signatures), A4 (iteration budget), A5 (indexer ceilings), B6 (crash/sleep/resume) | Sprint 3 + Block 5 |
| 10 | Extensibility & wire protocols | 88 | 30 | A12 (`WorktreeManager.allocate() -> WorkspaceRef`) plus `test_port_shape.py`, which is specified and unwritten | Sprint 3 |

**Three corrections to the blueprint's own numbers**, each of which changes a priority:

* **Security is not 92.** The design is. The code mints a grant, stores it, and never verifies it —
  `kernel/dispatch.py` checks only `decision.grant_id is None` and never calls
  `get_grant()`, so the expiry logic in `kernel/policy/engine.py:24-32` is dead. Path scoping
  iterates the literal key list `("path", "file_path", "target_file", "dir")` at `engine.py:45`,
  which cannot reach `EditRequest.path` **even in principle** — the primary mutation tool gets an
  empty scope. A capability system that does not check its own capability is worse than OpenCode's
  blocking modal, because it reads as secure.
* **Workflow flexibility is not 82.** Nothing exists: no `WorkflowStep`, no `PRDSpec`, no
  `StoryBoard`, and no doc in `04-workflows-and-loops/` above the inner loop. 60 is generous for a
  dimension whose specification is one paragraph in an advisory review.
* **Resilience is not 80.** §2.12 of the comparative analysis
  found this dimension has no SAGIHA column at all — nothing on network filesystems, crashes,
  sleep/wake, or mid-turn interjection.

**The pattern is the finding.** The three lowest *implementation* columns — security, evaluation,
prompt economics — are the three dimensions the vision documents lean on hardest. Sprint 0's real
output is not a higher score; it is that the gap is now written down where a sprint plan can consume
it.

---

## 2. 🎯 **Intentional Minimalism: What SAGIHA Refuses, and Why**

SOTA comes from depth in a few dimensions that compound, not breadth across many. Six rejections,
each with a cost that would have been paid in a property SAGIHA is unwilling to lose.

### A. Universal model abstraction wrappers (LiteLLM) — ❌ **Reject**
Breaks prompt-cache prefix locking, the largest cost lever in the system, and puts model calls
outside the cassette so replay stops being total. Found in OpenHands and Hermes; chosen for vendor
breadth. **Instead:** native SDKs plus one OpenAI-compatible `base_url` adapter covering Ollama,
vLLM, and OpenRouter. → [ADR-0008](../../08-decisions/0008-native-sdks-no-litellm.md)

### B. Monte-Carlo tree search over code hypotheses — ❌ **Reject**
Needs a value model before the agent can run at all — a cold-start it cannot bootstrap out of. One
node expansion costs a full agent run plus a test suite; tree search at that cost profile is
irrational. **Instead:** best-of-N at depth one — three parallel worktrees, test all three, rank,
repair sequentially. → [ADR-0005](../../08-decisions/0005-best-of-n-not-mcts.md)

### C. External graph and vector daemons (Neo4j / Qdrant / Milvus) — ❌ **Reject**
Adds a sidecar to operate, token cost for LLM entity extraction, network latency, and unverified
edges. **It also breaks determinism**: two runs with different extraction produce different code
graphs. **Instead:** Tree-sitter AST for deterministic symbol graphs, SQLite FTS5 for lexical search.
→ [ADR-0014](../../08-decisions/0014-defer-dense-retrieval.md),
[ADR-0011](../../08-decisions/0011-split-code-and-episodic-graphs.md)

### D. Monolithic query engines and God classes — ❌ **Reject**
Hermes's 816KB `cli.py` and Claude Code's ~1,700-line `QueryEngine` are the evidence. **Instead:**
CAR three-layer architecture with hexagonal ports, ~300–500 LOC per file, enforced by `import-linter`
rather than by review discipline. This is the one dimension where SAGIHA's implementation currently
leads — Python gets no encapsulation from its compiler, which is why the layer contracts are
load-bearing and not decorative.

### E. Unbounded tool outputs — ❌ **Reject**
Raw shell dumps blow the context window, spike cost, and destroy long-horizon planning. **Instead:**
paginated reads (`read_file_max_lines=2000`), structured truncation carrying `truncated: true`, large
payloads offloaded to a handle. The model always sees structure; it never sees a 40,000-line dump.

### F. Third-party orchestration frameworks (LangGraph / LangChain / Temporal) — ❌ **Reject**
A framework that calls our steps rather than being called by them relocates the dispatch choke point
outside `kernel/` — outside the TCB. LangChain assembles its own message lists, forfeiting the prefix
rule; wrapped provider clients put calls outside the cassette. **Instead:** a native
`WorkflowStep[In, Out]` Protocol in `agency/`. → [ADR-0018](../../08-decisions/0018-native-workflow-dag.md)

### G. Premature peripheral machinery (MCP, OTel, AOI, RHI, sidecars) — ⏸️ **Defer**
The failure mode Sprint 2 already demonstrated: kernel plumbing was built while E0 was named the
moat, and the loop still cannot dispatch a tool. **Close the inner loop first (Sprint 3), then
measure (Block 2), then add periphery as measurement justifies it.**
→ [ADR-0010](../../08-decisions/0010-defer-exotic-components.md)

### 📊 Summary matrix

| Concern | Competitor approach | SAGIHA approach | What this buys |
| :--- | :--- | :--- | :--- |
| Model providers | Universal wrapper (LiteLLM) | Native SDKs + one `base_url` adapter | Locked cache prefix; total replay |
| Code indexing | Vector / graph daemons | Tree-sitter AST + FTS5 | No sidecar; deterministic graph; no token cost |
| Parallel search | MCTS / graph search | Git worktrees + gate verification | No value model, no cold start |
| File size | Monolithic (816KB) | Ports, ~500 LOC/file, CI-enforced | Testable at day one; no merge hell |
| Tool outputs | Raw dumps | Paginated + handle-offloaded | Bounded context, bounded spend |
| Macro workflow | Framework DAG, or none at all | Native `WorkflowStep` in `agency/` | Kernel keeps its loop, prefix, and cassette |

**One honest caveat on this section.** Every row is a rejection made from first principles by a
project that has not shipped. The reference projects' weaknesses were discovered by real users on
real deadlines; these rejections were reasoned in a document. They are defensible, but they are not
yet earned, and each carries a reversal condition in its ADR for exactly that reason.

---

## 3. 🧩 **The Genuine Gap: Macro-Workflow Orchestration**

Of the ten dimensions in §1, nine are covered by existing Tier A/B/C recommendations. **Dimension 8
is the one thing the blueprint contributes that no prior review identified**, and it is worth stating
plainly why it was invisible: none of the four reference harnesses have it either, so a comparative
analysis could not surface it as a gap.

**The gap.** `docs/04-workflows-and-loops/` describes only the inner loop — `TaskSpec` in,
`GateReport` out. A senior developer handed a paragraph of intent writes a spec, decomposes it into
stories, orders them, picks one, implements, verifies, records, repeats. SAGIHA specifies step four
and assumes a human does the other seven.

**The shape** ("dbt for agent logic" — declarative stages, typed edges, each independently testable):

```
[ Prompt ] ─► [ PRDGeneratorStep ] ─► [ StoryDecomposerStep ] ─► [ StoryBoard ]
                                                                      │
                                                                      ▼
[ Commit ] ◄─ [ VerifierStep ] ◄─ [ DMARTIC inner loop ] ◄─ [ Pick Story ]
                    │                                             ▲
                    └────────── returns to the board ─────────────┘
```

Four properties make this a SAGIHA layer rather than a prompt chain:

1. **Stages are classes, order is config.** `WorkflowStep[In: BaseModel, Out: BaseModel]` with
   `async execute(ctx, input_data) -> Out`. Composition order is declared in `config.toml` and
   resolved once at the composition root, so a stage can be swapped, reordered, or A/B-tested without
   touching kernel code.
2. **Every step boundary is an event, and every output is persisted.** A pipeline is therefore
   resumable at step granularity, replayable from a cassette, and measurable in E0 — the same three
   properties the inner loop has. A step that cannot be replayed is a defect, not a category.
3. **`TaskSpec` stays the inner loop's only input.** The macro layer *produces* `TaskSpec` values.
   `StorySpec` carries the `parent_task_id` and disjoint file-set closure that
   [Task & Acceptance](../../03-contracts-and-models/task-and-acceptance.md) already specifies for
   decomposition. A `chat` profile binds no pipeline; `sagiha run <goal>` skips to `CodingStep`.
4. **It is an RHI target.** Because the decomposition strategy is data, the outer loop can propose a
   different one and E0 can measure whether it helped. This is the first mechanism in the design that
   makes *planning quality* a measurable quantity rather than a matter of taste.

**And the discipline that keeps it honest.** A planning pipeline multiplies cost per task and adds a
failure mode above the loop — a bad `StoryBoard` wastes every downstream step. Per §8.5 of the
comparative analysis, no stage enters the tree without an E0 gate showing it beats running the inner
loop directly on the raw prompt. **If planning does not beat no-planning on the benchmark, the layer
does not ship.**

**Sequencing is not negotiable.** This is a **non-goal until Sprint 3's exit test is green.** Writing
a planner above a loop that cannot dispatch a tool (D1) is precisely the sequencing error the
2026-07-29 review diagnosed. Contract and rationale:
[ADR-0018](../../08-decisions/0018-native-workflow-dag.md).

### Obsidian-style knowledge net (the memory half)

Long-term episodic memory is a linked net, not a table
([neural-symbolic-memory.md](../../02-architecture/neural-symbolic-memory.md)): `MemoryRecord` carries
`links: tuple[str, ...]` joining decisions, episodes, and rules, supporting neighborhood queries
(*"what connects to this module?"*) and backlinks (*"what beliefs depend on this decision?"*).
**Code facts stay strictly AST-derived** via Tree-sitter; only *learned* facts live in the net —
that separation is [ADR-0011](../../08-decisions/0011-split-code-and-episodic-graphs.md) and it is
what keeps the code graph deterministic. `neighbors()` and `backlinks()` are not yet on the `Memory`
port; honest invalidation is impossible without backlinks, which is why that is Tier B item B5 and
not a nicety.

---

## 4. 🔍 **Reconciliation: Which Audit Findings Survived Verification**

An earlier draft of this document proposed five overengineering findings and a universality matrix.
§7 of the comparative analysis checked each against
`src/sagiha/` and the normative docs. **Three were confirmed, one was rejected, one was not a
finding, and one was right about the design but wrong about the status.** Recording the rejections
matters as much as the confirmations — per
[reviews/README.md](./README.md), a rejected finding is recorded, never deleted.

| Claim | Verdict | Disposition |
| :--- | :--- | :--- |
| 21 ports and 74 docs before a working tool loop | **Substantially correct** (22 Protocols; 82 `.md`) — but the examples were wrong: `AOICoprocessor` and `RHI` are **not ports**, and the five mandatory ports are `model_provider`, `policy_engine`, `resource_governor`, `tool_registry`, `trajectory_store` — **`ToolRegistry`, not `Workspace`** | Freeze the compatibility *promise*, not the declaration. See §5 Q1 |
| Three redundant memory concepts; steps run memoryless | **Confirmed.** `ShortTermMemoryAdapter` is wired zero times; `composition.py:63` binds only `InMemoryMemory` | Sprint 3 A12 + B2. But `TrajectoryStore` is **not** a redundant third concept — it is wired at `composition.py:78` and serves append-only audit |
| Security is ceremony without enforcement | **Confirmed, and worse than stated** — the flat key scan cannot reach `EditRequest.path` even in principle | **A9 + A10 — the highest-priority items in the entire review set** |
| Evaluator too rigid for unstructured tasks | **Not a finding.** [Task & Acceptance](../../03-contracts-and-models/task-and-acceptance.md) already states ungated runs are excluded from benchmarks and outer-loop evidence by construction | No change. The proposed fix *is* the existing text |
| 32 event subclasses cause maintenance overhead | **Count exact; concern already solved; remedy rejected** | `gen_event_catalog.py --check` runs in `ci.yml:43`, so drift already fails the build. **Collapsing to four events is refused** — the `ToolCallRequested`/`ToolCallAuthorized` split is what lets an audit separate *attempted* from *permitted* |
| Universal across MCP / gRPC / JSON / OpenAI API | **Right about the design, wrong about the status** | A2A is deferred, not native; gRPC is a trigger, not a shim we have; `WorktreeManager.allocate() -> Workspace` (`ports/workspace.py:40`) actively violates the rule. See §6 |

**The event-collapse rejection deserves its own line**, because it is the one place the original
blueprint would have made the architecture worse. Typed events are *cheaper* to read, not more
expensive — a discriminated union narrows in one step where a generic envelope forces every consumer
to branch on a string and re-validate a payload. And profiles require that *absence of a verdict* and
*a verdict of pass* never be the same value, which a generic event carrying an optional `gate_report`
reintroduces immediately. **The durable fix for doc/code drift is generation, not amputation.**

---

## 5. ❓ **Tech-Lead Questions, Answered**

### Q1. Freeze unused ports and prune `src/sagiha/` to four folders (`domain`, `ports`, `kernel`, `adapters`)?

**Freezing: yes. Pruning to four folders: no — and pruning `agency/` or `runtime/` would break a
binding decision.**

Split the question into three, because it conflates them:

**(a) Freeze port expansion until an adapter exists — approved.** Correct and already policy-shaped.

**(b) Collapse to five ports — rejected.** A port is ~25 lines of `Protocol` and is precisely the
mechanism that makes every deferral in the [phased migration
matrix](../../07-roadmap/phased-migration-matrix.md) safe. Deleting `EmbeddingProvider` does not
simplify the system; it converts a *deferred component* into a *future refactor*. The
Stable/Provisional/Experimental scheme in [Port Stability &
Versioning](../../03-contracts-and-models/port-stability-and-versioning.md) is already normative and
already declared in every port module. What it lacks is teeth: a **generated** tier table (the trick
`gen_event_catalog.py` already uses), a per-tier CI assertion, and an explicit statement that
*stability* and *mandatory binding* are **separate axes** — `Workspace` is a Stable contract that a
`chat` profile leaves unbound, and both facts are true at once. **Freeze the promise, not the
declaration.**

**(c) Prune the empty folders — rejected for two of the four.** Verified: `agency/`, `aoi/`,
`runtime/`, and `outer_loop/` contain only a docstring `__init__.py`. But `agency/` and `runtime/`
are the **A** and **R** of CAR. Deleting them would contradict
[ADR-0007](../../08-decisions/0007-trusted-computing-base.md), void the `import-linter` layer
contracts that are SAGIHA's single strongest implemented property, and remove the home
[ADR-0018](../../08-decisions/0018-native-workflow-dag.md) assigns to `WorkflowStep`.

The emptiness is a real finding with a different fix, and `.importlinter` already documents it against
its own `car-layering` contract: *"`agency/` is an empty stub until S3 — the ignore above legitimately
matches nothing yet. warn, not error … revisit once `agency/` has code,"* with
`unmatched_ignore_imports_alerting = warn` keeping CI green. That is an honest temporary concession,
correctly annotated. It also means the strongest claim in the whole architecture argument — mechanical
boundary enforcement in a language that gets none from its compiler — currently rests on a contract
whose subject is an empty package. Sprint 3 already writes the code that fixes it: **prompt assembly
(B2) belongs in `agency/`**, **tool execution over the dev-mode subprocess `Workspace` (B4) belongs in
`runtime/`**.

> **Decision.** Keep `agency/` and `runtime/`. Sprint 3 B2 and B4 must land their code there, and
> `unmatched_ignore_imports_alerting` flips back to **`error`** in the same PR — that is what makes
> the concession self-closing instead of permanent. Delete `aoi/` and `outer_loop/`: both are deferred
> behind [ADR-0010](../../08-decisions/0010-defer-exotic-components.md) triggers, neither has a Sprint
> 3 role, and the deferral seam is the **port**, not the package —
> `ports/advisory.py` already holds the three advisory Protocols that an empty `aoi/` only gestures
> at. Finally, add the one contract that makes the TCB real in code rather than prose: **nothing
> outside `kernel/` may import `kernel.policy` or construct a `Grant`.**

### Q2. Adopt a native `WorkflowStep` DAG instead of LangGraph?

**Approved, and recorded as [ADR-0018](../../08-decisions/0018-native-workflow-dag.md)** — so it is
binding rather than advisory.

The reasons are structural, not aesthetic: LangGraph owns the loop (relocating the dispatch choke
point outside the TCB), LangChain assembles its own message lists (forfeiting the byte-identical
prefix rule), wrapped provider clients bypass the cassette (ending total replay), and
Prefect/Temporal duplicate a durability model `TrajectoryStore` already provides. Python 3.13 supplies
everything needed: PEP 695 generics, `typing.Protocol`, Pydantic, `anyio`.

**Binding now:** the framework rejection, the ownership rules (steps live in `agency/`, hold no tool
references, mint no grants, call no provider outside `ModelProvider`), and the replayability
requirement. **Provisional:** the exact Protocol signatures, until two steps have adapters and a gate.
**Sequenced:** not before Sprint 3's exit test is green.

### Q3. Are Sprint 3's exit criteria approved to unblock implementation?

**They are the right criteria, and this document recommends approval with two amendments.** The exit
test — *the agent, driven by a committed cassette, fixes a failing test in a fixture repo through the
dispatch choke point, the run is gate-evaluated, and `sagiha replay --verify` passes* — is a genuine
end-to-end proof, and the D10-before-D2 ordering (`ModelRequest` v2 must land before any cassette
fixture is committed, because cassettes embed the shape) is correctly identified.

Two amendments, both cheap and both closing a hole the current checklist leaves:

* **Add A9 and A10 to Section C.** Sprint 3 C4 currently tests an expired grant only *at
  `record_outcome` correlation* and defers full path-scope enforcement to Block 3. That leaves
  `dispatch` still not calling `get_grant()` at the point of effect for the whole sprint. A9 is a
  handful of lines at a choke point that Sprint 3 is already rewriting; deferring it means touching
  the most security-sensitive code in the system twice. A10 (schema-declared path scoping at
  registration) can stay in Block 3 — but the *declaration site* should be added when the five
  built-in tools are registered in B4, or it becomes a retrofit across every tool.
* **Add A2 (SQLite journal-mode probe) to Section A.** Sprint 3 makes SQLite the trajectory store on
  every developer machine. On an NFS- or CIFS-mounted home directory, WAL's mmap'd `-shm` file cannot
  be backed coherently and the failure is a **`SIGBUS` panic, not an error message**. This is ~100
  lines in one adapter and it will otherwise be discovered by whoever on the team has a network home
  directory.

Everything else in Tier A can wait for the sprint after. Neither amendment changes the exit test.

---

## 6. 🌐 **Universality — Corrected Status**

The architectural reasoning is sound and worth restating: because
[remoteable-ports.md](../../02-architecture/remoteable-ports.md) requires every port method to be
`async` and every payload to be Pydantic-serializable, transport becomes a shim rather than a
refactor. `AsyncIterator[T]` is permitted where `T` is serializable, which is what makes streaming
remoteable. **The status claims, however, were overstated in three places, and the table below is the
corrected version.**

| Protocol | Corrected status | Notes |
| :--- | :--- | :--- |
| **OpenAI-compatible API** | **Native by design, Sprint 3 by schedule** | One `base_url` adapter covers Ollama, vLLM, OpenRouter. The adapter does not exist yet (G8) |
| **MCP client** (consume tools) | **S0, stdio** | Tools register via JSON Schema, `trusted_output=False` |
| **MCP server** (expose SAGIHA) | **S1 / Block 5** | JSON-RPC over the event stream. Deferred, not native |
| **HTTP + SSE** | **S1** | Event serialization, `?since=<step_id>`, redaction in the streamer |
| **gRPC / protobuf** | **Trigger, not a capability** | The docs themselves note gRPC "brings protobuf schema management and a threading model that fights asyncio." Start with msgpack or JSON-RPC over a Unix socket |
| **A2A** | **Deferred** — was claimed "native" | [ADR-0010](../../08-decisions/0010-defer-exotic-components.md): A2A waits for a genuinely remote peer. The entry point satisfies its *shape*; nothing implements it |
| **"100% async, pure Pydantic"** | **Aspiration with a live violation** | `WorktreeManager.allocate() -> Workspace` (`ports/workspace.py:40`) returns a Protocol instance — the one shape that cannot cross a wire, on precisely the port a container or remote runtime would replace. Fix is A12: `-> WorkspaceRef`, resolved through the registry. `test_port_shape.py` is specified and unwritten |

**Honest verdict.** SAGIHA is *designed* for universality with a credible mechanism. It has not
*demonstrated* it, one port contradicts it, and A2A is a shape rather than a capability. Two rules
keep the design from decaying as surfaces are added: **frames, not objects** (any port returning a
live object is not remoteable regardless of how async it is), and **one inbound signature** — no
`execute_chat()`, no REST-only entry point. A channel needing a second signature is evidence the
boundary is wrong.

---

## 7. 🚀 **Action Plan**

Ordered by dependency. Each phase has a single completion test, because a phase without one is a
wish.

### Phase 1 — Close the inner loop (Sprint 3, immediate)
Kernel defect fixes D1–D18, plus the two amendments in §5 Q3 (A9, A2). Land prompt assembly in
`agency/` and tool execution in `runtime/` so the CAR contract stops being vacuous.
**Done when:** the Sprint 3 exit test is green in CI — one failing test fixed, gated, logged, and
`replay --verify` passing at L1 fidelity.

### Phase 2 — Measure before optimizing (Block 2 / Sprint 4)
E0-lite: commit-replay harvester, task runner, **A/A noise floor measured before any ratcheting**,
`tests_unmodified` as a hard gate, cost-per-success recorded.
**Done when:** 10–30 harvested tasks run unattended and the A/A noise floor is a number in a report.
Until it is, no claim that any change "helped" is admissible.

### Phase 3 — Production hardening and Tier A ergonomics
Remaining Tier A: A1 (post-edit diagnostics delta in `EditResult`), A3–A5 (loop-stuck signatures,
iteration budget, indexer ceilings), A6 (first-N/last-N compaction), A7 (canonical block tags), A8
(generated config JSON Schema), A12 (`WorkspaceRef`). Plus generated port-tier table and per-tier CI
assertions.
**Done when:** every generated artifact is `--check`ed in CI, so doc/code drift is a build failure.

### Phase 4 — Macro workflow, gated (Block 4 / Sprint 5)
`WorkflowStep`/`PipelineRunner` per [ADR-0018](../../08-decisions/0018-native-workflow-dag.md);
`PRDSpec` and `StoryBoard` added to
[Task & Acceptance](../../03-contracts-and-models/task-and-acceptance.md); the four-stage set.
**Done when:** E0 shows PRD-and-story decomposition beats direct execution on the benchmark suite.
**If it does not, the layer does not ship.**

### Cross-cutting rule (adopt now)
> **A new port, event type, or subsystem enters the tree only with (a) a vertical slice that uses it
> and (b) a gate in E0 that measures it.** Absent either, it stays `experimental` with at most one
> consumer, and that consumer is a test.

This is the single rule that would have prevented the condition Sprint 0 spent its time diagnosing.
It is Tier C item C5 and it deserves an ADR of its own.

---

## 8. 📋 **Owed Work — Docs**

Concrete, small, and each with a named target file.

| # | Change | Target | Why |
| :-- | :--- | :--- | :--- |
| 1 | Add the workflow orchestration spec — `WorkflowStep`, `PipelineRunner`, stage set, event boundaries | **new** `docs/04-workflows-and-loops/workflow-orchestration-and-dags.md` | [ADR-0018](../../08-decisions/0018-native-workflow-dag.md) records the *decision*; the contract needs a normative home |
| 2 | Add `PRDSpec` / `StoryBoard` / `StorySpec` lifecycle schemas | [task-and-acceptance.md](../../03-contracts-and-models/task-and-acceptance.md) | The macro layer's payloads are domain models and must live with `TaskSpec`. Note Sprint 3 D3 simultaneously **removes** duplicated code fences from this file — add references to `src/`, not fences |
| 3 | Add a resilience section: journal-mode probe, crash/sleep-wake, interjection queue | [composition-and-configuration.md](../../05-tech-stack/composition-and-configuration.md) + [error-taxonomy.md](../../03-contracts-and-models/error-taxonomy.md) | §1 dimension 9 is the weakest *specified* dimension, not merely the weakest built one |
| 4 | Generate the port stability table from `STABILITY` declarations and `--check` in CI | `scripts/`, [port-stability-and-versioning.md](../../03-contracts-and-models/port-stability-and-versioning.md) | The doc names five Stable ports; the code marks eight. Same drift class the event catalog already solved |
| 5 | Document the `todo/` → `doing/` → `done/` convention and log the three `todo/` reviews | [reviews/README.md](./README.md) | The convention exists on disk and nowhere in prose; the log table omits these documents entirely |
| 6 | Fix the foundation-review link path repo-wide (`reviews/` → `reviews/doing/`) | [README.md](../../README.md), [STATUS.md](../../STATUS.md), sprint-2.md, sprint-3.md | The file moved into `doing/`; every inbound link still points at the old path |
| 7 | Add `docs/sprints/` to the README sitemap | [README.md](../../README.md) | Sprints are referenced in "Start Here" but absent from the sitemap table |

---

## 9. 🔗 **Cross-References**

* Harness vs. SAGIHA — Comparative Analysis — the evidence base; Tier A/B/C items and §7 verdicts
* [2026-07-29 Foundation Review](../done/2026-07-29-foundation-review.md) — D1–D18, G1–G10, U1–U5
* [STATUS.md](../../STATUS.md) — implementation truth · Sprint 3 — the near-term contract
* [ADR-0018](../../08-decisions/0018-native-workflow-dag.md) — native workflow DAG · [ADR Log](../../08-decisions/README.md)
* [CAR Model](../../02-architecture/car-model.md) · [Remoteable Ports](../../02-architecture/remoteable-ports.md) · [Neural-Symbolic Memory](../../02-architecture/neural-symbolic-memory.md)
* [Phased Migration Matrix](../../07-roadmap/phased-migration-matrix.md)
