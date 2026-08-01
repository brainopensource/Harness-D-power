"""System prompt resolution — Layer 4 (`AGENTS.md`) injection at run setup."""

from __future__ import annotations

from pathlib import Path

import anyio

from sagiha.agency.run_loop import DEFAULT_SYSTEM_PROMPT


async def resolve_system_prompt(
    workspace_root: str | Path,
    *,
    base: str = DEFAULT_SYSTEM_PROMPT,
) -> str:
    """Return ``base`` unchanged when ``AGENTS.md`` is absent; append verbatim when present."""
    agents_path = anyio.Path(workspace_root) / "AGENTS.md"
    if not await agents_path.is_file():
        return base
    content = await agents_path.read_text(encoding="utf-8")
    if not content.strip():
        return base
    return f"{base}\n\n{content}"
