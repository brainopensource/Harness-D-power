"""Detect `retrieval: excluded` YAML frontmatter (no PyYAML dependency)."""

from __future__ import annotations


def is_retrieval_excluded(text: str) -> bool:
    """Return True if the document's leading frontmatter sets retrieval: excluded."""
    if not text.startswith("---"):
        return False
    # Find closing ---
    rest = text[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    else:
        return False
    end = rest.find("\n---")
    if end < 0:
        return False
    block = rest[:end]
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        if key.strip() == "retrieval" and val.strip().strip("'\"") == "excluded":
            return True
    return False
