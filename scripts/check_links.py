#!/usr/bin/env python3
"""Resolve every relative markdown link under docs/ and fail on any that does not.

See refactor_sagiha_v2_guidelines.md §4.2 (PR-0b). PR-0a repaired seven dead links by
hand; that does not scale, and `docs/STATUS.md` had already been deleted out from under
four inbound links before anyone noticed. From here the check is mechanical.

Scope is deliberately narrow — **relative** links only. External URLs are not fetched
(a network call in CI is a flake source, not a gate), and pure `#anchor` links are not
resolved against heading text.

Usage:
    uv run python scripts/check_links.py            # exit 1 on any dead link
    uv run python scripts/check_links.py --list     # also print every link checked
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"

#: Inline links `[text](target)` and reference definitions `[label]: target`.
_INLINE = re.compile(r"\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]+)")
_REFDEF = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)

_SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "ftp://", "data:")

#: Fenced code blocks are stripped before scanning: shell transcripts and python
#: snippets contain bracket/paren pairs that are not links.
_FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


class DeadLink:
    __slots__ = ("source", "target")

    def __init__(self, source: Path, target: str) -> None:
        self.source = source
        self.target = target

    def __str__(self) -> str:
        return f"{self.source}: {self.target}"


def extract_targets(text: str) -> list[str]:
    stripped = _FENCE.sub("", text)
    targets = [m.group(1) for m in _INLINE.finditer(stripped)]
    targets += [m.group(1) for m in _REFDEF.finditer(stripped)]
    return [t.strip("<>") for t in targets]


def is_relative(target: str) -> bool:
    if not target or target.startswith("#"):
        return False
    return not target.lower().startswith(_SKIP_SCHEMES)


def resolve(source: Path, target: str) -> bool:
    """True when `target`, read relative to `source`'s directory, exists on disk."""
    path_part = target.split("#", 1)[0].split("?", 1)[0]
    if not path_part:
        return True  # bare fragment — nothing to resolve
    candidate = (source.parent / path_part).resolve()
    return candidate.exists()


def check(docs_root: Path, *, list_all: bool = False) -> list[DeadLink]:
    dead: list[DeadLink] = []
    for md in sorted(docs_root.rglob("*.md")):
        for target in extract_targets(md.read_text(encoding="utf-8")):
            if not is_relative(target):
                continue
            ok = resolve(md, target)
            if list_all:
                rel = md.relative_to(REPO_ROOT)
                print(f"{'ok  ' if ok else 'DEAD'} {rel} -> {target}")
            if not ok:
                dead.append(DeadLink(md.relative_to(REPO_ROOT), target))
    return dead


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="print every link checked")
    parser.add_argument("--docs-root", type=Path, default=DOCS_ROOT)
    args = parser.parse_args(argv)

    dead = check(args.docs_root, list_all=args.list)
    total_files = sum(1 for _ in args.docs_root.rglob("*.md"))

    if dead:
        print(f"\n{len(dead)} dead relative link(s) across {total_files} files:", file=sys.stderr)
        for d in dead:
            print(f"  {d}", file=sys.stderr)
        print(
            "\nFix the link or the target. A link to a file that a reorganisation moved is "
            "how docs/STATUS.md went missing for four inbound references.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: every relative link in {total_files} markdown files under docs/ resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
