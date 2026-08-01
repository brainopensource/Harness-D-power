"""Tree-sitter-backed CodeGraph adapter — AST parsing, edge extraction, SQLite storage.

See ports/code_graph.py and docs/08-decisions/0011-split-code-and-episodic-graphs.md.
The code graph is a cache rebuilt from HEAD, not a system of record.
"""

from __future__ import annotations

import logging
import sqlite3
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from anyio.to_thread import run_sync
from tree_sitter import Node, Tree

from sagiha.adapters.indexer.chunking import parse_python
from sagiha.domain.graph import CoChange, GraphEdge, SymbolRef

logger = logging.getLogger(__name__)

_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", ".sagiha"})
_SYMBOL_NODE_TYPES = frozenset({"function_definition", "async_function_definition", "class_definition"})


@dataclass(frozen=True)
class _SymbolMeta:
    symbol_path: str
    path: str
    name: str
    kind: str
    line: int


def _module_name(path: str) -> str:
    stem = path
    if stem.endswith(".py"):
        stem = stem[:-3]
    return stem.replace("/", ".")


def _node_text(source: bytes, node: Node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _resolve_import(current_path: str, module: str | None, level: int) -> str | None:
    parts = current_path[:-3].split("/") if current_path.endswith(".py") else current_path.split("/")
    if level == 0:
        if not module:
            return None
        return module.replace(".", "/") + ".py"
    if level > len(parts) - 1:
        return None
    package = parts[: len(parts) - level]
    if module:
        package = [*package, *module.split(".")]
    return "/".join(package) + ".py"


def _symbol_path(module: str, name: str, *, class_name: str | None = None) -> str:
    if class_name is None:
        return f"{module}.{name}"
    return f"{module}.{class_name}.{name}"


def _parse_symbol_ref(symbol_path: str, *, module: str | None = None) -> SymbolRef | None:  # pyright: ignore[reportUnusedFunction]
    """Resolve a dotted symbol path to a ``SymbolRef`` using an optional module prefix."""
    parts = symbol_path.split(".")
    if len(parts) < 2:
        return None
    name = parts[-1]
    if module is None:
        return None
    module_parts = module.split(".")
    if len(parts) <= len(module_parts) or parts[: len(module_parts)] != module_parts:
        return None
    rest = parts[len(module_parts) :]
    file_path = "/".join(module_parts) + ".py"
    if len(rest) == 1 and rest[0][0].isupper():
        kind = "class"
    elif len(rest) > 1:
        kind = "method"
    else:
        kind = "function"
    return SymbolRef(path=file_path, name=name, kind=kind, line=1)  # type: ignore[arg-type]


class TreeSitterCodeGraph:
    """SQLite-backed code graph with Tree-sitter AST edge extraction."""

    def __init__(
        self,
        db_path: str = ".sagiha/code_graph.db",
        *,
        workspace_root: Path | None = None,
    ) -> None:
        self._db_path = db_path
        self._workspace_root = workspace_root
        self._init_db()

    def _init_db(self) -> None:
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    src TEXT NOT NULL,
                    dst TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    PRIMARY KEY (src, dst, kind)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS symbols (
                    path TEXT NOT NULL,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    PRIMARY KEY (path, name, line)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS symbol_refs (
                    symbol_path TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    line INTEGER NOT NULL
                );
                """
            )
            conn.commit()

    def _clear_edges(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM edges")
            conn.execute("DELETE FROM symbols")
            conn.execute("DELETE FROM symbol_refs")
            conn.commit()

    def _upsert_symbol_refs_sync(self, symbol_meta: Iterable[_SymbolMeta]) -> None:
        rows = [(m.symbol_path, m.path, m.name, m.kind, m.line) for m in symbol_meta]
        if not rows:
            return
        with sqlite3.connect(self._db_path) as conn:
            conn.executemany(
                """
                INSERT INTO symbol_refs (symbol_path, path, name, kind, line)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(symbol_path) DO UPDATE SET
                    path = excluded.path,
                    name = excluded.name,
                    kind = excluded.kind,
                    line = excluded.line
                """,
                rows,
            )
            conn.commit()

    def _upsert_edges_sync(self, edges: Iterable[GraphEdge]) -> None:
        rows = [(e.src, e.dst, e.kind, e.weight) for e in edges]
        if not rows:
            return
        with sqlite3.connect(self._db_path) as conn:
            conn.executemany(
                """
                INSERT INTO edges (src, dst, kind, weight)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(src, dst, kind) DO UPDATE SET weight = excluded.weight
                """,
                rows,
            )
            conn.commit()

    def replace_file_edges(
        self,
        path: str,
        edges: list[GraphEdge],
        symbol_meta: dict[str, _SymbolMeta] | None = None,
    ) -> None:
        """Replace all edges and symbols associated with a single file."""
        module = _module_name(path)
        meta = list(symbol_meta.values()) if symbol_meta else []
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                DELETE FROM edges
                WHERE src = ?
                   OR src LIKE ? OR dst LIKE ?
                """,
                (path, f"{module}.%", f"{module}.%"),
            )
            conn.execute("DELETE FROM symbols WHERE path = ?", (path,))
            conn.execute(
                "DELETE FROM symbol_refs WHERE path = ?",
                (path,),
            )
            for edge in edges:
                conn.execute(
                    """
                    INSERT INTO edges (src, dst, kind, weight)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(src, dst, kind) DO UPDATE SET weight = excluded.weight
                    """,
                    (edge.src, edge.dst, edge.kind, edge.weight),
                )
            for m in meta:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO symbols(path, name, kind, line)
                    VALUES (?, ?, ?, ?)
                    """,
                    (m.path, m.name, m.kind, m.line),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO symbol_refs(symbol_path, path, name, kind, line)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (m.symbol_path, m.path, m.name, m.kind, m.line),
                )
            conn.commit()

    def index_file_from_tree(
        self,
        path: str,
        source: bytes,
        tree: Tree,
    ) -> tuple[list[GraphEdge], dict[str, _SymbolMeta]]:
        """Extract import/define/call edges from an already-parsed Python tree."""
        module = _module_name(path)
        edges: list[GraphEdge] = []
        symbol_meta: dict[str, _SymbolMeta] = {}
        local_defs: dict[str, str] = {}
        imported_names: dict[str, str] = {}
        current_symbol: str | None = None
        current_class: str | None = None

        def add_edge(src: str, dst: str, kind: str) -> None:
            edges.append(GraphEdge(src=src, dst=dst, kind=kind))  # type: ignore[arg-type]

        def walk_imports(node: Node) -> None:
            if node.type == "import_statement":
                for child in node.children:
                    if child.type in {"dotted_name", "aliased_import"}:
                        name_node = child.child_by_field_name("name") or child
                        if name_node.type == "dotted_name" or name_node.type == "identifier":
                            module_name = _node_text(source, name_node)
                            target = _resolve_import(path, module_name, 0)
                            if target:
                                add_edge(path, target, "imports")
            elif node.type == "import_from_statement":
                module_node = node.child_by_field_name("module_name")
                module_name = _node_text(source, module_node) if module_node else None
                level = 0
                for child in node.children:
                    if child.type == "relative_import":
                        level = sum(1 for c in child.children if c.type == ".")
                target = _resolve_import(path, module_name, level)
                if target:
                    add_edge(path, target, "imports")
                import_module = _module_name(target) if target else module_name
                for child in node.children:
                    if child.type == "dotted_name" or child.type == "aliased_import":
                        imported = child.child_by_field_name("name") or child
                        alias = child.child_by_field_name("alias")
                        local = _node_text(source, alias or imported)
                        imported_name = _node_text(source, imported)
                        if import_module:
                            imported_names[local] = f"{import_module}.{imported_name}"
            for child in node.children:
                walk_imports(child)

        def register_def(name: str, *, class_name: str | None, node: Node) -> str:
            sym = _symbol_path(module, name, class_name=class_name)
            line = node.start_point[0] + 1
            if node.type == "class_definition":
                kind = "class"
            elif class_name is not None:
                kind = "method"
            else:
                kind = "function"
            local_defs[name] = sym
            symbol_meta[sym] = _SymbolMeta(
                symbol_path=sym,
                path=path,
                name=name,
                kind=kind,
                line=line,
            )
            add_edge(path, sym, "defines")
            return sym

        def walk_defs(node: Node, *, class_name: str | None = None) -> None:
            nonlocal current_symbol, current_class
            if node.type in _SYMBOL_NODE_TYPES:
                name_node = node.child_by_field_name("name")
                if name_node is None:
                    return
                name = _node_text(source, name_node)
                if node.type == "class_definition":
                    sym = register_def(name, class_name=class_name, node=node)
                    body = node.child_by_field_name("body")
                    if body is not None:
                        prev_symbol, prev_class = current_symbol, current_class
                        current_symbol, current_class = sym, name
                        for child in body.children:
                            walk_defs(child, class_name=name)
                        current_symbol, current_class = prev_symbol, prev_class
                    return
                sym = register_def(name, class_name=class_name, node=node)
                prev_symbol = current_symbol
                current_symbol = sym
                body = node.child_by_field_name("body")
                if body is not None:
                    for child in body.children:
                        walk_calls(child)
                current_symbol = prev_symbol
                return
            for child in node.children:
                walk_defs(child, class_name=class_name)

        def resolve_callee(name: str) -> str | None:
            if name in local_defs:
                return local_defs[name]
            if name in imported_names:
                return imported_names[name]
            return None

        def walk_calls(node: Node) -> None:
            if node.type == "call":
                fn = node.child_by_field_name("function")
                if fn is None:
                    return
                if fn.type == "identifier":
                    callee = resolve_callee(_node_text(source, fn))
                elif fn.type == "attribute":
                    attr = fn.child_by_field_name("attribute")
                    if attr is None:
                        return
                    method_name = _node_text(source, attr)
                    obj = fn.child_by_field_name("object")
                    if obj is not None and obj.type == "identifier":
                        base = local_defs.get(_node_text(source, obj))
                        callee = f"{base}.{method_name}" if base else None
                    else:
                        callee = resolve_callee(method_name)
                else:
                    callee = None
                if callee and current_symbol:
                    add_edge(current_symbol, callee, "calls")
            for child in node.children:
                walk_calls(child)

        walk_imports(tree.root_node)
        walk_defs(tree.root_node)
        return edges, symbol_meta

    def index_file(self, path: str, source: bytes) -> list[GraphEdge]:
        """Extract import/define/call edges from a Python source file."""
        tree = parse_python(source)
        edges, _ = self.index_file_from_tree(path, source, tree)
        return edges

    async def upsert_edges(self, edges: list[GraphEdge]) -> None:
        await run_sync(lambda: self._upsert_edges_sync(edges))

    async def rebuild_from_root(self, root: Path) -> int:
        """Walk *root*, rebuild the graph from Python sources. Returns file count."""

        def _sync() -> int:
            self._clear_edges()
            count = 0
            for file_path in sorted(root.rglob("*")):
                if not file_path.is_file():
                    continue
                if any(part in _SKIP_DIRS for part in file_path.parts):
                    continue
                if file_path.suffix != ".py":
                    continue
                rel = file_path.relative_to(root).as_posix()
                source = file_path.read_bytes()
                tree = parse_python(source)
                edges, symbol_meta = self.index_file_from_tree(rel, source, tree)
                self._upsert_edges_sync(edges)
                self._upsert_symbol_refs_sync(symbol_meta.values())
                count += 1
            return count

        return await run_sync(_sync)

    async def impacted_by(self, file_path: str, hops: int = 2) -> list[str]:
        """Hop-limited BFS over dependents (reverse edge traversal)."""

        def _sync() -> list[str]:
            module = _module_name(file_path)
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute("SELECT src, dst FROM edges").fetchall()

            reverse: dict[str, list[str]] = {}
            for src, dst in rows:
                reverse.setdefault(dst, []).append(src)

            start_nodes = {file_path}
            for src, dst in rows:
                if src == file_path and dst.startswith(f"{module}."):
                    start_nodes.add(dst)

            visited = set(start_nodes)
            frontier = list(start_nodes)
            results: list[str] = []
            for _ in range(hops):
                next_frontier: list[str] = []
                for node in frontier:
                    for neighbor in reverse.get(node, []):
                        if neighbor in visited:
                            continue
                        visited.add(neighbor)
                        if neighbor.endswith(".py"):
                            results.append(neighbor)
                        next_frontier.append(neighbor)
                frontier = next_frontier
                if not frontier:
                    break
            return results

        return await run_sync(_sync)

    async def callers_of(self, symbol: SymbolRef) -> list[SymbolRef]:
        """Find symbols that call the given symbol (best-effort, same-file and imports)."""

        def _sync() -> list[SymbolRef]:
            module = _module_name(symbol.path)
            target = _symbol_path(module, symbol.name)
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT src FROM edges WHERE kind = 'calls' AND dst = ?",
                    (target,),
                ).fetchall()
                callers: list[SymbolRef] = []
                for (src,) in rows:
                    row = conn.execute(
                        """
                        SELECT path, name, kind, line
                        FROM symbol_refs
                        WHERE symbol_path = ?
                        """,
                        (src,),
                    ).fetchone()
                    if row is not None:
                        callers.append(
                            SymbolRef(
                                path=row[0],
                                name=row[1],
                                kind=row[2],  # type: ignore[arg-type]
                                line=row[3],
                            )
                        )
            return callers

        return await run_sync(_sync)

    async def co_changed_with(self, path: str, since: datetime) -> list[CoChange]:
        """Mine git history for files that change alongside *path*."""

        def _sync() -> list[CoChange]:
            git_cwd = str(self._workspace_root) if self._workspace_root is not None else None
            try:
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        "--since",
                        since.astimezone(UTC).isoformat(),
                        "--name-only",
                        "--pretty=format:%H|%cI",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=git_cwd,
                )
            except OSError:
                return []
            if result.returncode != 0:
                return []

            counts: dict[str, int] = {}
            last_seen: dict[str, datetime] = {}
            current_commit: str | None = None
            current_time: datetime | None = None
            commit_files: set[str] = set()

            def flush_commit() -> None:
                nonlocal commit_files
                if current_commit is None or path not in commit_files:
                    commit_files = set()
                    return
                for other in commit_files:
                    if other == path:
                        continue
                    counts[other] = counts.get(other, 0) + 1
                    if current_time is not None:
                        prev = last_seen.get(other)
                        if prev is None or current_time > prev:
                            last_seen[other] = current_time
                commit_files = set()

            for line in result.stdout.splitlines():
                if "|" in line and not line.endswith(".py") and not line.endswith(".md"):
                    flush_commit()
                    commit, ts = line.split("|", 1)
                    current_commit = commit
                    current_time = datetime.fromisoformat(ts)
                    commit_files = set()
                elif line.strip():
                    commit_files.add(line.strip())
            flush_commit()

            return [
                CoChange(path=other, commits=count, last_seen=last_seen[other])
                for other, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            ]

        return await run_sync(_sync)
