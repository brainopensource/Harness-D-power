---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Security, Sandboxing and Contamination Control

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Answers RFP [§4-D](../reviews/review_project_rewrite_v300.md).

---

## 0. Position

This is the one area where the recommendation is **port SAGIHA almost verbatim**. The perimeter is
the most complete and most carefully reasoned part of the predecessor, and the parts that are right
are right for non-obvious reasons that took a full audit cycle to establish. Rewriting it would be
re-earning knowledge we already paid for.

Three properties carry over unchanged, and each is stated as a rule because each is routinely
violated by implementations that believe they have security:

1. **The sandbox is the perimeter.** Command blocklists are UX, not security (ADR-0006).
2. **Grants are verified at the point of effect**, not merely at issuance.
3. **External content is data, never instruction** — and provenance survives storage round-trips.

---

## 1. Capability authorization (CAR)

### 1.1 One choke point

Every effect in the system passes through `kernel/dispatch.py`. The sequence is fixed:

```
policy.authorize(call, ctx) → Decision(grant_id)
      ↓
policy.verify_grant(grant_id)        ← unconditional, at the point of effect
      ↓
governor.acquire(kind, run_id)       ← lease
      ↓
registry.dispatch(call)              ← the only place a tool actually runs
      ↓
governor.release(lease_id)           ← in a finally
```

**The second step is the one that matters.** Authorizing at issuance and executing later is the
common design, and it is wrong: between issuance and effect, arguments can be mutated, a replayed
transcript can reintroduce a stale grant, or a resumed run can carry an authorization minted under
different conditions. Verifying immediately before the effect closes all three.

Enforcement is an architecture test asserting there is **no bypass path** to the tool handlers —
not a code-review convention.

### 1.2 No `Grant` crosses a port

`PolicyEngine.authorize()` returns a `grant_id` — a string — and nothing else. No `Grant` object
appears in any port signature, and `tests/contracts/test_port_shape.py` asserts this generically
across every port by reflection.

Two consequences follow, and both are load-bearing:

- A caller cannot forge or mutate a grant, because it never holds one.
- A grant cannot be serialized into a freeze file. `FrozenRunState` therefore contains no
  authorization, and a thawed run **re-mints** its grants under current policy rather than restoring
  authority captured hours ago. This is checked by
  `test_port_shape.py::test_no_grant_in_frozen_run_state`.

### 1.3 Effect classes, narrowed per call

Tools carry a static `EffectClass` (`PURE` / `MUTATING` / `DESTRUCTIVE`), and `run_command` is
re-classified **per invocation** by `kernel/policy/effects.py::classify_command`. `ls` and
`rm -rf /` cannot share one authorization decision merely because both arrive through the same tool.

Codex reaches the same conclusion independently — its `execpolicy` is a crate distinct from its
execution crates. Two systems arriving at the same seam is reasonable evidence the seam is real.

### 1.4 The three-valued permission model

Claude Code's `settings.json` schema contributes the shape worth copying: **`allow` / `ask` /
`deny`**, matched per tool and per argument pattern, deny-first.

`ask` is the state that makes an autonomous agent usable rather than merely safe. A binary
allow/deny forces every uncertain case to a policy author who is not present; `ask` routes it to the
human who is. `PolicyEngine` returns a `Decision` that can carry it, and the
[UI layer](./rewrite_v300_uiux_tui.md) renders it as a first-class interaction.

### 1.5 Hooks as configuration

Pre/post-tool interception belongs in **config**, not in a plugin API. The user extends behavior
without extending the type system, and — critically — a hook cannot widen authority: it observes and
may veto, never grant. Extensions register via entry points, resolved once at composition, then
frozen (ADR-0013). No runtime discovery, no filesystem scanning, no monkey-patching.

---

## 2. Execution isolation

Two layers with different jobs. Conflating them is the usual mistake.

| Layer | Mechanism | Protects against |
| :--- | :--- | :--- |
| **Concurrency isolation** | Git worktrees, one per candidate, pooled and reused | Candidates corrupting each other's files. **Not a security boundary** |
| **Security perimeter** | Rootless Podman container + egress allowlist proxy | Agent-authored code affecting the host or reaching the network |

SAGIHA's `adapters/sandbox/container.py` (372 LOC) and `egress.py` (132 LOC) port directly. Codex's
decomposition — `bwrap`, `linux-sandbox`, `sandboxing`, `windows-sandbox-rs` behind one abstraction —
is the right shape for cross-platform support later; the Podman implementation becomes one backend of
that abstraction rather than the abstraction itself.

**Why no command blocklist (ADR-0006).** A blocklist enumerates known-bad commands, and there are
unboundedly many spellings of any of them — shell expansion, base64, an interpreter, a fetched
script. The perimeter is the container. Blocklists remain useful for *UX* — catching an obvious
mistake early with a clear message — and are never relied upon for containment. Stating this
explicitly matters because a blocklist that looks like security invites the security to be removed.

**Egress is part of the perimeter.** Filesystem isolation without network isolation leaves
exfiltration open, and an allowlist proxy is what makes "this run touched only these hosts" an
auditable claim rather than an assumption.

### 2.1 Three escape vectors the perimeter must be designed against

Documented against shipped native sandboxes and worth designing for rather than discovering. Each has
the same shape: a configuration that *looks* restrictive and is not.

| Vector | Mechanism | Rule |
| :--- | :--- | :--- |
| **Domain fronting** | An allowlisted CDN apex hosts arbitrary user content. Allow `*.cloudflare.com` and the agent can fetch an attacker-uploaded payload from a Workers subdomain — the allowlist was satisfied | **Never allowlist a CDN apex or broad wildcard.** Allowlist specific hosts. Accept that perfect blocking is impossible without TLS inspection, and treat egress as *auditable*, not *airtight* |
| **Unix socket privilege escalation** | A socket is a capability. `/var/run/docker.sock` is full host access; `containerd.sock`, a supervisor socket, or a systemd user bus are process control. A pattern like `/tmp/*.sock` grants whatever happens to be there | **Sockets deny-by-default; allowlist individually after audit**, never by glob. A socket that reaches a process manager or container daemon is a perimeter breach, not a convenience |
| **Filesystem escalation via write paths** | Write access to a `$PATH` directory or a shell rc file is deferred code execution outside the sandbox — drop a binary named `sudo` in `/usr/local/bin`, wait for the human | **Write scope is the worktree.** `$PATH` directories, shell rc files, and anything sourced at login are outside the writable set regardless of how convenient an exception looks |

The generalization: **an allowlist entry is a capability grant, and its blast radius is whatever sits
behind it — not what the person writing it had in mind.** That is the same failure mode as
[§1.3](#13-effect-classes-narrowed-per-call)'s static effect class, one layer down, and it is why the
config schema treats broad wildcards in egress, socket, and write-path lists as a validation error
rather than a style issue.

**Layered sandboxes are weaker than they look.** Nesting a sandbox inside another does not compose
their guarantees on Linux; the inner boundary can be the weaker of the two. AETHER's perimeter is one
boundary that is actually enforced, not a stack of partial ones — which is also why the worktree layer
is documented as *isolation, not security* above.

---

## 3. TaintGate — untrusted content

### 3.1 The threat

The agent reads content it did not author: repository files, READMEs, issue text, dependency
documentation, web results, MCP tool output. Any of it can contain text shaped like an instruction.
This is OWASP LLM01, and in a coding agent it is not hypothetical — a comment in a vendored
dependency is a fully general injection vector.

### 3.2 The mechanism

**Deterministic rules, no LLM judge.** A classifier that can be talked out of its verdict is not a
control.

| Rule | Behavior |
| :--- | :--- |
| Content from an external source is marked `trusted=False` at ingestion | Provenance is stamped **at the registry**, never by the tool handler — a handler cannot mark its own output trusted |
| An EDIT within a taint window of external-provenance context | `tainted=True`; `request_approval` becomes mandatory |
| A diff that adds a network endpoint, a new dependency, a lint or type suppression, or touches CI config | Gate failure unless the `TaskSpec` explicitly authorizes that category |
| Provenance survives storage round-trips | Trust is a property of the record, not of the in-memory object |
| Fail-closed | Unknown provenance is untrusted |

SAGIHA's tool table already encodes the distinction: `read_file`, `list_dir` and `grep` return
`trusted_output=False` — repository content is data. `apply_edit` and `write_file` return
`trusted_output=True` because their output is our own confirmation, not repository content. Gate
feedback is trusted for the same reason: it originates from our evaluator.

Hermes arrives at the same conclusion by a different route (`agent/tool_result_classification.py`,
`tool_guardrails.py`) — independent convergence on "tool output needs a trust class, not just a
value."

### 3.3 Two provider-level cases

**Tool calls emitted as prose.** With thinking disabled, current frontier models occasionally write a
tool call into visible text rather than emitting a structured `tool_use` block. The turn completes
normally, the call never runs, and no error is raised. SAGIHA has a regex extractor for exactly this
(`adapters/model/openai.py::_parse_embedded_tool_block`), added for weak local models.

**AETHER does not parse tool calls out of prose.** The structured tool-call channel is the only
channel that reaches dispatch. A parser that promotes text to an executable call is a path around the
choke point, and the model's own output is not the only text that could ever reach it. The correct
mitigations are upstream: keep thinking enabled (lowering `effort` is the cost lever, not disabling
thinking), and treat a turn that produced neither a structured call nor a final answer as a **failed
step** — visible, counted, and repaired — rather than silently rescued.

**Refusals are a normal outcome, not an error.** A frontier model may decline a request and return
HTTP 200 with `stop_reason: "refusal"`. Code that reads `content[0]` unconditionally breaks. Since
AETHER is a *security-adjacent* tool that will legitimately touch cryptography, parsers, auth code and
sandbox logic, benign false positives are expected. The `ModelProvider` port surfaces refusal as a
typed outcome with its category, and the run loop treats it as a disposition — not a crash, and not
a silently truncated success.

---

### 3.4 The agent can attack the harness's own supervision

A threat class none of §1–§3 covers, and one AETHER would otherwise ship into: **the agent's
legitimate capabilities, aimed at the harness's own lifecycle.**

The concrete case, documented in `cron/lifecycle_guard.py` in `src/hermes_agent`:

1. The agent schedules a cron job whose command restarts the gateway process
   (`hermes gateway restart`, `launchctl kickstart`, `systemctl restart …`).
2. The cron fires. The gateway dies.
3. The supervisor — launchd `KeepAlive`, systemd `Restart=` — revives it, correctly.
4. Auto-resume picks up the session that scheduled the job.
5. The resumed turn re-runs the same logic.

**Result: a SIGTERM-respawn loop every ~10 seconds until a human breaks it.** No sandbox was escaped,
no policy was violated, no untrusted content was involved. Scheduling and durable resume are both
features working exactly as designed, and their composition is a self-inflicted denial of service.

Two things make this generalize rather than being one bug:

- **It is a composition failure.** Each capability is individually safe and individually authorized.
  The perimeter model in §2 reasons about *what the agent may touch*; it has nothing to say about
  *what two permitted actions do to each other*. AETHER has all three ingredients on the roadmap —
  scheduling, hibernation and durable resume, and supervised restart — so it inherits the failure
  unless it inherits the guard.
- **The guard has to read past the prompt.** Hermes' check scans the job's prompt *and any shell
  scripts it references*, because "run `./deploy.sh`" hides the restart one level down. A guard that
  inspects only the literal command is trivially bypassed without any adversarial intent.

**AETHER's rule.** Harness lifecycle primitives — process restart, supervisor control, scheduler
mutation, and the freeze/resume machinery itself — are **not reachable from agent-authored scheduled
work**, and the check is enforced at job *creation* so it fires on every path rather than at each call
site. More generally, and stated as a design obligation rather than one patch:

> Any capability that can **re-enter the agent loop** — a scheduler, a webhook, a resume trigger, a
> self-directed task queue — must be analyzed for loops with every capability that can **restart or
> resume the harness**. This is a required review item when scheduling
> ([autonomy §8](./rewrite_v300_autonomia_agi.md)) lands, not a note.

The budget governor is a mitigation and not a solution: a respawn loop that restarts the *process*
starts a fresh budget each time.

---

## 4. The Trusted Computing Base

| In the TCB | Why |
| :--- | :--- |
| `kernel/policy/` | Authorization decisions |
| `kernel/dispatch.py` | The choke point |
| The evaluator and gate definitions | What counts as success |
| Benchmark definitions | What we measure against |
| `.importlinter`, CI workflows | The enforcement of everything above |

**The TCB is unmodifiable by the agent and by the meta-loop.** Invariant I8. Without it, the
self-improvement loop's most efficient available strategy is to weaken the gate that judges it — and
"the agent edited its own grading criteria" is a failure mode that invalidates every number the
project has ever produced, retroactively.

Two enforcement layers, because one is a convention and the other is mechanical:

- `.importlinter` `tcb-isolation`: TCB modules may not import from agency, aoi, or adapters. The TCB
  cannot reach *up* into the things it judges.
- CI `tcb-check`: rejects PRs from the agent identity that touch TCB paths.

**Generator ≠ Evaluator** (invariant I7). The agent that writes code cannot modify the tests that
grade it. Tests are injected read-only from the base commit; `require_tests_unmodified` is a hard
gate. Hard gates admit; learned scorers may rank and may never admit or override a gate failure —
enforced at the type level by separating `rank()` from `admit()`.

---

## 5. The isolation defect that must not recur

`docs/rationale/benchmarks/s4-harvest-findings.md`, defect **D3**: the editable install's `.pth` file
placed the live `src/` on `sys.path` inside every isolated worktree. Every candidate's tests imported
the same working tree, so **candidate diffs were invisible to the gates scoring them**.

This is a security-shaped bug that lived in the measurement layer: an isolation mechanism that
silently did not isolate. It is worse than no isolation, because no isolation is obvious and this
produced numbers.

**Structural fix, not a checklist item.** The evaluation environment is constructed to make the
failure impossible rather than merely detected:

- No editable install inside an evaluation container.
- The container's Python environment is built from the task's own dependency specification.
- A **canary test** asserts that a deliberately broken candidate *fails* — proving the gate can see
  the candidate at all. This is the security-layer instance of the standing rule that
  [every gate ships with a test proving it can fail](./rewrite_v300_measurement_strategy.md).

Companion defects, both fixed at the same layer: pytest-uncollectable files in `failing_test_cmd`
(D1), and exit-127 "command not found" scored as a test failure rather than an instrument error (D2).

---

## 6. Long-horizon and multi-agent security

**Hibernation re-mints, never restores.** Grants are not in `FrozenRunState` (§1.2), so a run that
resumes after a reboot is re-authorized under current policy. A frozen run is data, not a suspended
capability.

**Sub-agents get scoped registries.** A delegated agent receives a narrowed tool registry and its own
budget. Delegation must not widen authority — it is the obvious escalation path and the one a
capability model exists to close.

**MCP tools are untrusted by default.** External tool servers are third-party code reached over the
network. Their output is `trusted=False`; their invocation is grant-gated like any other effect.

**Credentials never enter the sandbox.** Where a credential is needed, it is injected outside the
perimeter — at a proxy, on the way out — so that code running inside, including code the agent wrote,
cannot read it even under successful prompt injection. This is the same principle as §3.2's
fail-closed provenance, applied to secrets.

---

## 7. Summary

| Decision | Choice | Enforcement |
| :--- | :--- | :--- |
| Authorization | Single choke point; `verify_grant` at the point of effect | Architecture test: no bypass path |
| Grants | `grant_id` only; never cross a port; never frozen | Reflection contract over all ports |
| Effect classes | Static per tool, narrowed per `run_command` invocation | Unit tests over `classify_command` |
| Permissions | `allow` / `ask` / `deny`, deny-first | Policy conformance suite |
| Hooks | Config-level; may veto, never grant | Composition test |
| Perimeter | Rootless Podman + egress allowlist. **No command blocklist as security** | Perimeter canary test (podman-marked) |
| Concurrency | Git worktrees — isolation, not security | — |
| TaintGate | Deterministic rules, no LLM judge, fail-closed | Taint canary test |
| Tool-call channel | Structured blocks only; **no prose parsing** | Registry contract |
| Refusals | Typed outcome with category; a disposition, not a crash | Provider conformance test |
| TCB | Immutable by agent and meta-loop | import-linter + CI `tcb-check` |
| Generator ≠ Evaluator | `require_tests_unmodified`; gates admit, scorers rank | Hard gate + type-level separation |
| Evaluation isolation | No editable install; canary proves the gate sees the candidate | Canary test |
| Hibernation | Grants re-minted | `test_no_grant_in_frozen_run_state` |
| Harness lifecycle | Unreachable from agent-scheduled work; checked at job creation, scans referenced scripts | Lifecycle-guard test |
| Capability composition | Re-entry capabilities reviewed against restart/resume capabilities | Required review item |
| Sub-agents | Scoped registry, own budget; cannot widen authority. Delegated children scrub inherited identity | Policy test |
| Credentials | Injected outside the perimeter | — |
