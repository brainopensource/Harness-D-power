"""Secret redaction — reapplied at export, per `next_gen_architecture_specs.md` §6's hygiene
pass: "the same scanner as the log path re-applied at export".

Reuses `TelemetryConfig.redact_patterns` (name-shaped regexes: `api_key`, `secret`, `password`,
`token`) rather than inventing a second pattern list, so the export-time scanner and the
log-time scanner never silently drift from each other.
"""

from __future__ import annotations

import re
from typing import Any, cast

#: Matches `<pattern-name>` followed by a `:`/`=` assignment and a bare (unquoted-whitespace)
#: value — the shape `api_key: sk-abc123` or `TOKEN=xyz` takes in logs, prompts, and shell output.
_VALUE_AFTER_KEY = r"({pattern})(\s*[:=]\s*)([^\s'\"]+)"


def redact_text(text: str, patterns: list[str]) -> tuple[str, int]:
    """Returns `(redacted_text, hit_count)`. Never raises on a malformed pattern — a pattern
    compile failure disables that one pattern (logged by the caller, not here) rather than
    aborting the whole export, which would make one bad regex a denial-of-service on distillation.
    """
    redacted = text
    hits = 0
    for pattern in patterns:
        try:
            regex = re.compile(_VALUE_AFTER_KEY.format(pattern=pattern), re.IGNORECASE)
        except re.error:
            continue
        redacted, n = regex.subn(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", redacted)
        hits += n
    return redacted, hits


def redact_sample(data: dict[str, Any], patterns: list[str]) -> tuple[dict[str, Any], int]:
    """Recursively redacts every string value in a JSON-shaped `dict`/`list` structure — a
    sample's secrets can hide inside `messages`, `labels`, or a nested tool-call argument, and a
    shallow top-level-only pass would miss all three."""
    total_hits = 0

    def _walk(node: Any) -> Any:
        nonlocal total_hits
        if isinstance(node, str):
            redacted, hits = redact_text(node, patterns)
            total_hits += hits
            return redacted
        if isinstance(node, dict):
            node_dict = cast("dict[Any, Any]", node)
            walked_dict: dict[Any, Any] = {}
            for k, v in node_dict.items():
                walked_dict[k] = _walk(v)
            return walked_dict
        if isinstance(node, list):
            node_list = cast("list[Any]", node)
            return [_walk(v) for v in node_list]
        return node

    walked = _walk(data)
    return walked, total_hits
