"""Per-repo license gate — "exports only from repos whose license permits derivative training
data, recorded per sample" (`next_gen_architecture_specs.md` §6).

Fails closed: an unrecognized or absent SPDX identifier refuses export rather than assuming
permission, matching the `GateReport` doctrine (absence of a verdict must never be a pass).
"""

from __future__ import annotations

#: Conservative starter allowlist — permissive licenses with no attribution-propagation or
#: copyleft clause that would complicate derivative training data. Expand deliberately, per
#: repo, not by loosening this default.
ALLOWED_SPDX_LICENSES: frozenset[str] = frozenset(
    {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "Unlicense"}
)


def is_export_permitted(spdx_license: str | None) -> bool:
    """`None` (no recorded license) refuses export — the same fail-closed posture the coding
    gates use for `None`-valued verdicts."""
    if spdx_license is None:
        return False
    return spdx_license in ALLOWED_SPDX_LICENSES
