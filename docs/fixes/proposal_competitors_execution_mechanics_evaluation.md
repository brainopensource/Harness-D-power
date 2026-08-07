---
status: rationale
updated: 2026-08-07
---

# Evaluation: Four Kimi CLI Execution Mechanics, Against AETHER's Invariants

**Verdict up front.** Two of the four should be adopted, one should be adopted with its
central claim **inverted**, and one should be refused at this milestone. The refusal is not
about difficulty — it is that the proposal as written violates three invariants at once.

| # | Mechanic | Verdict | Why |
| :--- | :--- | :--- | :--- |
| **2** | Stdin closing + non-interactive env | ✅ **Adopt now** — Sprint 4 | Cheapest item here and the only one with a *measurement* argument. Three defects in eight lines of `builtin.py` |
| **3** | Line-buffered output telemetry | ✅ **Adopt, display-only** — post-M1b | Correct idea, wrong channel. Must never reach the durable trajectory log |
| **4** | Interactive approval interceptor | ⚠️ **Adopt the mechanism, invert the provenance claim** | Already funded as `TASK-030a`. The proposed label rule is a capability-laundering vector |
| **1** | Async background task execution | ❌ **Refuse at this milestone** | Breaks the governor lease triple, `spec.md` §8, and replay determinism. Revisit at M3 |

---

## 0. Corrections to the report's factual claims

Both trees were read. Three claims need adjusting before the recommendations rest on them.

**C1 — `get_noninteractive_env` sets one variable, not four.** The report attributes
`PAGER=cat`, `DEBIAN_FRONTEND=noninteractive` and `CI=1` to Kimi CLI.
`src/kimi_cli/src/kimi_cli/utils/subprocess_env.py:55-72` sets exactly one thing —
`GIT_TERMINAL_PROMPT=0` — on top of a PyInstaller `LD_LIBRARY_PATH` cleanup that is irrelevant
to us (we do not ship a frozen binary). The other three are the report author's additions. They
are *good* additions, and §2 keeps them — but they are ours to justify, not Kimi's to credit.

**C2 — `Decision.ASK_OPERATOR` does not exist.** `ports/policy_engine.py:20-24` declares
`GRANT | REJECT | ASK_RULE_MATCH | ASK_FAIL_CLOSED`. The two `ASK_*` values are the escalation
taxonomy from [ADR-0008](../decisions/0008-shell-ast-classifies.md)/[ADR-0015](../decisions/0015-taintgate-provenance-model.md),
and `DefaultPolicyEngine` already returns `ASK_FAIL_CLOSED` for the I11 case. There is no gap to
fill with a new enum value; there is a gap in what happens *after* one is returned.

**C3 — the container path is already hardened; the uncontained paths are not.**
`adapters/sandbox/podman.py:92-110` builds an explicit `--env` allowlist (`TMPDIR`,
`PYTHONDONTWRITEBYTECODE`) and passes no `-i`, so the container inherits neither the host
environment nor a stdin. The exposure is entirely in the two host-side paths, which is where §2
should aim.

---

## 1. Background task execution — refuse at this milestone

**What Kimi does is real.** `config.py:111-118` carries a `BackgroundConfig` with a keep-alive
flag and a 900-second ceiling; `app.py:401-509` reconciles and kills background tasks on exit.
It is a coherent design for an *interactive assistant*, where the human is the scheduler.

**Three invariants say no for a benchmark harness.**

1. **The governor lease triple.** `spec.md` §5 requires `authorize → verify → acquire lease →
   dispatch → release`, and `kernel/dispatch.py:91-104` refuses any effect without a live lease,
   committing `actuals` before release. A background process **outlives its lease by
   construction** — its actuals arrive after `release()`. That is after-the-fact accounting, the
   precise thing `TASK-034` exists to make structurally unrepresentable, and
   [`backlog.md`](../agile/backlog.md) records it as *"H2 in the predecessor's refactor plan."*
2. **`spec.md` §8: events never schedule nodes.** `kernel/bus.py`'s module docstring states it
   as an enforced property — *"the executor drives its own order from the validated topology,
   never from what lands on this bus."* The report's phrasing — *"the DAG executor receives this
   notification"* — is that rule inverted. A sensor that must cause work enqueues a task through
   the engine API; it does not wake the executor.
3. **Replay determinism.** `TASK-026` requires replay from the trajectory store to be
   **byte-for-byte deterministic**, and `TASK-006` requires cassettes to be too. A task that
   completes at a wall-clock-dependent point interleaves differently on every run. The event
   *order* in the durable log stops being a function of the topology.

There is also a plain measurement objection. Backgrounding a test suite so the model can keep
working means **the model acts on a stale worktree while the judge reads a moving one**. On an
interactive assistant that is a UX trade; on a harness whose entire output is a resolve rate, it
is an instrument defect of the B3 family — the gate scoring a state the candidate did not
produce.

**When to revisit: M3.** `TASK-035` designs concurrency properly — N parallel candidates carve N
child leases from one parent reservation, every fan-out site has a declared join, and unjoined
fan-out is *not expressible in a valid topology*. Background execution belongs inside that model,
as a bounded, joined, lease-carrying construct, or not at all. Adding it before M3 means building
the concurrency semantics twice and getting the lease tree wrong the first time.

---

## 2. Stdin closing and non-interactive environment — adopt now

**This is the strongest item in the report, and the case for it is stronger than the report
makes.** Three defects live in eight lines of `adapters/tools/builtin.py:110-120`:

```python
proc = await asyncio.create_subprocess_shell(
    str(args["command"]),
    cwd=path,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
)
stdout, _ = await proc.communicate()
```

- **Stdin is inherited**, not closed. `git push` prompting for credentials, `apt` asking `[y/n]`,
  or a paged `git log` will block on a terminal the harness is not driving.
- **There is no timeout.** `generate.py:189-193` passes `BudgetDims(wall_clock_ms=30000)` as a
  *cost estimate*; the governor reserves against it and **nothing enforces it as a deadline**.
  The 30 seconds is decorative — the same defect class as the node budget that is reserved and
  released without a commit.
- **The environment is inherited whole**, including any `OPENROUTER_API_KEY` or `OPENAI_API_KEY`
  in the shell that launched the run. Model-written code executes uncontained on the host with
  the operator's credentials in `os.environ`.

The uncontained evaluator path has the same environment exposure by a different route:
`measurement/evaluator.py:56` defines `_EVAL_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}`
and passes it to `_evaluate_uncontained`. That path is documented as smoke-only and never valid
for a published number, which is correct — but "never valid for a number" is not the same as
"safe to run", and it is the default when `sandbox_runtime` is `None`.

### The argument that actually settles it: this is an instrument fix

A hung tool call is not a neutral slowdown. It runs to the evaluation timeout, returns
`GateStatus.NONE`, and `NONE` is **excluded from the resolve-rate denominator**
([`measurement.md` §2, B4](../measurement.md#2-instrument-blockers)). So an interactive prompt
nobody answers silently shrinks N, and it shrinks it **non-randomly** — tasks whose repositories
prompt are systematically dropped. That is a selection effect entering the sample through a
subprocess default, and it would be invisible in the aggregate. Deterministic non-interactivity
is a precondition for the floor meaning what it says.

### Proposed: `TASK-062`, and one helper, not three copies

```python
# domain/... no. This is I/O policy, so: src/aether/adapters/subprocess_env.py
NON_INTERACTIVE = {
    "GIT_TERMINAL_PROMPT": "0",      # git fails instead of prompting        (Kimi's one var)
    "GIT_ASKPASS": "",               # and does not fall back to an askpass helper
    "DEBIAN_FRONTEND": "noninteractive",
    "PAGER": "cat",
    "MANPAGER": "cat",               # pydoc/git read MANPAGER before PAGER
    "PYTHONUNBUFFERED": "1",         # required by §3's streaming, harmless now
    "CI": "1",
}
```

Applied at all three host-side spawn sites (`adapters/tools/builtin.py`,
`measurement/evaluator.py`, `adapters/workspace/git_cli.py`) with `stdin=DEVNULL` and a real
`asyncio.wait_for` deadline derived from the lease.

**Two constraints that are not optional:**

- **`CI=1` changes test behaviour.** Some suites skip, some enable strict mode, some change
  output format. Setting it changes what the judge measures, so it enters through the
  **container's** `--env` allowlist as a pinned, declared part of the evaluation environment —
  never inherited ambiently. A change to it is a new manifest hash, like any other instrument
  change.
- **The environment becomes an allowlist, not a copy.** `_EVAL_ENV = {**os.environ, ...}` is
  also a reproducibility hole: `measurement.md` §6 requires a run to name its instrument, and an
  evaluation whose behaviour depends on the launching shell cannot. Replace with an explicit
  small dict. This is the same argument as *image by digest, never by tag*.

---

## 3. Line-buffered telemetry — adopt, but not on the durable channel

The mechanic is right and the report's framing of where it lands is wrong in one specific way.

`kernel/bus.py` has exactly two drop policies, and the split is load-bearing:
`"never"` (unbounded queue — the trajectory store and the measurement harvester, which must not
lose an event) and `"drop_oldest"` (bounded at 1000 — display consumers, *"losing a rendering
frame is acceptable, losing a step is not"*).

Per-line log deltas on the `"never"` channel would:

- write thousands of SQLite rows per evaluation into the append-only log, which is also the
  **replay source**;
- make replay ordering depend on OS pipe scheduling rather than on the topology, weakening
  `TASK-026`'s byte-determinism guarantee;
- require a new typed event in `domain/events.py`, which is subject to the catalog drift check —
  fine, but it means log lines become part of the published event contract forever.

**Correct shape:** a `LogLineEmitted` event delivered **only to `drop_oldest` subscribers**, with
the durable log continuing to store the tail-biased summary it already stores via
`tail_biased()`. That preserves the existing property that *the prompt sees the same truncation
the gate recorded*, while the TUI/GUI gets its live `12/45 tests passed…` counter.

**Sequencing:** after `TASK-058` (`RunConfig`) and the M1b event work, because there is no client
that renders it today. It is a genuine UX win with no correctness payoff, so it does not
compete with Sprint 4.

---

## 4. Approval interceptor — adopt the mechanism, invert the provenance rule

**The mechanism is already funded.** `TASK-030a` builds the
`Reject | AskRuleMatch | AskFailClosed` taxonomy with auto-denial bounded at 3 consecutive / 20
total; `DefaultPolicyEngine` already returns `ASK_FAIL_CLOSED` for the I11 case. What is missing
is the round trip: `Dispatcher.dispatch()` treats any non-`GRANT` decision as a terminal denial
(`dispatch.py:85-87`), so an `ASK_*` today is indistinguishable from a `REJECT`. Wiring that to a
client prompt over the event bus is the right design and it needs no new enum value.

### The part that must not be adopted as written

> *"Upon operator approval, the effect executes and its outputs acquire `Provenance.OPERATOR`
> labels."*

**This is capability laundering, and it is the exact attack I11 exists to prevent.**

`BuiltinToolRegistry.execute` labels every `ToolResult` span `Provenance.UNTRUSTED_EXTERNAL`
**at construction** (`builtin.py:89-96`) — [ADR-0015](../decisions/0015-taintgate-provenance-model.md)
requires that timing precisely so a caller never has to remember to taint a result afterwards.
`DefaultPolicyEngine`'s predicate then fails closed when a capability-widening request is
justified by any span in `UNTRUSTED`.

Relabelling approved output as `OPERATOR` removes it from that set. So: an operator approves
`curl https://example.com/x | head` once — a reasonable-looking read. The fetched bytes come back
labelled `OPERATOR`. Those bytes now sit in the context as trusted, operator-authored text, and
can justify the *next* capability-widening request without tripping the gate. One approval
converts arbitrary external content into instruction authority. That is `vision.md` §2's named
failure mode — *"an authorization granted early and used later under different conditions"* — with
a label change doing the work.

**The correct rule, and it is a one-line distinction:**

> **Approval authorizes the *effect*. It does not relabel the *output*.**
>
> An operator decision produces a `PolicyDecision` — a fact about the request. The result's spans
> keep the provenance their source gives them. Tool output is `UNTRUSTED_EXTERNAL` whether or not
> a human clicked yes, because the human approved *running the command*, not *the bytes it
> returned* — which they had not seen.

The audit trail belongs on the decision, not on the data: record the approving operator, the
rule id, and the timestamp in the `PolicyDecision` and the trajectory. That gives the same
accountability with none of the laundering.

**One more constraint from the existing design.** `TASK-030a`'s auto-denial bound is *3
consecutive / 20 total, after which the run halts*. An interactive approval path must not become
a way around that bound in unattended benchmark runs — a harness that stops to ask a human
mid-benchmark has an unbounded wall-clock and a human in the measurement loop. **Approval is a
client-mode feature; benchmark runs fail closed**, and that should be a field in `RunConfig`
(`TASK-058`) rather than an ambient default.

---

## 5. What this changes in the plan

| Change | Where | When |
| :--- | :--- | :--- |
| **`TASK-062`** — non-interactive subprocess hardening: `stdin=DEVNULL`, env allowlist, lease-derived timeouts at all three host spawn sites | `adapters/subprocess_env.py` (new), `tools/builtin.py`, `measurement/evaluator.py`, `workspace/git_cli.py` | **Sprint 4** — it is an instrument fix and belongs beside the other instrument fixes |
| **`TASK-063`** — `LogLineEmitted` on the `drop_oldest` channel only; durable log keeps the tail-biased summary | `domain/events.py`, `adapters/sandbox/podman.py`, `tools/builtin.py` | Post-M1b, with the first client that renders it |
| **`TASK-030a` amendment** — the `ASK_*` round trip to a client, with the *approval authorizes the effect, not the output* rule written into the ADR | `kernel/dispatch.py`, ADR-0008/ADR-0015 | Unchanged milestone (M2/M3, CI-gated) |
| **Background execution** — recorded as **deferred to M3**, inside `TASK-035`'s lease-tree and declared-join model, with a note that it must carry a lease and a join or it is not expressible | [`backlog.md`](../agile/backlog.md) `TASK-035` | M3 |

## 6. What this evaluation does not claim

- **No performance or capability claim** is made for any of the four. `TASK-062` is justified by
  determinism and credential exposure, not by speed.
- **No security claim** attaches to the environment allowlist. The sandbox is the perimeter
  ([ADR-0008](../decisions/0008-shell-ast-classifies.md)); an env allowlist on an *uncontained*
  host process reduces exposure, it does not create isolation. The real fix for
  `BuiltinToolRegistry` remains `TASK-018`'s second half — its own container, its own lease class.
- **The comparison is not a benchmark.** Kimi CLI is read here as a source of implementation
  ideas. Nothing about its resolve rate, cost or speed is claimed, and under
  [`spec.md` §9](../spec.md#9-standing-rules) nothing could be without running it through our own
  evaluator (`TASK-015`).
