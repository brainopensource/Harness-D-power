---
status: normative
updated: 2026-08-05
---

# AETHER v3.0.0 — Normative Specification

**This is the minimal statement of what is true.** It is not a summary of the rationale and
it does not argue. Where a contract can live in code it lives in code, and this document
points at it — `src/aether/ports/` defines, `docs/spec.md` navigates.

**When this document and the code disagree, the code is right and this document is the bug.**

Decisions and their reversal conditions are ADRs under [`decisions/`](decisions/README.md).
Why any of it is so is [`vision.md`](./vision.md) and the Phase 0 trail in
[`concepts/`](concepts/README.md).

---

## 1. What the system is

A harness: the system around a coding model that gives it tools, a workspace, memory, a
security perimeter and a feedback loop. We do not build the model.

**We measure two numbers, always together.** *Absolute* resolve rate on SWE-bench Pro and
Verified, and **lift** — the delta between a bare model call and the same model inside
AETHER on identical tasks. Lift is the committed target; absolutes are provisional
(ADR-0004). **An absolute number is never published without its lift.**

---

## 2. Invariants

Each has a mechanical enforcement. An invariant enforced by discipline is a wish.

| # | Invariant | Enforced by |
| :--- | :--- | :--- |
| **I1** | **Pure domain.** `domain/` imports no DB driver, filesystem, or HTTP client | import-linter `domain-is-pure` |
| **I2** | **Typed ports.** All I/O crosses a `Protocol` boundary | pyright strict, zero errors |
| **I3** | **Wire-serializable ports.** Every method `async`; only serializable payloads — no file handles, callables, generators, live objects, or `Path` | Reflection contract over all ports |
| **I4** | **Adapter substitutability.** Every adapter passes the same parametrized conformance suite | One suite, N adapters, in CI |
| **I5** | **Single dispatch choke point.** Every effect passes `kernel/dispatch.py`; grants verified at the point of effect, not at authorization | Architecture test: no bypass path |
| **I6** | **Frozen extension resolution.** Entry points resolved once at composition, then frozen; runtime registration raises | Composition test |
| **I7** | **Generator ≠ Evaluator.** The agent that writes code cannot modify the tests grading it | `tests_unmodified` hard gate |
| **I8** | **Immutable TCB.** Policy, evaluator, gates, benchmark definitions and CI are unmodifiable by agent or meta-loop | import-linter `tcb-isolation` + CI `tcb-check` |
| **I9** | **Hard gates admit; proxies rank.** A learned scorer may order candidates, never admit one | Type-level `rank()` / `admit()` separation |
| **I10** | **Prompt cache is architecture.** Fixed prefix layers, explicit breakpoints; the gated metric is **harness-side prefix stability** | CI floor on byte-identical-prefix rate over a fixed replay |
| **I11** | **Taint cannot acquire authority.** Every context span carries a provenance label; propagation is deterministic; an untrusted or untrusted-derived span can never satisfy a policy predicate that grants or widens capability | Pinned injection corpus in CI — gate is **zero capability grants** (ADR-0015) |

**I3 is the one that saves the project.** It lets any port move out of process — to a
compiled sidecar, a container, a remote peer — without changing a caller. It is nearly free
on day one and impossible to retrofit, which is what makes ADR-0001 affordable.

---

## 3. Structure

Dependencies point downward only. The kernel and the evaluator may not import from the
agency layer: **the thing that judges cannot reach up into the thing being judged.**

```
src/aether/
├── domain/          pure models — zero I/O (I1)
├── ports/           Protocols — async, wire-serializable (I2, I3)
├── kernel/          TCB — dispatch, bus, governor, policy (I5, I8)
├── adapters/        behind ports
├── measurement/     TCB — evaluator, gates, statistics, runner, harvester
├── agency/          the mutable capability layer — sources, assembler, inference, roles
│   └── context/     assembler · compactor · tokens · taint_gate
├── workflow/        WorkflowStep DAG + schema/validator/executor (ADR-0013, ADR-0014) — TCB
├── evolution/       offline only — never imported by anything (ADR-0006)
├── tui/
├── engine.py        headless API — the surface every client uses
└── composition.py   explicit wiring; no DI container
```

**The full import lattice.** Every package has a declared position; the import-linter
contracts encode all of it. A package outside the lattice is where coupling accretes
unobserved.

```
engine  >  workflow  >  agency  >  measurement  >  kernel  >  adapters  >  ports  >  domain
```

`agency` sits **below** `workflow` (ADR-0018): the TCB executor drives mutable capabilities,
not the other way round.

| Package | May import | May be imported by | Contract |
| :--- | :--- | :--- | :--- |
| `domain/` | stdlib + pydantic only | everything | `domain-is-pure` |
| `ports/` | `domain/` | everything above | `ports-are-pure` |
| `adapters/` | `ports/`, `domain/` | `kernel/`, `composition.py` | layer order |
| `kernel/` | `adapters/`, `ports/`, `domain/` | `agency/`, `workflow/`, `engine.py` | `tcb-isolation` |
| `measurement/` | `ports/`, `domain/`, `kernel/` | `agency/`, `workflow/`, `engine.py` | `tcb-isolation` |
| `agency/` | `kernel/`, `ports/`, `domain/` | `workflow/`, `engine.py` | layer order + `agency-cannot-reach-the-judge` |
| `workflow/` | `agency/`, `kernel/`, `measurement/`, `ports/`, `domain/` | `engine.py` | layer order |
| `evolution/` | **`ports/` and `domain/` only** | **nothing** | `tcb-isolation` forbidden importer |
| `tui/` | `engine.py`, `domain/` | — | layer order |

Four rules carry the weight:

- **`kernel/` and `measurement/` may not import `agency/` or `workflow/`.** The thing that
  judges cannot reach up into the thing being judged.
- **`agency/` may not import `measurement/`, even though the bare lattice line above would
  permit the edge** (`measurement` sits below `agency`). A dedicated forbidden-import contract
  closes that gap: `spec.md`'s port-versioning and TCB rules exist so that a capability cannot
  construct its own `Evaluator` and become a second judge, which is the one thing I7 forbids.
- **`evolution/` imports no higher than `ports/` and is imported by nothing.** "Offline" is a
  description; this is the import rule that makes it one (ADR-0006).
- **`workflow/` sits above `kernel/`** because the executor dispatches through the choke point.
  The topology schema, validator and executor are TCB; the topologies themselves are not
  (ADR-0014).

**Language: Python 3.13, monoglot.** Compiled sidecars arrive per component on a measured
trigger, never speculatively (ADR-0001).

---

## 4. Ports

**Eight boundaries, nine protocols.** A port enters `ports/` **in the same change as its
first adapter and its conformance test** (ADR-0005). A mock adapter satisfies that rule only
when the first real adapter is named. No other exceptions; the predecessor declared seventeen
and five had no implementation.

`ModelProvider` · `Workspace` · `WorktreeManager` · `ToolRegistry` · `PolicyEngine` (TCB) ·
`ResourceGovernor` · `TrajectoryStore` · `Evaluator` (TCB) · `Indexer`

*(`Workspace` and `WorktreeManager` are two protocols on one boundary.)*

**Growth tier**, admitted only with an adapter: `CodeGraph`, `Memory`, `Toolchain`,
`CandidateSearch`. **Not ports:** `Orchestrator`, `MetaImprover`, short-term memory,
measurement, and `LSPAdapter` (ADR-0011).

**Port rules**, asserted generically by reflection: every method `async`; no `Path`, file
handle, callable, generator or live object; no untyped `dict[str, Any]`; all datetimes
timezone-aware; **no `Grant` in any public signature**.

**TCB port residency.** A port is a boundary; where its *concrete implementation* lives decides
whether the path-keyed import contracts select it. So it is a rule, not a style:

> **The implementations of TCB ports live inside TCB paths.** `PolicyEngine` in `kernel/`,
> `Evaluator` in `measurement/`. **Never in `adapters/`.** Only non-TCB ports have adapters
> under `adapters/`.

Without this, `tcb-isolation` selects an evaluator that has quietly moved into the mutable
layer, and I7 is enforced by a contract pointing at the wrong directory.

**Port versioning.** Protocols are **frozen per minor version and additive-only within one**:
a new optional method or an added optional field is a minor change; anything that breaks an
existing adapter is **a new protocol name**, entering under ADR-0005 with its own first
adapter. For a project whose thesis is "swap anything," a compatibility rule is what makes the
swap safe; the alternative is discovering the contract by breaking it.

---

## 5. Execution

Every effect follows one path, and an architecture test proves there is no second:

```
authorize → verify grant → acquire lease → dispatch → release
```

`verify` happens immediately before the effect, not at authorization time. Between issuance
and use, arguments can change and a resumed run can carry a stale grant.

**Untrusted content can never acquire instruction authority (I11).** Every context span
carries one of five provenance labels — `trusted-system`, `operator`, `agent`,
`untrusted-external`, `untrusted-derived`. Repository files, issue text, tool output, test
output and web results are `untrusted-external` **at birth**. Propagation is deterministic and
monotone: a completion that consumed any untrusted span produces `untrusted-derived` output.

The binding rule sits in the policy engine, not in the gate: **a request that widens capability
fails closed when any span justifying it is untrusted or untrusted-derived.** The gate labels;
the policy decides. Enforcement is a pinned injection corpus in CI whose gate is **zero
capability grants** (ADR-0015).

Untrusted content may *inform* work — the agent must read the repository. It may not
*authorize* it.

**The sandbox is the perimeter** (ADR-0008). Shell AST analysis **classifies** effects and
escalates; it never contains. A control that looks like security invites the real security
to be removed.

**Budget is reserved before execution, not recorded after** — a reserve/commit/release
triple. This matters most under Best-of-N fan-out, which is where the predecessor's
after-the-fact accounting broke.

**The workflow DAG is the execution structure; the event stream is the observation
structure.** Nodes emit events; events never drive node scheduling (ADR-0013).

---

## 6. Trusted Computing Base

| | Contents |
| :--- | :--- |
| **Immutable** | Policy engine · evaluator · gates · **task manifests and split assignment** · **gate-family declarations** · **workflow schema, validator and executor** · CI configuration · `.importlinter` |
| **Mutable by the meta-loop** | Prompts · skills · instructions · retrieval parameters · **workflow topologies** (as data, ADR-0014) · **memory content** |

The meta-loop may **auto-commit within the mutable surface** and must open a **PR for
anything else** (ADR-0006). It may rewrite a prompt automatically precisely because it
structurally cannot rewrite the gate.

**`evolution/` is a forbidden importer of the TCB, by named contract.** An optimizer whose
mutable surface includes its evaluator has one dominant strategy — weaken the judge — and no
downstream statistics detect it, because the statistics are computed by the thing being
weakened.

> **The enforcement is the decision.** `tcb-isolation` and `TCB_PATHS` must name real paths.
> A contract that selects no files forbids nothing and passes green.
> `tests/unit/test_path_constant_drift.py` fails when one selects nothing.

---

## 7. Measurement

Full protocol: [`measurement.md`](./measurement.md). The binding rules:

- **Instruments are built and verified before the capability they measure.**
- **Every gate ships with a test proving it can fail.**
- **No capability number is published before the A/A variance floor is** (ADR-0002).
- Gates are tri-state: `True` / `False` / **`None`** — `None` means *unmeasured* and never
  silently passes.
- **Stubs raise.** They never return a plausible value. An exception swallowed into `[]`
  makes failure indistinguishable from "no results".
- Admission: **exact McNemar**, **Holm–Bonferroni** across a **pre-declared** gate family,
  α = 0.05 family-wise, and **N derived for ≥ 0.80 power** at the declared minimal effect —
  never a fixed N (ADR-0003 rev. 2). Primary outcome is **pass@1 on the first seeded pass**;
  extra passes estimate flakiness and never merge into it.
- Admission also requires **cost per resolved task non-inferior within a declared margin**
  (default ≤ +20%) — not raw cost held flat.
- No mechanism promotes to production without an ablation clearing the noise floor. **This
  includes workflow topologies**, whoever proposed them (ADR-0014).

---

## 8. Clients

The core is **headless** and emits one typed, append-only event stream. Every surface — TUI,
CLI, CI, a future GUI — is a consumer with no privileged access. The TUI is built first
deliberately: it keeps the engine honest, because the UI cannot do anything the protocol
does not expose.

The event catalog is **generated from `domain/events.py`** with a CI drift check. It is not
maintained by hand here.

---

## 9. Standing rules

- **Code wins.** Contracts live in `src/aether/ports/`; documents navigate.
- **No external code enters `src/aether/`.** Concepts and published theory transfer;
  implementation does not. **Predecessor code in this repository is not external**: it may be
  ported verbatim when its claimed properties verify line by line, with the provenance noted
  in the module docstring. `e0/statistics.py` is the case this clause exists for — 259 LOC
  that verify, ported under ADR-0003, and the only Phase 0 asset that earned it.
- **An experiment produces a number and a recommendation.** It becomes a decision only
  through an ADR with a reversal condition. Experiments live outside `src/aether/`, are
  exempt from these invariants, and are deletable.
- **An experiment that shows nothing is recorded as showing nothing.**
- **A number we did not measure on our own instruments never appears in a result, a claim,
  or a regression gate.** It may set a default, motivate an ablation, or bound a design —
  nothing more.
- `STATUS.md` makes no claim unsupported by a line-level code read.
