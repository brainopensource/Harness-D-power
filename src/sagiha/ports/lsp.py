"""LSPAdapter — diagnostics, definitions, references from a warm language-server pool.

See docs/03-contracts-and-models/lsp-interface.md. No `@runtime_checkable`. Diagnostics rank
candidates (soft score) — never admit; trivially gameable (delete failing code, `# type: ignore`,
widen to `Any`). `no_new_suppressions` is the hard gate that closes the cheapest exploit.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.content import Symbol
from sagiha.domain.graph import DiagnosticItem

PORT_VERSION: Final = 1
STABILITY: Final = "provisional"


class LSPAdapter(Protocol):
    async def get_diagnostics(self, file_path: str) -> list[DiagnosticItem]: ...

    async def get_definition(self, file_path: str, line: int, column: int) -> Symbol | None: ...

    async def get_references(self, file_path: str, line: int, column: int) -> list[Symbol]: ...
