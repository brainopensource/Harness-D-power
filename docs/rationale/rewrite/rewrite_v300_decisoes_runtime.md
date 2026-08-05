---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Runtime, Polyglot Strategy and Commercial Packaging

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Answers RFP [§4-A](../reviews/review_project_rewrite_v300.md) and [§5.2](../reviews/review_project_rewrite_v300.md).
Closes open decision **Q2** from the [Phase-0 charter](../reference/PLANNING.md).

---

## 0. Recommendation

**Python 3.13 monoglot control plane. No second language in Phase 1.** Every port stays
wire-serializable so that any measured hot path can move out of process — to a Rust sidecar, a
container, a remote peer — as a new adapter behind an unchanged interface.

This is a recommendation with a stated expiry: §3 lists the **three measurements that would
overturn it**. It is not a preference for Python. It is a claim about where this workload's time
actually goes, and that claim is falsifiable.

---

## 1. The measurement that decides the question

Before comparing languages, establish the budget the language is competing for. Order-of-magnitude
figures for the operations in one agent step:

| Operation | Typical latency | Relative |
| :--- | ---: | ---: |
| PyO3 in-process FFI call (Python → Rust, no copy) | ~100 ns | 1× |
| SQLite FTS5 query, warm cache | ~50 µs | ~500× |
| Unix-domain-socket IPC round trip, small payload | ~20 µs | ~200× |
| gRPC over loopback, protobuf encode + decode | ~200 µs | ~2,000× |
| Tree-sitter parse, one 1,000-line file | ~2 ms | ~20,000× |
| Container command execution (test suite start) | ~200 ms – 5 s | ~10⁶–10⁷× |
| **LLM completion, one step** | **~2 – 60 s** | **~10⁷–10⁸×** |

A coding agent step is one LLM round trip plus some local work. **The LLM call is between four and
seven orders of magnitude more expensive than any in-process language boundary, and three to five
orders more expensive than a gRPC hop.** A polyglot architecture chosen to reduce inter-component
latency is optimizing a term that does not appear in the total.

This is what PLANNING.md risk **R4** names: "premature Rust rewrite — weeks burned on a second
toolchain for a network-bound workload."

### The counter-argument, stated fairly

The workload is network-bound *per step*. It is not network-bound in two places:

- **Cold indexing a large repository.** Parsing 1M LOC is genuinely CPU-bound, embarrassingly
  parallel, and hits Python's GIL.
- **Resident footprint.** A Python process with pydantic, httpx, tree-sitter and the SQLite stack
  loaded sits around 80–150 MB RSS before doing anything. Target **T6** is <300 MB peak and <1%
  idle CPU for a process expected to hibernate for hours. That is achievable but not comfortable.

Both are *local, bounded* problems. Neither requires the control plane to change language — which
is precisely the case for isolating them behind ports rather than rewriting around them.

### What is already native

A frequently-missed point in this comparison: Python's hot paths here are **already C**.
`tree-sitter` is a C library with thin bindings; FTS5 is SQLite, C; JSON parsing in pydantic v2 is
Rust (`pydantic-core`); `httpx`'s TLS is OpenSSL. The Python in the loop is glue and control flow,
not computation. "Rewrite it in Rust" would, for most of the index path, replace a Python call into
C with a Rust call into the same algorithms.

---

## 2. Language comparison, without a thumb on the scale

| Dimension | Python 3.13 | Go | Rust |
| :--- | :--- | :--- | :--- |
| LLM/provider SDK ecosystem | **Strongest** — first-party SDKs, first to support new features (caching, thinking blocks, streaming shapes) | Adequate; community SDKs lag provider features | Weakest; usually hand-rolled HTTP |
| Iteration speed | **Highest** — no build step | Fast build, static types | Slowest; compile times dominate the edit loop |
| Idle RSS | 80–150 MB | **20–50 MB** | **10–30 MB** |
| Concurrency for I/O fan-out | `anyio`/`asyncio`, adequate | **Goroutines, excellent** | `tokio`, excellent |
| CPU parallelism | GIL-limited; needs subprocess/native offload | **Native** | **Native** |
| Startup time (CLI-relevant) | 200–500 ms with a heavy import graph | **<10 ms** | **<10 ms** |
| Single-binary distribution | Requires Nuitka/PyOxidizer | **Native** | **Native** |
| Ecosystem for the *domain* (AST, tokenizers, statistics, ML) | **Strongest** | Weak | Growing |
| Hiring / contributor pool for agent work | **Largest** | Medium | Smallest |

### The argument that is specific to *this* system

AETHER is designed to reach L3 — a meta-loop that optimizes the harness's own prompts, tool schemas
and routing from its trajectory corpus. **A compiled control plane puts a build-and-link step
inside the self-improvement loop.** In Python, an accepted mutation is a new config or a new prompt
file loaded on the next run. In Rust or Go, it is a rebuild, and the RHI iteration cost rises by
orders of magnitude for exactly the component whose value depends on iterating cheaply.

This argument does not apply to a sidecar. A Rust *indexer* is rebuilt on a human's schedule, not
the agent's. It applies to the plane the meta-loop is allowed to mutate — which, by invariant I8,
is precisely the plane that is **not** the TCB.

### Why not the three-plane polyglot design

`../reference/go_rust_greenfield_harness.md` proposes a Rust microkernel + Go/TS control plane +
Python intelligence sidecar. It is a coherent design and it is wrong for Phase 1 on three counts:

1. **It splits the TCB across a wire.** The dispatch choke point plus grant verification is the
   security argument. Running it in Rust while agency runs in Go means the authorization decision
   and the effect happen in different processes, and the property "verified at the point of effect"
   now depends on a protocol rather than a function call. That is a *harder* thing to prove, bought
   with latency nobody can measure.
2. **It triples the contract surface before any contract has been exercised.** PLANNING.md §4
   already concedes that schemas written before code exercises them are wrong in ways only a
   running system reveals. Freezing them across three languages compounds that.
3. **It pays the cost up front and collects the benefit never**, unless a §3 trigger fires.

The design's genuinely good idea — **contract-first, wire-serializable, remotable ports** — is
adopted in full (invariant I3). That is what makes the polyglot option *cheap later* instead of
*mandatory now*.

---

## 3. Reversal conditions

The monoglot decision is overturned, for a **named component only**, when any of these is measured
on real hardware and recorded in `docs/rationale/benchmarks/`:

| # | Trigger | Response |
| :--- | :--- | :--- |
| **RT-1** | Cold index of a ≥1M-LOC repository exceeds **10 min** (target T7) after `anyio` worker-process parallelism is already in place | Rust indexer sidecar behind the `Indexer` port |
| **RT-2** | Control-plane RSS exceeds **300 MB** peak or **1%** idle CPU (target T6) and profiling attributes it to interpreter overhead rather than retained data | Move the resident component out of process |
| **RT-3** | Incremental re-index of a single file exceeds **200 ms**, breaking the editing agent's feedback loop | Same as RT-1 |

Absent a trigger, adding a language is a decision to spend engineering time on a term that does not
appear in the latency budget.

### If a trigger fires: which boundary

| Mechanism | Latency | Use when |
| :--- | ---: | :--- |
| **PyO3 / maturin (in-process FFI)** | ~100 ns/call, zero-copy via the buffer protocol | The component is a pure function over bytes — parsing, tokenizing, hashing, ranking. **Preferred.** Ships as a wheel; no process supervision, no protocol |
| **Unix socket / gRPC sidecar** | ~20–200 µs | The component holds long-lived state (a warm LSP pool, a resident index), needs its own supervision or crash isolation, or must be replaceable at runtime |

The port stays identical either way. That is the whole point of I3: the caller cannot tell which
side of the boundary the adapter lives on.

---

## 4. Commercial packaging and IP protection

The RFP asks how to sell this while protecting the source. The honest answer has two parts, and the
first one is uncomfortable.

### 4.1 Compilation is a speed bump, not protection

| Approach | What it actually gives you |
| :--- | :--- |
| **PyOxidizer / PyInstaller / freezing** | Bundles the interpreter with frozen bytecode. `.pyc` decompiles to near-source with off-the-shelf tools. **Effectively no protection.** |
| **Nuitka** | Genuine C compilation of Python semantics to a native binary. Raises the cost of recovery from minutes to days: no bytecode to decompile, but string literals, class and function names, and the module graph survive. **A real speed bump. Not a barrier to a determined competitor.** |
| **Cython** on selected modules | Same class of protection as Nuitka, applied surgically. Adds a build step per module |
| **Native Go or Rust binary** | Strongest of the shippable options. Go retains substantial type and symbol metadata; stripped Rust retains less. Still yields to a motivated reverse engineer |

No client-side technique resists an adversary who runs the binary. Anything shipped to a machine
you do not control is recoverable given enough motivation.

### 4.2 What actually constitutes the moat

Per PLANNING.md, *"the measurement discipline is the moat."* Sharpened:

| Asset | Protectable by compilation? | Protectable by not shipping it? |
| :--- | :--- | :--- |
| Orchestration code | Barely | Yes |
| Prompt corpus and tool schemas | No — extractable from any running binary at the network boundary | Yes, if generated server-side |
| Learned model-routing policy | No | Yes |
| Skill corpus / trajectory dataset | No | Yes |
| **Private held-out evaluation suite** (target T3) | Not applicable | **Yes — and it is never shipped in any topology** |
| Measurement methodology and ablation history | No | Yes |

The differentiating assets are **data and process**, not source. They are protected by where they
live, not by how they are compiled. A competitor handed the entire orchestration source still lacks
the trajectory corpus, the tuned prompts, the private benchmark, and the ablation record that says
which mechanisms actually earned their place.

### 4.3 Recommended distribution posture

1. **Phase 1–2: do not optimize for closed distribution.** No paying customer exists yet; designing
   for obfuscation now costs iteration speed and buys nothing.
2. **Keep the option free.** Invariant I3 means the engine can be lifted behind a wire boundary
   without touching a caller. A thin client (TUI/GUI) talking WS+JSON to a hosted engine is the
   posture where IP protection is *structural* rather than cosmetic — the code is never on the
   customer's machine. This is why decision **Q5** (WS+JSON for the UI leg) is load-bearing beyond
   the UI.
3. **If on-premise shipping becomes a contractual requirement**, layer it: Nuitka the control plane,
   keep prompts/routing/skills server-fetched under license check, keep the private suite in-house.
   State plainly to the client that this raises the cost of copying and does not eliminate it.
4. **Watch the license surface now.** Current dependencies are permissively licensed — pydantic
   (MIT), httpx (BSD), anyio (MIT), tree-sitter (MIT), SQLite (public domain), typer/rich (MIT).
   A single copyleft dependency pulled in later can foreclose closed distribution entirely, so
   license class becomes a review criterion on every dependency addition.

### 4.4 A note on studying competitors

Recorded here because it constrains what may enter the codebase, not just the docs: reference
harnesses are cloned to **study concepts**, never to copy implementation. Convergence toward a
competitor's design decision requires a rationale grounded in our own measurements. The full policy
and its rationale live in [reference teardowns §0](./rewrite_v300_reference_teardowns.md).

---

## 5. Decision summary

| Question | Decision | Reversal |
| :--- | :--- | :--- |
| Control-plane language | **Python 3.13** | RT-1 / RT-2 / RT-3, per component |
| Polyglot in Phase 1 | **No** | Same triggers |
| Inter-language mechanism, if needed | **PyO3 in-process** by default; sidecar only for stateful or separately-supervised components | — |
| UI transport | **WS + JSON**, TS types generated from the schema | A genuine cross-language sidecar boundary justifies protobuf there, not on the UI leg |
| Packaging, Phase 1–2 | `uv`-managed source install; no obfuscation | A signed on-premise contract |
| IP posture | Protect **data and process**; keep the hosted-engine topology structurally available | — |

Downstream: [architecture blueprint](./rewrite_v300_blueprint_arquitetura.md),
[ADR compilation](./rewrite_v300_decisoes_adr.md),
[UI and TUI](./rewrite_v300_uiux_tui.md).
