"""tree-sitter Indexer adapter (ADR-0011) — syntax-tier retrieval.

First real adapter for the `Indexer` port. Not wired into the M1a DAG itself
(Gate 3 covers exactly the four boundaries the skeleton walks) — this is its
own deliverable, and `measurement/timers.py`'s AST-parse-and-validate F1 timer
wraps `build()` on a real small repo.
"""

from __future__ import annotations

import asyncio
import os

import tree_sitter_language_pack as tslp

from aether.domain.workspace import WorktreeRef
from aether.ports.indexer import SymbolHit

_EXTENSION_LANGUAGE: dict[str, str] = {".py": "python"}
_DEF_NODE_KIND: dict[str, str] = {"function_definition": "function", "class_definition": "class"}
_IGNORED_DIR_NAMES = {".git", "__pycache__", "node_modules", ".venv"}


def _worktree_path(worktrees_root: str, worktree: WorktreeRef) -> str:
    return os.path.join(worktrees_root, worktree.run_id, worktree.worktree_id)


class TreeSitterIndexer:
    """Symbol index is per worktree, held in process memory — rebuilt by a
    fresh `build()` call, not incrementally maintained (Block 4 territory)."""

    def __init__(self, worktrees_root: str) -> None:
        self._worktrees_root = worktrees_root
        self._index: dict[str, list[SymbolHit]] = {}

    async def build(self, worktree: WorktreeRef) -> None:
        path = _worktree_path(self._worktrees_root, worktree)
        self._index[worktree.worktree_id] = await asyncio.to_thread(self._build_sync, path)

    def _build_sync(self, path: str) -> list[SymbolHit]:
        """Blocking directory walk + parse — run via `asyncio.to_thread` from
        `build()` so it never blocks the event loop (ASYNC230/240)."""
        hits: list[SymbolHit] = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in _IGNORED_DIR_NAMES]
            for fname in files:
                lang = _EXTENSION_LANGUAGE.get(os.path.splitext(fname)[1])
                if lang is None:
                    continue
                abs_file = os.path.join(root, fname)
                rel_file = os.path.relpath(abs_file, path)
                hits.extend(self._parse_file(abs_file, rel_file, lang))
        return hits

    def _parse_file(self, abs_file: str, rel_file: str, lang: str) -> list[SymbolHit]:
        with open(abs_file, "rb") as f:
            source = f.read()
        parser = tslp.get_parser(lang)
        tree = parser.parse(source)

        hits: list[SymbolHit] = []
        for node in tree.root_node.children:
            kind = _DEF_NODE_KIND.get(node.type)
            if kind is None:
                continue
            name_node = node.child_by_field_name("name")
            name = source[name_node.start_byte : name_node.end_byte].decode() if name_node else "?"
            snippet = source[node.start_byte : node.end_byte].decode(errors="replace")[:200]
            hits.append(
                SymbolHit(
                    repo_rel_path=rel_file,
                    line=node.start_point[0] + 1,
                    kind=kind,
                    name=name,
                    snippet=snippet,
                )
            )
        return hits

    async def search(self, worktree: WorktreeRef, query: str, limit: int = 20) -> tuple[SymbolHit, ...]:
        hits = self._index.get(worktree.worktree_id, [])
        matched = [h for h in hits if query.lower() in h.name.lower()]
        return tuple(matched[:limit])

    async def outline(self, worktree: WorktreeRef, repo_rel_path: str) -> tuple[SymbolHit, ...]:
        hits = self._index.get(worktree.worktree_id, [])
        return tuple(h for h in hits if h.repo_rel_path == repo_rel_path)
