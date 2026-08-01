"""YAML frontmatter scanning for retrieval exclusion (no PyYAML dependency)."""

from __future__ import annotations


def is_retrieval_excluded(text: str) -> bool:
    """Return True when leading frontmatter sets ``retrieval: excluded``."""
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end == -1:
        return False
    frontmatter = text[3:end]
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith("retrieval:"):
            value = stripped.split(":", 1)[1].strip()
            return value == "excluded"
    return False
