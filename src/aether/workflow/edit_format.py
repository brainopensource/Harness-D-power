"""Re-export shim (TASK-055, ADR-0018) — kept for one release.

`edit_format.py` moved to `agency/capabilities/edit_format.py`: it is pure
(imports only `aether.domain.ids.Frozen`), so it belongs beside the other
capability protocols rather than in `workflow/nodes/`'s own package.
`workflow/nodes/{generate,repair}.py` still import from here; both names
resolve to the same classes. New code should import from
`aether.agency.capabilities.edit_format` directly.
"""

from __future__ import annotations

from aether.agency.capabilities.edit_format import (
    DEFAULT_EDIT_FORMAT,
    FORMATS,
    EditFormat,
    FileEdit,
    ParsedEdit,
    UnifiedDiffFormat,
    UnknownEditFormat,
    WholeFileCodeblockFormat,
    get_edit_format,
)

__all__ = [
    "DEFAULT_EDIT_FORMAT",
    "FORMATS",
    "EditFormat",
    "FileEdit",
    "ParsedEdit",
    "UnifiedDiffFormat",
    "UnknownEditFormat",
    "WholeFileCodeblockFormat",
    "get_edit_format",
]
