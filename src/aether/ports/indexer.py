"""Indexer — syntax-tier retrieval boundary."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aether.domain.ids import Frozen
from aether.domain.workspace import WorktreeRef


class SymbolHit(Frozen):
    repo_rel_path: str
    line: int
    kind: str
    name: str
    snippet: str


@runtime_checkable
class Indexer(Protocol):
    """Syntax-tier retrieval (tree-sitter adapter, ADR-0011). Semantic answers
    come from the project's own toolchain at T2 — deliberately not this port."""

    async def build(self, worktree: WorktreeRef) -> None: ...

    async def search(self, worktree: WorktreeRef, query: str, limit: int = 20) -> tuple[SymbolHit, ...]: ...

    async def outline(self, worktree: WorktreeRef, repo_rel_path: str) -> tuple[SymbolHit, ...]: ...
