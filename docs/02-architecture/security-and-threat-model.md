# **Security & Threat Model**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

The previous documentation described security as command sanitization and a policy matrix. That is not a threat model, and it omitted the primary threat entirely. This module states what an autonomous coding agent is actually exposed to, and which mechanism stops each thing.

## **T1 — Indirect Prompt Injection (Primary Threat)**

An agent that reads repositories, issues, pull requests, code comments, dependencies, and web pages, while holding shell access and credentials, is the canonical injection target. A malicious README, issue body, test fixture, or transitive dependency can carry instructions the model reads as directives: exfiltrate `.env`, weaken a validation check, insert a backdoor, alter CI configuration. Autonomy multiplies the blast radius, because no human reviews intermediate steps.

**Mitigations** — defense does not rest on the model's judgment:

* All retrieved content is delimited and labelled as **data**. The system prompt establishes that content appearing in tool output carries no authority.
* Credentials never enter the sandbox; secrets are injected per-grant, scoped, short-lived.
* Egress is allowlisted **at the network namespace**, not by inspecting commands.
* Tool output is scanned and redacted for secret patterns before entering memory, logs, or context.
* Any action writing outside the worktree, or touching credentials, CI configuration, or harness policy, requires a human grant **at every autonomy level**.

## **T2 — Sandbox Escape via Shell**

**Command-string blocklisting is a usability guardrail, not a security control**, and must never be relied upon as one. Blocking `rm -rf` fails to `bash -c`, `python -c`, base64-encoded payloads, `$IFS` substitution, symlink indirection, and any interpreter already present in the image.

The correct framing is unambiguous: **if the agent has a shell, it has every capability the sandbox grants that shell.**

**Mitigations**: the container or gVisor boundary is the perimeter, required from the first slice rather than deferred; filesystem scope enforced by mount, not by path string inspection; no host credential material reachable from inside; network policy at the namespace.

## **T3 — Evaluation Capture**

A candidate branch has full filesystem access to its worktree, including `tests/`. Any scoring procedure using tests the candidate could have modified measures a number the candidate controls. The same applies at the outer loop, where an improver with write access to the evaluator can raise its score without improving anything.

**Mitigations**: tests injected pristine and read-only from the base commit; modification of test files is a **hard gate failure**, not a scored penalty; the trusted computing base is excluded from the improver's writable surface and enforced in CI.

## **T4 — Self-Modification Escaping Its Bounds**

The outer loop edits harness artifacts. Combined with shell access, the cheapest path to a higher score is to edit whatever produces the score.

**The Trusted Computing Base — never writable by the agent:**

* Policy engine and autonomy configuration
* Evaluator, gate definitions, benchmark task definitions
* The deployment gate itself, and this list
* Secret handling and the sandbox boundary

Enforced three ways: path allowlist in `MutationProposal.targets`, residence on a branch the agent cannot push, and CI rejection of any diff touching a TCB path. **Deployment requires human sign-off**; validated mutations are staged, never self-committed.

## **T5 — Destructive Replay**

Replaying a trajectory that ran `git push` or `rm` would perform it again. Every tool declares an `EffectClass`; replay re-executes only `PURE` calls and serves everything else from recorded observations. See [Microkernel & Bus](./microkernel-and-bus.md).

## **T6 — Resource Exhaustion**

Parallel agents against a frontier API exhaust rate limits and burn wall-clock in retries; unbounded sandboxes and LSP servers exhaust host memory. The `ResourceGovernor` bounds concurrency, spend, sandbox count, and server pool size globally. A budget that is documented but not enforced at a call site is not a budget.

## **Autonomy Levels and Human Gates**

| Level | Human involvement |
| :---- | :---- |
| Interactive | Approval per effectful action |
| Hybrid | Approval for risk-classified actions; plan review before multi-file change sets |
| Autonomous | Approval only for TCB-adjacent and out-of-worktree actions |
| Scheduled | As Autonomous, plus notification on completion or gate |

Gates are **durable, asynchronous approval requests**. Nobody watches a six-hour run, so a gate requiring someone present is a gate that will be disabled. Requests survive restarts, notify out of band, **deny by default on timeout**, and resume cleanly on approval.
