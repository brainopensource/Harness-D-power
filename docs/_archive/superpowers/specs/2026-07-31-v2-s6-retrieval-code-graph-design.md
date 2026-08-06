---
status: rationale
updated: 2026-07-31
retrieval: excluded
---

# v2-S6 Retrieval, Code Graph & Cold-Start — Design

> Approved in design review 2026-07-31. Approach: **shared Tree-sitter walk** (option 1).
> Close mode: **mechanism-first** (option A) — same honest-negative pattern as v2-S4.

## Goal

Replace quiet indexer/code-graph shells with real lexical+graph retrieval, register three
code-intel tools, wire construction-time Layer-6 seeds, and add `sagiha init` — all **off by
default** until ablations exist.

## Non-goals (this close)

- Labelled recall@10 suite / published recall target
- Retrieval-on vs off or init-on vs off E0 ablations
- Default-on flip (`retrieval.enabled` stays `false`)
- Dense / embedding tier (ADR-0014)
- `watchfiles` daemon (dependency may stay; API is explicit `reindex`)
- Multi-language beyond Python v1 (grammar pack ready; Python proves the path)
- Conductor / Story-DAG consumers (v2-S7+)

## Architecture

```text
workspace files
      │
      ▼
 IndexService.reindex(root, paths?)     ← one Tree-sitter walk
      ├──► chunking.py  → AST-bounded Chunks (symbol-path prefix)
      ├──► FTS5Indexer  → SQLite FTS5 + symbols table
      └──► TreeSitterCodeGraph → edges (imports/calls/defines/inherits)
                                      + co_change via git (on demand)

Run start (retrieval.enabled):
  goal → Indexer.neighbors / find_symbols → top_k RetrievalHit
       → ContextAssembler(retrieval_seed=…)   # construction only (ADR-0021)

Agentic mid-run:
  find_symbols | get_skeleton | impacted_by   # PURE, trusted_output=True
```

### Shared parse

One parse per file feeds both chunk emission and edge extraction. Do not dual-parse with
stdlib `ast` for the indexer and Tree-sitter for the graph.

### Chunk shape

Per [indexing-and-retrieval.md](../../05-tech-stack/indexing-and-retrieval.md):

- Unit = Tree-sitter function / method / class span (never fixed windows in v1 default)
- Prefix each chunk with: path, enclosing symbol path, signature
- Oversized bodies split on statement boundaries still carrying the signature prefix
- `RetrievalHit.score` normalized 0–1 (BM25 rank → min-max or reciprocal-rank in query batch)

### `retrieval: excluded`

When indexing markdown under the workspace, skip files whose YAML frontmatter includes
`retrieval: excluded`. Code files are always eligible (not doc-scoped). Applies to FTS5
content only; does not delete the file from the worktree.

### Config

```python
class RetrievalConfig(BaseModel):
    enabled: bool = False  # NEW — mirrors search.enabled honesty
    chunk_strategy: Literal["ast_bounded", "fixed_window"] = "ast_bounded"
    max_chunk_tokens: int = 1024
    top_k: int = 20
    graph_expansion_hops: int = 2
```

When `enabled=False`: do not construct indexer/graph in `build_kernel` (or construct but do
not seed / do not register code-intel tools — prefer **not wiring** to keep tool-schema
cache stable for cassette runs). Tools and seed activate only when enabled.

### Tools (≤20 cap: 6 → 9)

| Tool | Effect | trusted_output | Notes |
| :--- | :--- | :--- | :--- |
| `find_symbols` | PURE | True | harness-derived symbol list |
| `get_skeleton` | PURE | True | signatures only |
| `impacted_by` | PURE | True | graph BFS paths |

### Seed wiring

At run construction (CLI / `RunLoop` setup), if `retrieval.enabled` and indexer present:

1. Ensure index exists (`reindex` if DB missing/stale heuristic: missing file OK for v1)
2. Query with task goal → `top_k` hits
3. Pass `retrieval_seed=tuple(hits)` into `ContextAssembler` constructor only

No public refresh surface (existing contract tests must stay green).

### `sagiha init`

`outer_loop/init/` + CLI command:

- Detect toolchain (pyproject / package.json / Cargo.toml presence)
- Summarize top-level packages / modules from code graph
- Write `AGENTS.md` at workspace root (fail if exists unless `--force`)
- Content enters Layer 4 via caller-supplied system prompt (read `AGENTS.md` when present
  in run setup — additive, empty if absent)

### Ports (unchanged)

- `Indexer`: `find_symbols`, `get_skeleton`, `neighbors`
- `CodeGraph`: `upsert_edges`, `impacted_by`, `callers_of`, `co_changed_with`

Add concrete methods on adapters as needed for ingest (`reindex`, `index_file`) — port stays
query-shaped; ingest is adapter/composition API, not a new Protocol (remoteable later via
RPC if needed).

## Error handling

- Unparseable files: skip + log; do not fail full reindex
- Missing tree-sitter grammar cache: fail closed with actionable error (install/cache path)
- `get_skeleton` unknown path: return `""` (not raise)
- Graph rebuild: delete SQLite + full reindex; rebuild-from-HEAD test asserts edge set equality

## Testing

| Suite | Asserts |
| :--- | :--- |
| Indexer unit/conformance | Fixture Python package → symbols, skeleton, FTS neighbors non-empty |
| Graph unit | Import/call edges; hop-limited BFS; wipe+rebuild identical |
| Frontmatter | `retrieval: excluded` md never in FTS hits |
| Tools | Registered when enabled; trusted_output; schema count ≤20 |
| Seed | Assembler contract: no post-construction RetrievalHit surface |
| Init | Writes expected `AGENTS.md` sections; `--force` overwrite |

Ablation / recall gates: **deferred** — document in STATUS as pre-default-on hard deps
(same language as S4 BoN).

## Exit gate (amended honest-negative)

Mechanism complete; `retrieval.enabled=false` by default; exporter/tools/seed paths tested.
Empirical claims (recall@10, retrieval beats none, init beats none) **not published**.

## PR order

1. S6.1 — chunking + FTS5 + exclusion + invert scaffolding tests  
2. S6.2 — code graph + rebuild-from-HEAD  
3. S6.3 — tools + composition seed wiring (`enabled` flag)  
4. S6.4–S6.5 — `sagiha init` + STATUS update  

## References

- `docs/implementation/development_plan_v2.md` § v2-S6  
- `docs/implementation/refactor_sagiha_v2_guidelines.md` § Phase 6  
- ADR-0011, ADR-0014, ADR-0021  
- `docs/05-tech-stack/indexing-and-retrieval.md`  
