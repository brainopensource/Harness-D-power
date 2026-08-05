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

## 4b. Revision-A amendments from the competitor review

### 4b.1 FFI versus IPC — the numbers, and why they do not change the recommendation

The review proposes PyO3 in-process FFI (**<50 ns C-ABI**) over IPC/gRPC (**1.5–5.0 ms**) for
tree-sitter parsing and FTS5 indexing. Both figures are plausible orders of magnitude and **neither is
our measurement** — they are recorded as design targets with a named benchmark, per
[measurement §1c.2](./rewrite_v300_measurement_strategy.md).

The comparison is also the wrong axis for the decision this document makes. §1's argument is not that
FFI is slow; it is that **the LLM round-trip dominates by four to seven orders of magnitude**. Against
a 2–30 s model call, the difference between 50 ns and 5 ms is not a design input. The FFI-vs-IPC
question becomes live only *after* a reversal trigger fires — and §3 already resolves it in the same
direction the review proposes:

> Response is a sidecar behind the existing port — **PyO3 in-process by default**, socket/gRPC only for
> stateful or separately-supervised components.

So: recommendation unchanged, and the review's preference is already the recorded default for the case
where it matters. What the competitor study **does** add is confirmation of *where* the trigger is most
likely to fire. Across three teardowns the one place a compiled language clearly earns its keep is the
**incremental tree-sitter index over a large repository** — Grok Build's `xai-codebase-graph` uses
rayon-parallel parsing, memory-mapped zero-copy reads, a disk cache surviving restart, and an actor
answering queries in place without cloning the index. That is exactly the shape RT-1 and RT-3 point at.
**Nothing else in three teardowns argues for a second toolchain.**

### 4b.2 Copy-on-write worktrees are a filesystem question, not a language one

The review proposes OverlayFS / Btrfs CoW mounts for `<10 ms` workspace clones and a pre-warmed
container pool for `0 ms` allocation. Two observations before this is treated as a runtime decision:

1. **It is not one.** `reflink` and `copy_file_range` are reachable from Python; Btrfs snapshots are
   `subvolume snapshot`; OverlayFS is a mount. The port signature does not change — this is entirely a
   `WorktreeManager` adapter concern, which is a point in its favour and why it belongs in
   [the blueprint §8b.4](./rewrite_v300_blueprint_arquitetura.md) rather than here.
2. **The benefit is filesystem-dependent and we do not know which case we are in.** Grok Build's own
   pool module is macOS-only in production, with the reason stated: *"Linux has O(1) BTRFS snapshots;
   the pool adds value only on macOS/APFS where worktree creation is O(file_count)."* On a Btrfs or
   XFS-with-reflink host much of the claimed gain may already be free.

The proposal that survives is the cheap one: **instrument worktree creation in M1a** — a timer on an
existing operation — and decide at M2 with a number.

### 4b.3 PTY and process-scope enrolment

A PTY-backed execution adapter (blueprint §8b.6) is a Python question with a clean answer:
`pty`/`ptyprocess` in stdlib and on PyPI, no second toolchain. The discipline worth importing is not the
PTY itself but the surrounding rule — Grok Build's lint configuration **bans raw process spawning
outright**, with the reason inline: *"an unenrolled child outlives the session that started it; use
`ProcessScope::enroll`."* Every spawned process belongs to a scope that dies with the run.

For an ≥8h unattended target that matters more than it does for an interactive session, and its
runtime-relevant consequence is a T6 one: leaked child processes are the most common way a
long-running Python service acquires a resident-memory trend that profiling attributes to the
interpreter.

### 4b.4 Prompt obfuscation, corroborated

§4.1's position — compilation is a speed bump, not protection — is confirmed by an unusually direct
data point. Grok Build ships a native binary and obfuscates exactly one thing: the **prompt text**,
XOR-encrypted at build time by a Python script with a position-dependent key, trivially reversible, in
a 139 KB generated file. A well-funded competitor shipping compiled code concluded that prompts were
the only asset worth a speed bump, and that a speed bump was enough.

---

## 4c. Fork F1 — the Rust core. Both positions, for the meeting

This is the widest disagreement between the two proposals and the one most worth spending meeting time
on. Both positions are stated here at full strength; the section deliberately does not resolve it.

### 4c.1 The two positions

| | **Track A** | **Track B** |
| :--- | :--- | :--- |
| Shape | Python 3.13 monoglot. A sidecar behind an existing port, **per component**, when a measured trigger fires | `src/aether/core_rs/` with **8 named modules**, PyO3 C-ABI, built by Maturin, **at Sprint 0** |
| Modules | none named | `ast_treesitter` · `fast_indexer` · `fast_worktree_cow` · `hunk_tracker` · `seek_sequence` · `exec_policy_ast` · `pty_harness` · `prompt_queue` |
| Trigger | RT-1 cold index >10 min on 1M LOC · RT-2 RSS >300 MB or idle CPU >1% · RT-3 incremental re-index >200 ms | None — it is foundational |
| Claimed benefit | Fastest iteration; one toolchain; the LLM round-trip dominates by 4–7 orders of magnitude | <50 ns FFI vs 1.5–5.0 ms IPC; <10 ms CoW worktrees; ~60 MB RSS vs ~150 MB |
| Claimed cost of the other side | A build step inside the dev loop and inside the self-improvement loop; eight subsystems coupled to one language; harder to swap, not easier | GIL-bound CPU parallelism; higher footprint; a rewrite later instead of a design now |

### 4c.2 What is actually contested, and what is not

**Not contested.** Both tracks agree that (a) the hot paths are AST parsing and indexing, (b) PyO3
in-process is the right *mechanism* if a sidecar is built — §3 of this document already says so — and
(c) the port signature does not change either way, because I3 makes the boundary wire-serializable.
So the fork is about **timing and scope**, not about technology.

**Contested, honestly.** Track A's position is safe and, from a builder's perspective, evasive: it
never names a module and defers everything to triggers that may never be instrumented. Track B's
position is decisive and unmeasured: it sets `<50 ns`, `<10 ms` and `0 ms` as *sprint acceptance
gates* for latencies nobody has timed on this repository.

Three specific problems with the numbers, offered as things to check rather than as refutations:

- **`<50 ns` conflates the FFI crossing with the work.** A PyO3 call can be tens of nanoseconds; a
  tree-sitter parse of a real source file is milliseconds in any language. Track B's blueprint reads
  *"passa o hunk por Tree-sitter `ast.parse` em <50ns"*, which applies the crossing cost to the parse.
  The correct comparison is Python-tree-sitter (already a C extension) against Rust-tree-sitter — a
  much narrower gap than 50 ns vs 4 ms suggests.
- **`<10 ms` may already be free, or may be unreachable.** It is a filesystem property. Grok Build's
  own worktree pool is macOS-only in production, with the reason in the source: *"Linux has O(1) BTRFS
  snapshots; the pool adds value only on macOS/APFS where worktree creation is O(file_count)."* On a
  reflink-capable host much of the gain may exist without any Rust.
- **`0 ms` container allocation is amortized, not achieved.** A pre-warmed pool drains under Best-of-N
  fan-out — the exact workload it exists for — and the Nth subagent waits for a cold container. The
  honest metric is p99 allocation latency under fan-out.

### 4c.3 A third position, offered as a suggestion

Neither "defer everything behind triggers that nobody instruments" nor "commit eight modules in
sprint 0". **Instrument the two candidate hot paths in the first working slice** — a timer on worktree
creation and a timer on AST parse-and-validate — and let the numbers select the modules, one at a
time, behind ports that already exist.

That costs one afternoon of instrumentation, defers the toolchain commitment by exactly one milestone
rather than by three, and produces the number that settles the argument instead of a preference. It
also preserves the property both tracks say they want: a component moves to Rust **because it was
measured**, which is the same rule the rest of this project applies to every other mechanism.

If the review prefers Track B's side outright, the sequencing that reduces the risk most is to take
the modules in the order of measured benefit — almost certainly `fast_indexer` and `ast_treesitter`
first, since those are the only two the competitor study shows a compiled language clearly winning —
and to leave `pty_harness`, `prompt_queue` and `exec_policy_ast` in Python, where none of them is
CPU-bound.

### 4c.4 Two smaller items from Track B, adopted with no conflict

**Maturin as the build tool**, if and when `core_rs/` exists. Track B names it; this document did not.
It is the right choice — it produces a wheel, keeps `pip install -e .` working, and does not require
contributors to have Rust installed unless they touch that crate.

**Windows Restricted Tokens / Job Objects** as the Windows sandbox backend, alongside `bwrap` on Linux.
Track B names both; ADR-0016 names rootless Podman as one backend of a cross-platform abstraction but
never says what the others are. Recorded in [security](./rewrite_v300_seguranca_sandbox.md).

### 4c.5 Fork F12 — IP protection

Track B's runtime matrix rates Nuitka-compiled Python as **"Excelente"** protection. §4.1 of this
document argues that compilation is a speed bump.

The corroboration from the competitor study is unusually direct and worth putting in front of the
meeting: **Grok Build ships a native Rust binary and still obfuscates only the prompt text**, with a
trivially reversible XOR generated by a build script. A well-funded competitor shipping compiled
machine code concluded that prompts were the only asset worth protecting, and that a speed bump
sufficed.

That does not make Nuitka worthless — it raises the cost of casual copying, which is a real product
decision. It does mean "Excelente" overstates it, and that betting the commercial moat on packaging
rather than on the measured harness is the risk worth naming.

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
