"""Toolchain — the port exists so gates never hardcode pytest and pyright. Optional.

See docs/03-contracts-and-models/hexagonal-ports.md#execution. `detect(root: str)` is
workspace-relative, not `pathlib.Path` — the known violation flagged in
docs/02-architecture/remoteable-ports.md, fixed here.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.graph import DiagnosticItem
from sagiha.domain.toolchain import CoverageReport, TestReport, ToolchainInfo

PORT_VERSION: Final = 1
STABILITY: Final = "provisional"


class Toolchain(Protocol):
    """Optional — unbound under profiles with `toolchain = "none"`."""

    async def detect(self, root: str) -> ToolchainInfo: ...

    async def test(self, selector: str | None = None, pristine: bool = True) -> TestReport: ...

    async def typecheck(self) -> list[DiagnosticItem]: ...

    async def lint(self) -> list[DiagnosticItem]: ...

    async def coverage(self) -> CoverageReport: ...
