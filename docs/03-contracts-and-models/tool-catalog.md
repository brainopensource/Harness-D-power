---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Tool Catalog**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Normative catalog of core tools shipping with the binary. Dynamic MCP servers extend this catalog at runtime.

## **Budget Discipline**

* **Cap**: Core catalog capped at **20 tools** to optimize prompt space and selection accuracy.
* **Consolidation**: Multi-mode parameters preferred over near-duplicate tools.
* **Threshold**: Capabilities required in <5% of tasks are relegated to external MCP servers.

## **The Catalog**

**Legend** — **Effect**: `P` pure, `I` idempotent, `D` destructive (see [Domain Schemas](./domain-schemas.md)). **Grant**: required capability token. **Trust**: output handling.

### **Navigation & Reading**

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `read_file` | `(path, offset?, limit?) -> ContentBlock[]` | P | read-scope | untrusted |
| `list_dir` | `(path, depth=1) -> DirEntry[]` | P | read-scope | untrusted |
| `glob` | `(pattern, path?) -> str[]` | P | read-scope | untrusted |
| `grep` | `(pattern, path?, glob?, mode="content") -> Match[]` | P | read-scope | untrusted |

*Note*: `read_file` always paginates (default 2000 lines; sets `truncated: true` and `full_output_uri`). `grep` uses `mode` (`content` | `files` | `count`).

### **Code Intelligence**

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `find_symbols` | `(query, limit=20) -> Symbol[]` | P | read-scope | trusted |
| `get_skeleton` | `(path) -> str` | P | read-scope | trusted |
| `find_references` | `(path, line, col) -> Symbol[]` | P | read-scope | trusted |
| `get_diagnostics` | `(path?) -> DiagnosticItem[]` | P | read-scope | trusted |
| `impacted_by` | `(path, hops=2) -> str[]` | P | read-scope | trusted |

*Note*: Derived deterministically via Tree-sitter, LSP, and git, making their output trusted.

### **Mutation**

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `apply_edit` | `(request: EditRequest) -> EditResult` | D | write-scope | trusted |
| `write_file` | `(path, content) -> EditResult` | D | write-scope | trusted |

*Note*: `apply_edit` applies search/replace hunk edits with Tree-sitter `syntax_valid` validation. `write_file` is reserved for file creation and complete rewrites.

### **Execution**

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `run_command` | `(argv: str[], timeout_s=120) -> CommandResult` | D | exec-scope | untrusted |
| `run_tests` | `(selector?, pristine=true) -> TestReport` | I | exec-scope | trusted |

*Note*: `run_command` takes `argv` as a list (no implicit shell string interpolation); output truncated at 30k chars. `run_tests` executes against read-only injected test suites (`pristine=true`) to feed `GateReport`.

### **Version Control**

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `git_read` | `(op, args) -> GitResult` | P | vcs-scope | trusted |
| `git_commit` | `(args) -> GitResult` | D | vcs-scope | trusted |

*Note*: Remote pushes, history rewrites, and destructive actions are excluded; they require human approval via `request_approval`.

### **Memory & Planning**

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `remember` | `(content, kind, provenance) -> memory_id` | I | memory-write | trusted |
| `recall` | `(query, k=10, as_of?) -> Recall[]` | P | — | trusted |
| `update_plan` | `(tasks: TaskSpec[]) -> None` | I | — | trusted |
| `request_approval` | `(summary, diff?, criteria) -> Decision` | I | — | trusted |

*Note*: `request_approval` parks the task in `input-required` until operator decision or timeout.

### **Research**

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `web_search` | `(query) -> SearchResult[]` | P | net-scope | untrusted |
| `web_fetch` | `(url) -> ContentBlock[]` | P | net-scope | untrusted |

*Note*: Network egress is policy-gated. Output is wrapped in untrusted boundaries (see [Security & Threat Model](../02-architecture/security-and-threat-model.md)).

### **Delegation**

| Tool | Signature | Effect | Grant | Trust |
| :--- | :--- | :--- | :--- | :--- |
| `spawn_subagent` | `(task: TaskSpec, budget) -> AsyncIterator[Event]` | I | delegate-scope | trusted |

*Note*: Sub-agents receive a strict subset of parent grants and a resource budget allocation.

## **Untrusted Output Envelope**

Outputs marked untrusted are encapsulated before prompt assembly:

```xml
<untrusted-data source="web_fetch" uri="https://...">
...content...
</untrusted-data>
```

## **Registration & Exclusions**

```python
registry.register(
    name="apply_edit",
    schema=EDIT_FILE_SCHEMA,
    effect=EffectClass.DESTRUCTIVE,
    grant_scope="write",
    trusted_output=True,
)
```

| Not in Core Catalog | Rationale |
| :--- | :--- |
| `think` / scratchpad | Covered by native provider reasoning blocks. |
| `list_tools` | Tool schemas are pre-rendered into the system prompt. |
| `create_file` | Handled by `write_file`. |
| `git_push` / `git_reset --hard` | Destructive out-of-worktree actions require human approval grants. |
| DB / cloud clients | Offloaded to external MCP servers. |
