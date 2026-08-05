---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Ideas from Grok Build: an agenda for the architecture review

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding, defines no contract, and **decides nothing**. Contracts live in `src/`.

## 0. What this document is, and is not

A study of `src/grok_build` (xAI, 81 workspace crates, ~1.5M lines of Rust across `codegen/`,
`common/` and `build/`) read for **ideas worth putting on an agenda** — not for conclusions.

> **Scope.** This document covers the **infrastructure** crates. A companion pass over the *agent*
> — goal mode, the verification cascade, context economics, retrieval, the tool layer, the safety
> perimeter — is in [`rewrite_v300_grokbuild_teardown.md`](./rewrite_v300_grokbuild_teardown.md)
> and continues the numbering at **P16**. Read them together; where they overlap, the teardown
> defers to the item here.

Everything below is phrased as a proposal with an open question attached. Several of these would
*change decisions already recorded* in [the ADRs](./rewrite_v300_decisoes_adr.md); where that is the
case it is stated explicitly, because a suggestion that quietly contradicts a settled decision is
worse than no suggestion. **Nothing here is adopted until the review decides.**

Under [A-007](./rewrite_v300_decisoes_adr.md), what transfers is understanding — an algorithm, a
seam, a failure mode. No code moves, and the fact that grok_build is Rust while AETHER is Python is
noted per item, because some of these ideas are language-neutral (OS primitives, protocol shapes) and
some are cheap in Rust and expensive in Python.

Proposals are graded by how strongly the evidence supports them, not by how attractive they sound:

| Grade | Meaning |
| :--- | :--- |
| **A** | Strong candidate. Addresses a known gap or a cost we will definitely pay |
| **B** | Worth measuring. Plausible, but the benefit is unproven for our workload |
| **C** | Noted for completeness. Probably decline, recorded so it is not rediscovered |

---

## Part I — Grade A: strong candidates

### P1 · Worktree creation via copy-on-write, and a pre-warmed pool

**What grok_build does.** `xai-fast-worktree` (~10k lines) exists solely to make worktree creation
fast: `git worktree add --no-checkout` for instant metadata, then **parallel CoW file cloning with
hash-based sharding**, **BTRFS snapshot support for O(1) cloning** on Linux, optional dirty-file
replication, and a **sync API for pre-created worktree pools**.

**Why it matters to us.** Best-of-N creates N worktrees per task. A plain `git worktree add` is a full
checkout — on a large repository that is seconds to tens of seconds, *per candidate, per task, per
benchmark run*. Across a Pro suite at N candidates this is not a rounding error; it may be a
meaningful share of wall-clock, and it lands on the single most expensive path in the system.

**What it would change.** `WorktreeManager` gains a CoW-capable implementation where the filesystem
supports reflinks (btrfs, XFS with reflink, APFS, overlayfs) with a plain-checkout fallback, plus a
pool that materializes worktrees ahead of the fan-out rather than during it. The port signature does
not change — this is entirely an adapter concern, which is a point in its favour.

**Cost and caveats.** Filesystem-dependent, so it needs a capability probe and a fallback path.
`reflink`/`copy_file_range` is available from Python. A pool adds lifecycle state to manage. And we
have **no measurement yet** showing worktree creation is a bottleneck for us.

> **Question for the review:** do we instrument worktree creation time in M1a — a cheap timer on an
> existing operation — so that by M2 we know whether this is worth building at all?

---

### P2 · Two-phase budget reservation, instead of spend-then-record

**What grok_build does.** The workflow engine asks its host for `ReserveAgentCalls { count }` before
spawning and `ReleaseAgentCalls { count }` after, alongside a `BudgetQuery`. Budget is *reserved*,
not merely observed.

**Why it matters to us.** Our `ResourceGovernor` leases concurrency but accounts spend **after the
fact** (`record_spend`), and the run loop checks `remaining_budget() <= 0` before a step. Under
sequential execution that is fine. Under **Best-of-N fan-out it is a race**: N candidates each check
"budget remaining > 0", all pass, and all spend. The overrun is bounded by N, and N is exactly the
knob we plan to increase.

**What it would change.** A reserve/commit/release triple on `ResourceGovernor`: reserve before
dispatching a fan-out, commit actual spend on completion, release the unused remainder. Same shape as
the lease mechanism already there, applied to money instead of concurrency.

**Cost and caveats.** Small. The interesting design question is what happens when a reservation cannot
be met mid-fan-out — degrade to fewer candidates, or refuse the whole fan-out? That is a policy
choice, not a mechanism one.

> **Question for the review:** is bounded overrun acceptable at our N, or does budget correctness under
> concurrency belong in the M1a governor while it is still three functions?

---

### P3 · A typed pause taxonomy instead of a binary outcome

**What grok_build does.** A workflow terminates as
`Completed | Paused { kind, message } | BudgetExceeded | Cancelled | Failed`, where
`PauseKind` is `User | BackOff | NoProgress | Verification | Infra`.

**Why it matters to us.** We have the pieces scattered across three documents and no single type: the
[disposition ladder](./rewrite_v300_mecanismo_edicao.md) has rungs, the
[API error taxonomy](./rewrite_v300_mecanismo_edicao.md) has recovery actions, the `ask` permission
state is a pause, and `BudgetExhausted` parks a run. **Five different pause reasons already exist in
our design and none of them share a type.** Their taxonomy maps onto ours almost exactly —
`NoProgress` and `Verification` are the repair loop, `BackOff` and `Infra` are the API taxonomy, `User`
is the approval gate.

**What it would change.** One `RunOutcome` sum type in the domain layer, surfaced on the event stream
and rendered distinctly by the TUI. It also gives the UI something honest to display: "paused, waiting
on you" and "paused, backing off" are very different things for an operator watching an 8-hour run.

**Cost and caveats.** Nearly free at M0 — it is a domain type. Expensive later, because every producer
and consumer has to change.

> **Question for the review:** does this belong in the M0 contract freeze, given it costs almost nothing
> now and is a breaking change afterwards?

---

### P4 · Engine / host split, with an explicit `replayed` flag

**What grok_build does.** The workflow engine is pure and requests every effect from the host through
a typed channel: `SpawnAgent`, `Log`, `Telemetry`, `RenderTemplate`, `WriteScratchFile`, `Phase`.
Three of those requests carry **`replayed: bool`** — the host is told whether it is seeing an original
event or a replay from the journal.

**Why it matters to us.** We adopt the pure-controller pattern in two places already (tool guardrails,
policy engine), so the split itself is familiar. The `replayed` flag is the part we do not have, and
it solves a problem hibernation creates: **a resumed run replays its journal, and every side effect in
that replay would fire twice** — duplicate log lines, duplicate telemetry, duplicate notifications.
Marking the replay lets each host decide whether to suppress.

**Why it is more than a logging nicety.** Our determinism target (T8, byte-equal replay) is currently
about *model calls*. Effects outside the model — telemetry, UI events, scratch files — have no
equivalent story, and hibernation plus durable resume is a core capability, not a growth one.

**Cost and caveats.** Small if done at M0/M1a, because it is a field on an event. It does raise a real
question about which effects are idempotent and which are not, and we have not enumerated that.

> **Question for the review:** should the event envelope carry replay provenance from the first
> version, and who owns the idempotency classification?

---

### P5 · One token estimator, shared by the gate and the display

**What grok_build does.** `xai-token-estimation` is 255 lines and is described as the *single source of
truth* for the estimation heuristic used by the context command, the session-info display, **the
auto-compact gates**, the preflight overflow check, and every client renderer.

**Why it matters to us.** This is the same principle we already adopted from Hermes for failure
classification — one classifier shared by the guardrail and the user-visible error tag. Applied to
tokens it is arguably more important: if the compaction trigger and the TUI's context meter disagree
about how full the window is, an operator watching a run cannot tell whether a surprising compaction
was correct. **Two estimators is a debugging trap, and estimators drift silently.**

**Cost and caveats.** Trivial. One module, one import.

> **Question for the review:** any reason not to make this a rule at M0, given that the alternative is
> discovering the drift in an incident?

---

## Part II — Grade B: worth measuring

### P6 · Workflow-as-script, as an alternative to workflow-as-config

**This one contradicts a decision we have already recorded**, which is why it is here rather than
buried.

**What grok_build does.** Workflows are **Rhai scripts** — an embedded scripting language — not YAML,
not a node graph. They are `validate`d, journaled, and dry-run before execution.

**What we decided.** [ADR-0018](../../08-decisions/0018-native-workflow-dag.md) and
[A-024](./rewrite_v300_decisoes_adr.md) put the pipeline in a typed `WorkflowStep` DAG serialized to
config, on the grounds that memoization by input digest makes ablation cheap and that config-driven
composition needs no kernel change.

**The honest tension.** A DAG is declarative and analyzable — you can memoize it, diff it, and validate
it statically. A script is expressive — loops, conditionals, and early exit are natural, and authoring
a new workflow does not require extending a node vocabulary. Our own reasoning for the DAG rests
substantially on memoization, and **a script is much harder to memoize**, because the unit of caching
is not obvious.

There is also a third position neither of us took: a DAG *of* scripted nodes, where the graph is the
memoization and scheduling unit and each node's body is free-form.

**Relevant to the decision:** A-024 already carries a reversal condition — if the node abstraction is
not carrying weight by the M2 boundary, collapse it. That is the natural moment to look at this again
with evidence rather than taste.

> **Question for the review:** do we keep A-024 as written and revisit at its own reversal point, or
> does the expressiveness argument justify examining a hybrid earlier?

---

### P7 · Dry-run validation of a workflow before it executes

**What grok_build does.** `validate.rs` exposes `validate_script` and
`validate_script_with_agent_budget`. Its tests describe failure modes it catches — missing metadata,
runtime misuse, engine limits reported as dry-run failures, and "authoring landmines are fixed or
hinted". A pause counts as a *valid* outcome.

**Why it matters to us.** Our validation story is type checking plus the conformance suite: both
static. **A pipeline that type-checks can still be wrong** — a node wired to an incompatible producer,
a budget that cannot cover its own fan-out, a graph that cannot terminate. Catching that before a run
starts is cheaper than catching it thirty minutes in, and dramatically cheaper during a benchmark
sweep where the same misconfiguration repeats across every task.

**Cost and caveats.** A dry-run mode means every node needs a no-op path, which is real work and a
maintenance surface. Cassette replay already gives us something adjacent, though it validates
*behaviour against a recording*, not *configuration against limits*.

> **Question for the review:** is graph validation distinct enough from replay to justify its own
> mechanism, and would `--dry-run` on the bench runner have caught the failures we actually hit?

---

### P8 · Circuit breaker on a sliding window with a minimum sample count

**What grok_build does.** `xai-circuit-breaker` trips when
`sample_count >= min_samples AND error_rate >= error_rate_threshold` over a live window. It is
protocol-agnostic, operating on an `Outcome`, with separate presets for server- and client-side
consumers running the same state machine.

**Why it matters to us.** [A-022](./rewrite_v300_decisoes_adr.md) specifies count-based guardrails —
warn at 2 exact repeats, block at 5, and so on. Counters have two known weaknesses: they trip on a
short unlucky streak early in a run, and they **never** trip on a sustained 40% failure rate that is
clearly pathological. A rate-over-window with a minimum sample count fixes both, and the min-samples
term is precisely what stops it firing on noise.

**Cost and caveats.** More state per signal and two parameters instead of one, which is more to tune —
and tuning cost is real when every parameter is an ablation. Counters are also easier for an operator
to reason about ("it failed the same way five times") than a rate.

> **Question for the review:** do we ship counters in M2 and revisit if the failure patterns we see
> justify a window, or is the rate model worth the extra tuning surface from the start?

---

### P9 · Compaction as a shared core with trait seams

**What grok_build does.** `xai-grok-compaction` is a *transport-agnostic compaction engine* holding
policy, prompts, selection and assembly — and explicitly **not** trigger wiring, transport,
persistence, replay/rewind, state commit, or metrics, all of which stay in the host. It depends on
neither the conversation-type crate nor the sampling-types crate, decoupling through named seams:
`CompactionItem`, `ItemTokenCounter`, `CompactionSampler`, and observers. It also distinguishes
**intra-** from **inter-**compaction as separate styles.

**Why it matters to us.** We treat the compactor as one component behind no seam. Their split says
something we have not considered: **the compaction *policy* and the compaction *trigger* are different
concerns with different reasons to change.** Policy is an ablation target; trigger wiring is host
plumbing. Fusing them means every trigger experiment touches policy code.

The intra/inter distinction is the part we most clearly lack — we have one notion of compaction where
they have two.

**Cost and caveats.** This is a Rust crate boundary; in Python it is a module boundary plus protocols,
which is cheaper but also less enforced. And it is a real question whether a component we have not yet
built once deserves an internal seam on day one — the port-rent rule ([A-010](./rewrite_v300_decisoes_adr.md))
argues against speculative boundaries.

> **Question for the review:** worth understanding what intra- vs inter-compaction means for our design
> before we build the compactor, even if we decline the seam?

---

### P10 · Hunk tracking with agent-versus-external attribution

**What grok_build does.** `xai-hunk-tracker` runs an **actor** on a dedicated task with exclusive state
— no locks — receiving commands from both the edit tool and a filesystem-notify loop, and tracking
every hunk with **source attribution: Agent or External**.

**Why it matters to us.** We have no answer to "who changed this file". Three of our scenarios need
one: an operator editing a file in the TUI while a run is in flight; a formatter or watcher mutating
files under the agent; and the `tests_unmodified` gate, which today asks *whether* tests changed but
not *by whom*. Attribution turns "the diff is unexpected" into "the diff is unexpected **and it wasn't
us**", which is a different and much more actionable statement.

**Cost and caveats.** Requires a filesystem watcher and an ownership discipline. The actor pattern
maps to a single `asyncio` task owning state — natural in Python. But this is a growth-tier capability
answering a problem we have not yet hit, and our container perimeter already reduces the surface for
external mutation.

> **Question for the review:** is attribution worth building before we have an interactive TUI where a
> human can edit mid-run — or is that exactly the moment it becomes necessary?

---

## Part III — Grade C: noted, probably decline for now

### P11 · Process-level OS sandbox plus per-subprocess network blocking

`xai-grok-sandbox` applies an OS-level sandbox **once at process startup**, covering both in-process
filesystem calls and child processes, with a deliberate asymmetry: **process-level network stays open
because the agent needs the LLM API, while child-process network is blocked per-subprocess via
seccomp.**

That asymmetry is a genuinely elegant answer to a problem [our security design](./rewrite_v300_seguranca_sandbox.md)
sidesteps by putting everything in a container: the harness process itself needs egress, so "block the
network" is not available at the process level. Worth recording as a lighter-weight option for the
local-development profile, where a container is heavy. **Not a replacement for the container
perimeter** — ADR-0006 stands, and a second security mechanism is a second thing to get right.

### P12 · Filesystem-aware SQLite journal-mode selection

`xai-sqlite-journal` exists because **WAL mode breaks on network filesystems**: it relies on an mmap'd
`-shm` file plus coherent shared memory and reliable POSIX locks, none of which NFS provides, and a
peer host rebuilding the `-shm` during recovery corrupts the mapping.

We use SQLite for the trajectory store. If anyone runs with an NFS-mounted home — common in university
and enterprise environments — we would ship this bug. The fix is a filesystem probe selecting the
journal mode. **Low effort, low probability, high embarrassment**; worth a line in the operational
notes even if we decline the code.

### P13 · A pure-data types package with zero runtime dependencies

`xai-grok-workspace-types` is 9,334 lines that are *intentionally* pure data — no async runtime, no
I/O, nothing beyond serialization — explicitly so it can be depended on from anywhere "including the
eventual WASM browser SDK".

Our `domain/` is already pure by invariant I1 and enforced by import-linter, so we have the property.
Recorded because their *reason* is a use case we have not considered: a browser or edge client
importing the domain types directly rather than through a generated schema. If the GUI ever needs to
validate locally, this is the shape that allows it.

### P14 · Hooks: capability injected at install, data-only at dispatch

`xai-agent-lifecycle` states its contract precisely: hook contributors "receive data-only per-hook
inputs at dispatch time; anything they act through is a **capability injected at install time**, and
they **never own loop control**."

This is our hooks rule ([security §1.5](./rewrite_v300_seguranca_sandbox.md)) stated better than we
stated it. No design change — worth borrowing the phrasing, because "a hook may veto, never grant" and
"capability at install, data at dispatch" are the same rule and the second is more precise about
*how*.

### P15 · Sub-agent resolution as a pure function

`xai-grok-subagent-resolution` (3,023 lines) extracts the *resolution* phase of spawning — given a
request plus roles, personas and parent state, resolve effective model, persona, capability mode and
isolation — into a pure library separate from the spawning itself.

Consistent with [A-019](./rewrite_v300_decisoes_adr.md), where a sub-agent gets a scoped registry and
its own budget. The idea worth keeping is that **the resolution is a pure function of the request and
the parent state**, and therefore unit-testable without spawning anything. Cheap to honour when we
build sub-agents; nothing to decide now.

---

## Part IV — Two structural observations

Not proposals, but the two things most worth discussing about how grok_build is organized.

**81 crates for ~117k lines.** Roughly 1,400 lines per crate. The boundaries are drawn far finer than
we plan — separate crates for token estimation (255 lines), the circuit breaker, PTY control, journal
mode selection. In Rust this buys enforced acyclic dependencies, parallel compilation, and precise
feature gating; in Python a package boundary buys much less and costs more ceremony. **The idea worth
taking is not the granularity — it is which *seams* they considered worth naming**, and several of
them (compaction policy vs. trigger, tool types vs. protocol vs. runtime, workspace types vs. client)
are seams we have not drawn.

**Tools are split three ways** — `xai-tool-types` (canonical types), `xai-tool-protocol` (JSON-RPC 2.0
envelope, method catalog, wire enums, numeric↔string error mapping), `xai-tool-runtime` (the `Tool`
trait, dispatch, context, streams, and a `ToolSearchIndex`). Our `ToolRegistry` fuses all three.

That split is invariant **I3** taken further than we take it: not merely *"the port could be
remoted"*, but *"the wire protocol is a separate artifact with its own error-code mapping"*. It is
also how they support tools served over RPC from a separate process. Whether that is worth it for us
depends entirely on whether tools ever run out-of-process — which is not on our roadmap, but is
exactly the kind of thing I3 exists to keep cheap.

---

## Part V — Suggested agenda

Ordered so that the cheap-now-expensive-later items come first, since those are the ones where
deferring is itself a decision.

| # | Decide | Why now |
| :--- | :--- | :--- |
| 1 | **P3** typed pause taxonomy · **P4** `replayed` flag · **P5** shared token estimator | All three are M0 domain-type decisions: nearly free before the schema freeze, breaking changes after |
| 2 | **P2** budget reservation | Cheap while the governor is three functions; a correctness gap under fan-out |
| 3 | **P1** worktree CoW + pool | Decide only to **instrument** now; build later if the number justifies it |
| 4 | **P6** script vs DAG | Does not need deciding today — A-024's reversal point at M2 is the natural moment, with evidence |
| 5 | **P8** breaker model · **P9** compaction seam · **P7** dry-run · **P10** hunk attribution | M2-and-later; the useful output today is understanding the trade, not choosing |
| 6 | **P12** SQLite journal mode | One line in the operational notes; costs nothing to record |

**Nothing above is adopted.** Items that survive the review should become ADRs with reversal
conditions like every other decision in this set — and, per RFP §1.1, any that changes a mechanism
needs an ablation before it reaches production rather than an argument.
