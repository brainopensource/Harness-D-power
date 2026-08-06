---
status: historical
updated: 2026-07-29
---
# **Security & Threat Model**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Threat Matrix & Mitigations**

### T1 — Indirect Prompt Injection
* **Data Delimiting**: All retrieved repository/web content is wrapped in `<untrusted-data>` envelopes in the system prompt.
* **Provenance Tracking**: Memory records carry `Provenance`. `EXTERNAL` data recalled into context is re-wrapped in `<untrusted-data>` to prevent prompt laundering.
* **Egress & Secret Redaction**: Scoped credentials injected per grant; egress allowlisted at the network namespace; tool output redacted for secret patterns prior to persistence.

### T2 — Sandbox Escape via Shell
* **Perimeter Boundary**: Command string blocklists are UX guards, not security boundaries. Security relies strictly on container isolation ([ADR-0006](../08-decisions/0006-sandbox-is-the-perimeter.md), [Phased Migration Matrix](../07-roadmap/phased-migration-matrix.md)).
* **Dev-Mode Restrictions**: Unsandboxed subprocess execution is allowed **only** under `interactive` autonomy; invalid configurations fail startup validation ([`src/sagiha/domain/config.py`](../../../src/sagiha/domain/config.py)).
* **Container Runtime**: Rootless Podman with rootless network namespace firewalling and explicit HTTP/HTTPS proxying ([ADR-0016](../08-decisions/0016-container-runtime-podman.md)).

### T3 — Evaluation Capture
* Test suites land pristine and read-only from the base commit. Modifying test files produces an immediate **hard gate failure**.

### T4 — Self-Modification & Trusted Computing Base (TCB)
The TCB is immutable to the agent and guarded by CI and `MutationProposal.targets` allowlists:
1. Policy engine and autonomy configuration.
2. Evaluator, gate definitions, and benchmark tasks.
3. Secret handling, sandbox boundary, and deployment gates.

### T5 — Destructive Replay
Replay execution relies on tool `EffectClass` declarations: `PURE` actions re-execute; `DESTRUCTIVE` actions return cached observations ([Microkernel & Bus](./microkernel-and-bus.md)).

### T6 — Resource Exhaustion
`ResourceGovernor` bounds concurrency, spend, sandboxes, and LSP servers.

### T7 — Tainted-Context Mutation (TaintGate v1)
Prevents untrusted data read within a run from driving unapproved file edits:

| Component | Rule |
| :--- | :--- |
| **Provenance at Source** | `ToolResult.trusted: bool` set by `dispatch`. Workspace tools (`read_file`, `grep`, `run_command`) yield `False`; edits yield `True`. |
| **Monotonic Taint** | Untrusted results mark `run_id` as tainted in `DefaultPolicyEngine._tainted_runs`. Taint persists until run termination. |
| **Enforcement Gate** | `PolicyEngine.authorize()` denies `MUTATION_TOOLS` (`apply_edit`, `write_file`) under taint with `requires_human=True` across **all** autonomy levels. |
| **Prompt Boundary** | Untrusted content is wrapped in `<untrusted-data>` envelopes when assembled into prompts; summaries retain taint through compaction (see [Prompt Architecture](./prompt-architecture.md)). |

*Note: `run_command` remains unblocked by default taint to preserve gate execution (`git diff`), relying on container network namespace perimeter isolation.*

## **Autonomy Levels & Approval Gates**

| Autonomy Level | Human Approval Requirement |
| :---- | :---- |
| **Interactive** | Approval required per effectful action. |
| **Hybrid** | Approval for risk-classified actions and multi-file plans. |
| **Autonomous** | Approval required strictly for TCB-adjacent or out-of-worktree actions. |
| **Scheduled** | Autonomous operation with completion/gate notifications. |

Approval requests are durable, asynchronous, and **deny by default** upon timeout.
