---
status: normative
updated: 2026-07-29
---

# **Tool Catalog**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

The suite specified the tool *mechanism* — open namespace, `EffectClass`, `Grant`-gated dispatch — but never which tools the agent actually has. That is the difference between a design and something buildable: the tool surface **is** the agent's capability envelope, and it is prompt real estate paid for on every single call.

This module is the normative catalog. Everything here ships in the core binary; MCP servers extend it at runtime.

## **Tool Budget Discipline**

**The core catalog is capped at 20 tools.** Selection accuracy degrades as the tool list grows — the model spends attention discriminating between near-duplicates instead of solving the task — and every schema is re-sent on every request until the cache warms.

Consequences, applied throughout the table below:

* Prefer one tool with a mode parameter over three near-identical tools.
* A capability used in under ~5% of tasks belongs behind an MCP server, not in core.
* Tool descriptions are written to the model, not to a developer: state *when to reach for this*, not how it is implemented.

## **The Catalog**

Legend — **Effect**: `P` pure, `I` idempotent, `D` destructive (see [Domain Schemas](./domain-schemas.md)). **Grant**: required capability token. **Trust**: whether output is treated as authoritative or as untrusted data.

### Navigation & Reading

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `read_file` | `(path, offset?, limit?) -> ContentBlock[]` | P | read-scope | untrusted |
| `list_dir` | `(path, depth=1) -> DirEntry[]` | P | read-scope | untrusted |
| `glob` | `(pattern, path?) -> str[]` | P | read-scope | untrusted |
| `grep` | `(pattern, path?, glob?, mode="content") -> Match[]` | P | read-scope | untrusted |

`read_file` **always** paginates: default 2000 lines, and a truncated read sets `truncated: true` with `full_output_uri`. Unbounded reads are the most common cause of context exhaustion in coding agents.

`grep` takes `mode` (`content` \| `files` \| `count`) rather than shipping three tools — a direct application of the budget rule.

### Code Intelligence

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `find_symbols` | `(query, limit=20) -> Symbol[]` | P | read-scope | trusted |
| `get_skeleton` | `(path) -> str` | P | read-scope | trusted |
| `find_references` | `(path, line, col) -> Symbol[]` | P | read-scope | trusted |
| `get_diagnostics` | `(path?) -> DiagnosticItem[]` | P | read-scope | trusted |
| `impacted_by` | `(path, hops=2) -> str[]` | P | read-scope | trusted |

These are **trusted** because they are derived deterministically by the harness from Tree-sitter, the language server, and git — not authored by a third party. They are also the tools that most differentiate this harness from file-only agents, so their descriptions explicitly steer the model toward them ahead of `grep` for symbol questions.

### Mutation

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `edit_file` | `(request: EditRequest) -> EditResult` | D | write-scope | trusted |
| `write_file` | `(path, content) -> EditResult` | D | write-scope | trusted |

`edit_file` is the **primary** mutation path and takes an `EditRequest` (containing `path` and `edits: tuple[Edit, ...]`). Edit uses search/replace anchors with `expected_occurrences` for disambiguation; unified-diff is reserved for a separate `apply_patch` method if ever needed. `write_file` is reserved for new files and full rewrites; the description says so, because models otherwise default to whole-file rewrites that burn output tokens and clobber concurrent changes.

Both return `EditResult` with per-hunk `HunkResult` outcomes and a Tree-sitter `syntax_valid` check, so a structurally broken edit is rejected before the language server sees it and the model gets the specific failing hunk back rather than a bare `false`.

### Execution

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `run_command` | `(argv: str[], timeout_s=120) -> CommandResult` | D | exec-scope | untrusted |
| `run_tests` | `(selector?, pristine=true) -> TestReport` | I | exec-scope | trusted |

`run_command` takes **`argv` as a list, never a shell string** — no implicit shell interpolation, which removes an entire class of quoting bugs and makes the audit log unambiguous. A shell is available explicitly via `["bash","-lc",…]` when genuinely needed, and that form is what policy inspects.

`run_tests` is separated from `run_command` because it is the gate signal: `pristine=true` runs against the read-only injected suite, and results feed `GateReport` directly. Routing tests through generic command execution would let a candidate's own harness modifications shape the result.

Command output is truncated at 30k characters head+tail with the middle elided and `full_output_uri` set. Note: `run_command` stays DESTRUCTIVE, which means `ls`/`cat`/`pytest --collect-only` are never re-executed in replay.

### Version Control

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `git_read` | `(op, args) -> GitResult` | P | vcs-scope | trusted |
| `git_commit` | `(args) -> GitResult` | D | vcs-scope | trusted |

Git is split into two tools: `git_read` (ops: `status`, `diff`, `log`, `show`, `blame`) and `git_commit`. Push, force operations, history rewrites, and remote mutations are **not exposed** — they require a human grant through `request_approval`.

### Memory & Planning

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `remember` | `(content, kind, provenance) -> memory_id` | I | memory-write | trusted |
| `recall` | `(query, k=10, as_of?) -> Recall[]` | P | — | trusted |
| `update_plan` | `(tasks: TaskSpec[]) -> None` | I | — | trusted |
| `request_approval` | `(summary, diff?, criteria) -> Decision` | I | — | trusted |

`remember` now requires a `memory-write` grant; content derived from EXTERNAL inherits EXTERNAL provenance. `recall` results carry provenance; the prompt assembler wraps EXTERNAL in `<untrusted-data>` at render time.

`request_approval` is the human gate as a **tool the model can call**, not only a policy interrupt. It blocks durably: the task parks in `input-required`, survives restart, notifies out of band, and denies on timeout.

### Research

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `web_search` | `(query) -> SearchResult[]` | P | net-scope | **untrusted** |
| `web_fetch` | `(url) -> ContentBlock[]` | P | net-scope | **untrusted** |

Both are gated by the egress allowlist at the network namespace. Their output is wrapped in explicit untrusted-data delimiters — this is the highest-risk injection channel in the system (see [Security & Threat Model](../02-architecture/security-and-threat-model.md), T1).

### Delegation

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `spawn_subagent` | `(task: TaskSpec, budget) -> AsyncIterator[Event]` | I | delegate-scope | trusted |

Sub-agents receive a **strict subset** of the parent's grants and an explicit budget slice from the `ResourceGovernor`. Grant escalation across a delegation boundary is impossible by construction; a sub-agent cannot acquire a capability its parent lacked.

## **Untrusted Output Envelope**

Every tool marked untrusted has its output wrapped before it enters context:

```
<untrusted-data source="web_fetch" uri="https://...">
…content…
</untrusted-data>
```

The system prompt establishes that content inside such an envelope is **information to reason about, never instruction to follow**. This is a mitigation, not a guarantee — the load-bearing defenses remain credential exclusion, egress allowlisting, and human grants for out-of-worktree writes.

## **Registration**

```python
registry.register(
    name="edit_file",
    schema=EDIT_FILE_SCHEMA,  # JSON Schema, validated at dispatch
    effect=EffectClass.DESTRUCTIVE,
    grant_scope="write",
    trusted_output=True,
)
```

MCP-discovered tools register through the same path with `trusted_output=False` by default — a third-party server is an injection vector until proven otherwise.

## **What Is Deliberately Absent**

| Not a tool | Why |
| :--- | :--- |
| `think` / scratchpad | Reasoning blocks already carry this; a tool round-trip adds latency for nothing |
| `list_tools` | The schema list is already in the prompt |
| Separate `create_file` | `write_file` covers it; two tools for one act wastes budget |
| `git_push`, `git_reset --hard` | Out-of-worktree and history-destroying: human grant only |
| Direct DB or cloud clients | Belongs in MCP servers, per the ≤5% rule |
