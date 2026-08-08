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


#: `retrieval: excluded` in a document's frontmatter. Same predicate
#: `docs_budget.py` already applies to the word ceiling, applied here for the
#: same reason: a file no retrieval surfaces and no live document links *into*
#: cannot send a reader anywhere, so its internal links are not a live gate.
#:
#: Without this the gate was permanently red — 109 dead links across 93 files,
#: 96 of them inside `docs/_archive/`, which `README.md` describes as deletable
#: "without breaking a link or losing a binding claim". A gate that is red for
#: content the tree has declared non-load-bearing gets reported green from
#: memory instead of re-run, which is exactly what happened to `STATUS.md`.
#: Excluded files are counted and printed, never silently skipped.
_RETRIEVAL_EXCLUDED = re.compile(r"^retrieval:\s*excluded\s*$", re.MULTILINE)


def is_retrieval_excluded(text: str) -> bool:
    head = text.split("---", 2)
    if len(head) < 3 or head[0].strip():
        return False  # no leading frontmatter block
    return bool(_RETRIEVAL_EXCLUDED.search(head[1]))


def is_relative(target: str) -> bool:
    if not target or target.startswith("#"):
        return False
    return not target.lower().startswith(_SKIP_SCHEMES)


def resolve(source: Path, target: str) -> bool:
    """True when `target`, read relative to `source`'s directory (or file:// URL), exists on disk."""
    if target.lower().startswith("file://"):
        file_path = target.split("file://", 1)[1].split("#", 1)[0].split("?", 1)[0]
        return Path(file_path).exists()
    path_part = target.split("#", 1)[0].split("?", 1)[0]
    if not path_part:
        return True  # bare fragment — nothing to resolve
    candidate = (source.parent / path_part).resolve()
    return candidate.exists()


def _display_path(md: Path) -> Path:
    """Path to show in output: repo-relative when possible, absolute otherwise.

    `md.relative_to(REPO_ROOT)` raises ValueError for any `--docs-root` outside the repo,
    and it sat on the *failure* branch — so the reporting path crashed instead of reporting,
    and only for trees that actually contained a dead link. It was found by
    `tests/unit/test_docs_gates.py`, which checks the tree in a tmp dir: the first test to
    plant a dead link is the first run that ever reached this line.
    """
    try:
        return md.relative_to(REPO_ROOT)
    except ValueError:
        return md


def check(docs_root: Path, *, list_all: bool = False, skipped: list[Path] | None = None) -> list[DeadLink]:
    dead: list[DeadLink] = []
    for md in sorted(docs_root.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        if is_retrieval_excluded(text):
            if skipped is not None:
                skipped.append(_display_path(md))
            continue
        for target in extract_targets(text):
            if not is_relative(target):
                continue
            ok = resolve(md, target)
            if list_all:
                print(f"{'ok  ' if ok else 'DEAD'} {_display_path(md)} -> {target}")
            if not ok:
                dead.append(DeadLink(_display_path(md), target))
    return dead


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="print every link checked")
    parser.add_argument("--docs-root", type=Path, default=DOCS_ROOT)
    args = parser.parse_args(argv)

    skipped: list[Path] = []
    dead = check(args.docs_root, list_all=args.list, skipped=skipped)
    total_files = sum(1 for _ in args.docs_root.rglob("*.md"))
    checked = total_files - len(skipped)

    if skipped:
        # Printed, never silent. "How many files does this gate not cover" is
        # the first question to ask of any gate reporting green.
        print(f"`retrieval: excluded`, not checked: {len(skipped)} file(s)")
        if args.list:
            for path in skipped:
                print(f"skip {path}")

    if dead:
        print(f"\n{len(dead)} dead relative link(s) across {checked} checked files:", file=sys.stderr)
        for d in dead:
            print(f"  {d}", file=sys.stderr)
        print(
            "\nFix the link or the target. A link to a file that a reorganisation moved is "
            "how docs/STATUS.md went missing for four inbound references.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: every relative link in {checked} checked markdown files under docs/ resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
