---
status: historical
retrieval: excluded
updated: 2026-08-01
---
# v2-S6 Retrieval, Code Graph & Cold-Start Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship real FTS5 + Tree-sitter code-graph retrieval, three code-intel tools, construction-time Layer-6 seeds, and `sagiha init` — all off by default (`retrieval.enabled=false`).

**Architecture:** One Tree-sitter walk per file feeds AST-bounded chunks (FTS5) and graph edges (SQLite). Query via `Indexer` / `CodeGraph` ports. Seed only at `ContextAssembler` construction. Dense tier deferred (ADR-0014).

**Tech Stack:** Python ≥3.13, `tree-sitter` + `tree-sitter-language-pack`, SQLite FTS5, `anyio`, existing ports in `src/sagiha/ports/{indexer,code_graph}.py`.

**Spec:** `docs/superpowers/specs/2026-07-31-v2-s6-retrieval-code-graph-design.md`

## Global Constraints

- `retrieval.enabled` defaults to `false`; no default-on without ablation evidence
- Layer-6 seed accepted only at `ContextAssembler` construction (ADR-0021)
- Code-intel tools: `trusted_output=True`, `EffectClass.PURE`, stay within 20-tool cap
- Indexer must skip markdown with `retrieval: excluded` frontmatter
- Dense / embeddings forbidden this sprint (ADR-0014)
- TCB (`kernel/policy`, `outer_loop/evaluator`) unchanged
- Test count monotonic; `pyright` 0; `lint-imports` 5/5; `ruff` clean

---

## File map

| File | Responsibility |
| :--- | :--- |
| `src/sagiha/adapters/indexer/chunking.py` | Tree-sitter → `Chunk` dataclasses |
| `src/sagiha/adapters/indexer/fts5.py` | FTS5 store + query + `reindex` |
| `src/sagiha/adapters/indexer/frontmatter.py` | Detect `retrieval: excluded` |
| `src/sagiha/adapters/indexer/service.py` | Shared walk → indexer + graph |
| `src/sagiha/adapters/code_graph/treesitter.py` | Edges, BFS, co-change |
| `src/sagiha/adapters/tools/builtins.py` | Register 3 tools when wired |
| `src/sagiha/domain/config.py` | `RetrievalConfig.enabled` |
| `src/sagiha/composition.py` | Wire indexer/graph/tools/seed helper |
| `src/sagiha/outer_loop/init/__init__.py` + `generate.py` | AGENTS.md generation |
| `src/sagiha/cli.py` | `sagiha init` |
| `docs/STATUS.md` | Mark S6 in progress / mechanism close |

---

### Task 1: AST chunking + FTS5 indexer + frontmatter exclusion

**Files:**
- Create: `src/sagiha/adapters/indexer/chunking.py`
- Create: `src/sagiha/adapters/indexer/frontmatter.py`
- Modify: `src/sagiha/adapters/indexer/fts5.py`
- Modify: `src/sagiha/adapters/indexer/__init__.py`
- Test: `tests/unit/test_fts5_indexer_scaffolding.py` → replace with real tests in `tests/unit/test_fts5_indexer.py`
- Test: `tests/contracts/test_indexer_conformance.py`
- Fixture: `tests/fixtures/retrieval_mini/` (small Python package + one excluded `.md`)

**Interfaces:**
- Consumes: `tree_sitter_language_pack.get_parser`, `Symbol` / `SymbolRef` / `RetrievalHit`
- Produces:
  - `Chunk(path: str, symbol_path: str, start_line: int, end_line: int, text: str)`
  - `chunk_python_source(path: str, source: bytes, *, max_chunk_tokens: int) -> list[Chunk]`
  - `is_retrieval_excluded(text: str) -> bool`
  - `FTS5Indexer.reindex_file(path: str, source: str) -> None`
  - `FTS5Indexer.reindex_root(root: Path, *, max_chunk_tokens: int = 1024) -> int`
  - Port methods return real data after index

- [ ] **Step 1: Write failing conformance tests**

Create `tests/fixtures/retrieval_mini/pkg/util.py`:

```python
"""Util module."""


def greet(name: str) -> str:
    """Return a greeting."""
    return f"hello {name}"


class Greeter:
    def shout(self, name: str) -> str:
        return greet(name).upper()
```

Create `tests/fixtures/retrieval_mini/docs/secret.md`:

```markdown
---
status: rationale
retrieval: excluded
---
This must never appear in FTS hits: UNIQUE_EXCLUDED_TOKEN_XYZ
```

Create `tests/fixtures/retrieval_mini/docs/visible.md`:

```markdown
---
status: rationale
---
VISIBLE_DOC_TOKEN_ABC appears in index
```

Create `tests/contracts/test_indexer_conformance.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from sagiha.adapters.indexer.fts5 import FTS5Indexer

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_mini"


@pytest.mark.asyncio
async def test_reindex_finds_symbols_and_skeleton(tmp_path: Path) -> None:
    db = tmp_path / "index.db"
    idx = FTS5Indexer(db_path=str(db))
    n = await idx.reindex_root(FIXTURE)
    assert n >= 1
    syms = await idx.find_symbols("greet", limit=10)
    assert any(s.ref.name == "greet" for s in syms)
    skel = await idx.get_skeleton("pkg/util.py")
    assert "def greet" in skel
    assert "return f" not in skel
    hits = await idx.neighbors("greet", limit=10)
    assert hits
    assert all(0.0 <= h.score <= 1.0 for h in hits)


@pytest.mark.asyncio
async def test_excluded_frontmatter_not_indexed(tmp_path: Path) -> None:
    idx = FTS5Indexer(db_path=str(tmp_path / "index.db"))
    await idx.reindex_root(FIXTURE)
    hits = await idx.neighbors("UNIQUE_EXCLUDED_TOKEN_XYZ", limit=20)
    assert hits == []
    visible = await idx.neighbors("VISIBLE_DOC_TOKEN_ABC", limit=20)
    assert any("VISIBLE_DOC_TOKEN_ABC" in h.chunk for h in visible)
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `uv run pytest tests/contracts/test_indexer_conformance.py -q`

Expected: FAIL (`reindex_root` missing or empty skeleton/neighbors).

- [ ] **Step 3: Implement frontmatter + chunking + FTS5**

`frontmatter.py` — scan leading `---` YAML for `retrieval:` value `excluded` (no PyYAML required).

`chunking.py` — `get_parser("python")`; walk `function_definition`, `async_function_definition`, `class_definition`; emit `Chunk` with symbol path (`module.Class.method`).

`fts5.py` — store chunks + symbols; implement `reindex_root` / `reindex_file`. Skip `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.sagiha`. For `*.md`/`*.mdx`: skip if excluded. `get_skeleton` from symbols table. `neighbors` via FTS5 MATCH with scores normalized 0–1. `find_symbols` on `symbols.name`.

- [ ] **Step 4: Invert scaffolding tests**

Replace empty-assert tests with index-via-`reindex_file` assertions. Delete obsolete “returns empty” cases.

- [ ] **Step 5: Verify**

Run:

```bash
uv run pytest tests/contracts/test_indexer_conformance.py tests/unit/test_fts5_indexer*.py -q
uv run pyright src/sagiha/adapters/indexer
uv run ruff check src/sagiha/adapters/indexer tests/contracts/test_indexer_conformance.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/sagiha/adapters/indexer tests/contracts/test_indexer_conformance.py tests/fixtures/retrieval_mini tests/unit/test_fts5_indexer*.py
git commit -m "$(cat <<'EOF'
feat(s6): real FTS5 indexer with AST-bounded chunks

Replace quiet FTS5 shell with Tree-sitter chunking, symbol table,
and retrieval:excluded frontmatter filtering.
EOF
)"
```

---

### Task 2: Tree-sitter code graph + rebuild-from-HEAD

**Files:**
- Modify: `src/sagiha/adapters/code_graph/treesitter.py`
- Create: `src/sagiha/adapters/indexer/service.py`
- Test: `tests/unit/test_code_graph_scaffolding.py` → real tests
- Test: `tests/contracts/test_code_graph_conformance.py`
- Fixture: add `tests/fixtures/retrieval_mini/pkg/client.py`

**Interfaces:**
- Consumes: parsers/chunks from Task 1; `GraphEdge`, `SymbolRef`, `CoChange`
- Produces:
  - `TreeSitterCodeGraph.index_file(path: str, source: bytes) -> list[GraphEdge]`
  - `TreeSitterCodeGraph.rebuild_from_root(root: Path) -> int`
  - `IndexService(root, indexer, graph).reindex(paths: list[str] | None = None) -> None`
  - Real `impacted_by` BFS; `callers_of`; `co_changed_with` via git

- [ ] **Step 1: Write failing tests**

Add fixture `pkg/client.py`:

```python
from pkg.util import greet


def main() -> None:
    print(greet("world"))
```

Create `tests/contracts/test_code_graph_conformance.py`:

```python
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sagiha.adapters.code_graph.treesitter import TreeSitterCodeGraph

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_mini"


def _edge_set(db_path: str) -> set[tuple[str, str, str]]:
    with sqlite3.connect(db_path) as c:
        return set(c.execute("SELECT src, dst, kind FROM edges").fetchall())


@pytest.mark.asyncio
async def test_import_edges_and_impacted_by(tmp_path: Path) -> None:
    g = TreeSitterCodeGraph(db_path=str(tmp_path / "g.db"))
    n = await g.rebuild_from_root(FIXTURE)
    assert n >= 1
    impacted = await g.impacted_by("pkg/util.py", hops=2)
    assert isinstance(impacted, list)


@pytest.mark.asyncio
async def test_rebuild_from_head_deterministic(tmp_path: Path) -> None:
    db1 = str(tmp_path / "g1.db")
    db2 = str(tmp_path / "g2.db")
    g1 = TreeSitterCodeGraph(db_path=db1)
    g2 = TreeSitterCodeGraph(db_path=db2)
    await g1.rebuild_from_root(FIXTURE)
    await g2.rebuild_from_root(FIXTURE)
    assert _edge_set(db1) == _edge_set(db2)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/contracts/test_code_graph_conformance.py -q`

- [ ] **Step 3: Implement graph + IndexService**

Extract imports → `kind="imports"`; definitions → `defines`; best-effort same-file calls → `calls`. `impacted_by`: hop-limited BFS with cycle detection. `co_changed_with`: `git log --name-only` co-occurrence (return `[]` if not a git repo). `IndexService.reindex`: one parse → chunks + edges.

- [ ] **Step 4: Verify + commit**

```bash
uv run pytest tests/contracts/test_code_graph_conformance.py tests/unit/test_code_graph*.py -q
git add src/sagiha/adapters/code_graph src/sagiha/adapters/indexer/service.py tests/contracts/test_code_graph_conformance.py tests/fixtures/retrieval_mini tests/unit/test_code_graph*.py
git commit -m "$(cat <<'EOF'
feat(s6): Tree-sitter code graph with rebuild-from-HEAD

Deterministic import/define edges, hop-limited impacted_by, shared
IndexService walk with the FTS5 indexer.
EOF
)"
```

---

### Task 3: Tools + composition seed wiring (`enabled=false`)

**Files:**
- Modify: `src/sagiha/domain/config.py`
- Modify: `src/sagiha/adapters/tools/builtins.py`
- Modify: `src/sagiha/composition.py`
- Modify: `src/sagiha/cli.py`
- Modify: `src/sagiha/agency/run_loop.py` (optional `retrieval_seed` default `()`)
- Test: `tests/unit/test_code_intel_tools.py`
- Test: extend `tests/contracts/test_composition.py`

**Interfaces:**
- Consumes: `Kernel.indexer`, `Kernel.code_graph`, `RetrievalConfig`
- Produces:
  - `RetrievalConfig.enabled: bool = False`
  - `register_builtin_tools(..., indexer=None, code_graph=None)` registers +3 tools iff provided
  - `build_retrieval_seed(indexer, goal: str, top_k: int) -> tuple[RetrievalHit, ...]`
  - `build_kernel` wires indexer/graph only when enabled

- [ ] **Step 1: Failing tests**

Assert: `enabled=False` → `kernel.indexer is None`, tool schemas count stays at builtin six.  
`enabled=True` → indexer set, `find_symbols` registered, `trusted_output=True`.  
Assembler seed-only contract still passes.

- [ ] **Step 2: Implement config, tools, composition, seed path**

Add `enabled: bool = False` to `RetrievalConfig`. Register `find_symbols` / `get_skeleton` / `impacted_by` as PURE + trusted when indexer/graph passed. Wire DBs under `.sagiha/`. `RunLoop` accepts `retrieval_seed: tuple[RetrievalHit, ...] = ()` into `ContextAssembler`. CLI builds seed only when enabled.

- [ ] **Step 3: Verify replay unchanged under defaults**

```bash
uv run pytest tests/unit/test_code_intel_tools.py tests/contracts/test_composition.py tests/unit/test_sprint3a_e2e.py -q
uv run sagiha replay verify --verify --cassette tests/fixtures/replay_smoke/cassette.json --workspace tests/fixtures/replay_smoke/workspace
```

- [ ] **Step 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(s6): code-intel tools and seed-only retrieval wiring

Register find_symbols/get_skeleton/impacted_by when retrieval.enabled;
default remains false so cassette digests stay stable.
EOF
)"
```

---

### Task 4: `sagiha init` + STATUS closeout

**Files:**
- Create: `src/sagiha/outer_loop/init/__init__.py`
- Create: `src/sagiha/outer_loop/init/generate.py`
- Modify: `src/sagiha/cli.py`
- Modify: `docs/STATUS.md`
- Modify: `docs/implementation/development_plan_v2.md` (S6 mechanism close note)
- Test: `tests/unit/test_sagiha_init.py`

**Interfaces:**
- Consumes: optional `CodeGraph`, filesystem toolchain sniff
- Produces: `generate_agents_md(root: Path, *, graph: CodeGraph | None, force: bool) -> Path`

- [ ] **Step 1: Failing test**

```python
@pytest.mark.asyncio
async def test_init_writes_agents_md(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "demo.py").write_text("def main():\n    pass\n", encoding="utf-8")
    from sagiha.outer_loop.init.generate import generate_agents_md

    path = await generate_agents_md(tmp_path, graph=None, force=False)
    text = path.read_text(encoding="utf-8")
    assert path.name == "AGENTS.md"
    assert "Python" in text or "demo" in text.lower()
```

- [ ] **Step 2: Implement generator + `sagiha init` CLI**

Sections: Project, Toolchain, Layout, Conventions. Optional graph module list. Fail if `AGENTS.md` exists unless `--force`.

- [ ] **Step 3: Load `AGENTS.md` into run system prompt when present** (even if retrieval disabled). Absent file → no prompt change (byte-stable).

- [ ] **Step 4: Update STATUS** — S6 mechanism closed / ablations deferred pre-default-on; `sagiha init` available.

- [ ] **Step 5: Full regression**

```bash
uv run pytest -q
uv run pyright src/sagiha
uv run ruff check src/sagiha
uv run lint-imports
```

- [ ] **Step 6: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(s6): sagiha init and Wave 5 mechanism closeout

Generate AGENTS.md from toolchain/graph; document honest-negative
ablation deferral in STATUS.
EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
| :--- | :---: |
| AST-bounded FTS5 chunks | 1 |
| `retrieval: excluded` | 1 |
| Code graph edges + rebuild | 2 |
| Shared IndexService walk | 2 |
| Tools trusted PURE | 3 |
| Seed-only assembler wiring | 3 |
| `enabled=false` default | 3 |
| `sagiha init` | 4 |
| STATUS honest close | 4 |
| Ablations / recall@10 | deferred (Task 4 docs) |
