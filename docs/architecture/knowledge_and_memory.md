---
status: rationale
updated: 2026-08-07
---

# Knowledge and Memory — Retrieval, Index, Graph, and the Two Memories

**Design of record for M5.** How the system knows things: what it retrieves, what it remembers
within a task, what it remembers across tasks, and — the part most systems get wrong — **which
of those may influence a measured result.**

Everything here is a `ContextSource` or a bus consumer. **No new port, no new node kind, no new
layer.** That is the test of whether the capability layer
([`capability_layer.md`](capability_layer.md)) was designed correctly, and it passes.

---

## 1. The shape

```
  ┌─ WORKING SET (one task) ──────────────────────────────────────────────┐
  │  L1 system · L2 tools · L3 repo brief · L4 task · L5 dialogue         │
  │  assembled by LayeredAssembler · compacted at L5 only                 │
  └───────────────────────────▲───────────────────────────────────────────┘
                              │ ContextBlocks (each carries layer + Provenance)
  ┌───────────────────────────┴───────────────────────────────────────────┐
  │  CONTEXT SOURCES — the only way anything enters a prompt              │
  │  EntryFile · Symbol · Lexical · Graph · Vector · GateOutput · Lesson   │
  └───────────────────────────▲───────────────────────────────────────────┘
                              │
  ┌───────────────────────────┴───────────────────────────────────────────┐
  │  KNOWLEDGE SUBSTRATE                                                  │
  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
  │  │ Symbol index │ │ Lexical index│ │ Code graph   │ │ Vector index │  │
  │  │ tree-sitter  │ │ grep / FTS   │ │ imports·refs │ │ embeddings   │  │
  │  │ ✅ BUILT     │ │ ⬜           │ │ ⬜           │ │ ⬜ growth    │  │
  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
  │  ┌──────────────────────────────────────────────────────────────────┐ │
  │  │ LESSON STORE — cross-task memory. SPLIT-SCOPED, OFF BY DEFAULT   │ │
  │  └──────────────────────────────────────────────────────────────────┘ │
  └───────────────────────────────────────────────────────────────────────┘
```

**`TreeSitterIndexer` is already built, passes conformance, and is reachable from no node and no
topology.** It is a working capability delivering zero value because there was no seam. That
seam is `ContextSource` (`TASK-054`), and it is the first thing this document cashes in.

---

## 2. Short-term memory — the working set

Scope: **one task**. Dies when the run ends. This is `ContextBlock`s assembled into L1–L5
(ADR-0010) and compacted at L5 only.

| Mechanism | Status | Where |
| :--- | :--- | :--- |
| Tail-biased truncation of gate output | ✅ built | `measurement/evaluator.py::tail_biased` |
| Failing-assertion isolation | ✅ built | `repair.py:78-88` |
| Five-layer assembly, ≤4 cache breakpoints | ⬜ `TASK-056` | `agency/context/assembler.py` |
| Structural compaction (L5 only) | ⬜ `TASK-024` | `agency/context/compactor.py` |

**Two properties worth stating because they are easy to lose.**

`tail_biased` lives in `measurement/` rather than in a node so that *the truncation the prompt
sees is the truncation the gate recorded.* A second truncation strategy that disagreed with the
gate would make the repair edge argue with a failure that was never reported.

Compaction touches **L5 only**, and the assembler exposes no API to touch L1–L4 — a type-level
guarantee, not a rule someone must remember. Model-summarised compaction is a separate mechanism
that does not promote without its own ablation.

**Borrowed, with attribution.** Kimi runs `should_auto_compact` *inside* the step loop
(`soul/kimisoul.py:1017`) and checkpoints context every step, enabling rewind. Both are worth
adopting: compaction that only runs between turns fails exactly when a single turn overflows.

---

## 3. Retrieval — the four indices

All four are `ContextSource` implementations over the substrate. A role opts in by naming them;
none is mandatory.

| Source | Answers | Backed by | Cost | Status |
| :--- | :--- | :--- | :--- | :--- |
| `EntryFileSource` | "the files the topology named" | Workspace | free | ✅ built (in `retrieve.py`, to be extracted) |
| `LexicalSource` | "where does this identifier appear" | grep / FTS5 | free | ⬜ `TASK-064` |
| `SymbolSource` | "where is this defined, what's in this file" | `TreeSitterIndexer` | free | ⬜ seam only |
| `GraphSource` | "what depends on this, what does it call" | code graph | free | ⬜ M5 |
| `VectorSource` | "what is semantically near this question" | embeddings | **paid** | ⬜ growth tier |

### 3.1 Order matters, and it is not the order people reach for

**Deterministic before semantic.** Lexical, symbol and graph retrieval are free, reproducible
and seedable. Vector retrieval costs an embedding call per query and per document, and its
results move when the model moves. On a codebase, an identifier is usually an exact string —
grep beats embeddings on the majority of retrieval questions and costs nothing.

So the pipeline is: **lexical → symbol → graph → (vector only if the first three under-fill the
byte budget).** `VectorSource` is a growth-tier port under ADR-0005 and arrives with an adapter
or not at all.

### 3.2 Three properties every source must have

1. **Deterministic and seeded.** A retrieval set that varies run to run makes
   `measurement.md` §6's reproducibility requirement unsatisfiable. Vector search is seeded and
   its index is hash-pinned into the instrument tuple, or it does not run in a measured arm.
2. **It publishes what it did not retrieve.** `RetrievedContext.missing` already exists for
   this: *"the model was not shown the file" and "the model was shown the file and failed" are
   different diagnoses, and the second is only believable when the first is excluded.*
3. **Its `Provenance` label is a property of the source, declared once** — never decided at the
   call site. That is what stops repository content and test tracebacks from both drifting to
   `AGENT`, which is exactly what happened when ten call sites each decided independently.

### 3.3 Localization is the retrieval problem that matters

`RetrieveStep` reads the files a topology *names*. `Task` carries no file list. On a real
repository there is no mechanism that decides which files to open — the SWE-bench blocker that
survives even after every container image is built (`TASK-064`).

It is also **the largest token win available**, and the only place where best-score and
fewest-tokens point the same direction: exploring a repo by having the model issue `grep`/`ls`
costs a round trip per step and re-enters every result into context, while a deterministic
pre-model localization pass costs **zero inference tokens** and produces a smaller prompt.

`TASK-065` is the honest companion — *did the gold patch's files appear in the retrieved set?* —
because the premise that localization dominates failures is a widely-reported hypothesis this
project has not measured.

---

## 4. The knowledge graph — second-brain, scoped honestly

A code graph over symbols, imports, call edges and file relationships. Nodes are symbols and
files; edges are `imports`, `calls`, `defines`, `tests`, `co-changed-with`.

`GraphSource` answers neighbourhood queries — *"what calls this"*, *"what changed alongside
this"* — and renders a compact Markdown neighbourhood into L3. That is the Obsidian-like
property that is actually useful to an agent: **not a visualisation, a bounded neighbourhood
that fits in a prompt.**

**Two constraints.**

*Derived, never authored.* The graph is rebuilt from the worktree at a pinned commit. It is a
cache, so it never becomes a place where facts live that the code does not contain — otherwise
it drifts and becomes a second source of truth that nobody validates.

*Bounded expansion.* Neighbourhood queries take a hop limit and a byte budget. An unbounded
graph walk is how a context window dies, and "the graph decided" is not a defensible reason for
a 40k-token prompt.

**Evidence it is worth building:** grok ships a complete embedded stack — `xai-grok-memory`
with `chunker`, `index`, `search`, `mmr` (maximal marginal relevance re-ranking),
`query_expansion`, over SQLite FTS5 + `vec0` vector — plus `xai-codebase-graph`. It works, it is
off by default, and it is scoped to cross-session memory rather than arbitrary corpora. **MMR
re-ranking is the specific idea to steal**: it optimises for coverage rather than similarity,
which is what you want when filling a fixed byte budget.

---

## 5. Long-term memory — and the hazard nobody flags

Cross-task memory is the highest-value capability here and **the sharpest measurement hazard in
the entire system.**

`ReflectorStep` extracts a lesson today, writes it into `task.instructions`, and it dies with the
run. A `LessonStore` would make it persist. That is desirable — a harness that learns a
repository's conventions once is strictly better — **and if tasks A and B are in the same
manifest, a lesson learned on A and applied to B is train-on-test.**

It breaks three things at once:

- **The paired design.** McNemar assumes both arms see each task under identical conditions. An
  arm whose behaviour on task 40 depends on tasks 1–39 has an order effect the pairing does not
  model.
- **The split discipline.** DEV/HOLDOUT/SEALED are pinned so a mechanism tuned on DEV cannot leak
  into an admission run. A persistent store crosses that boundary invisibly, because nothing in
  the manifest records it.
- **Reproducibility.** A store mutated by previous runs makes the same config produce different
  results, and the instrument tuple cannot capture it.

### 5.1 The four constraints, which are the minimum

1. **The store's content hash enters the instrument tuple.** `sha256(store)` is part of
   `sha256(RunConfig)`, or the run is not reproducible.
2. **Off by default** — an `AblationFlags` field like every other mechanism.
3. **Scoped and cleared per split, enforced in the engine.** A lesson learned on a DEV task may
   never be visible on a HOLDOUT or SEALED run. Enforcement in code, not convention.
4. **Its ablation reports order sensitivity.** The same manifest in shuffled order must give the
   same resolve rate. **A lift that disappears under shuffling is an order effect, not a lift.**

`Memory` is a growth-tier port in `spec.md` §4, admitted only with an adapter. Post-floor,
ablation-gated, and the shuffled-order replication is not optional.

### 5.2 What long-term memory holds

| Kind | Example | Written by | Read by |
| :--- | :--- | :--- | :--- |
| Convention | "this repo uses `pytest.raises`, never `assertRaises`" | Reflector, after a pass | `LessonSource` at L3 |
| Failure pattern | "edits to `storage.py` need `playlist.py` updated too" | Reflector, after a repair | `LessonSource` at L3 |
| Repo brief | Module map, entry points, test layout | Derived, rebuilt per commit | `GraphSource` at L3 |
| Trajectory | The full event log | `TrajectoryStore` (✅ built) | The outer loop and the meta-loop |

**The trajectory store is already the substrate for H3.** It is append-only, byte-deterministic
on replay, and never dropped under backpressure. The meta-loop's input is not a new database —
it is the log that already exists.

---

## 6. Tools are retrieval too, and they are labelled differently

`list_files`, `read_file`, `grep`, `search_web` reach the model through the same assembler — but
**tool output is labelled `UNTRUSTED_EXTERNAL` at construction** (ADR-0015), never at point of
use, so a caller cannot forget.

Three consequences that fall out of that one rule:

- **Deterministic retrieval beats a tool call when both are possible.** `SymbolSource` and a
  `grep` tool answer the same question; the source costs no round trip and no output tokens.
  Tools are for what the harness cannot precompute.
- **Web search is a declared egress surface.** `ResearchPayload.allowed_sources` names what may
  be reached, and it is hashed into the instrument tuple. Egress is never ambient.
- **Adding untrusted-labelled tools will make the policy engine start failing closed** on
  capability-widening requests — which is the gate working, and why `TASK-030a`'s escalation
  taxonomy is a prerequisite for a browser or MCP tool rather than a nicety.

---

## 7. Build order

| # | Item | Blocked on | Why here |
| :--- | :--- | :--- | :--- |
| 1 | `ContextSource` protocol + `EntryFile`/`GateOutput`/`CurrentFile` | `TASK-053` lattice | Removes the duplication; the seam everything else plugs into |
| 2 | `SymbolSource` | ↑ | Makes an already-built, conformance-passing indexer reachable |
| 3 | `LayeredAssembler` | ↑ | Nothing above L5 is enforceable without it |
| 4 | `LexicalSource` + localization set | ↑ | The SWE-bench precondition and the biggest token win |
| 5 | Retrieval-recall diagnostic | 4 | Decides whether to invest in retrieval or generation |
| 6 | Compaction (L5) | 3 | Long tasks |
| 7 | `GraphSource` | 2 | Neighbourhoods for `explain`/`qa` |
| 8 | `VectorSource` | growth-tier ADR | Only if 1–7 under-fill the budget |
| 9 | `LessonStore` | floor + §5.1's four constraints | Highest value, highest hazard, therefore last |

**The order is deliberate: free deterministic retrieval first, paid semantic retrieval late,
cross-task memory last.** Each step is separately ablatable, and one that does not clear the
floor is deleted rather than kept.

## 8. What this does not claim

- **No lift.** Every source here is a mechanism and promotes only on an ablation clearing the
  floor (`spec.md` §7).
- **No token-saving percentage.** §3.1's ordering is an argument from cost structure, not a
  measurement.
- **No new port.** `Memory`, `CodeGraph` and any vector index are growth-tier in `spec.md` §4 and
  enter under ADR-0005 with a first adapter, or not at all.
- **Nothing here is scheduled before the floor.** A retrieval ablation on a contaminated
  instrument produces a number that has to be discarded.
