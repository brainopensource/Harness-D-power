#!/usr/bin/env python3
"""Measure the normative word budget of docs/ and fail when it exceeds a ceiling.

See refactor_sagiha_v2_guidelines.md §4.2 (PR-0b). The v2 re-baseline found ~54k words
tagged `status: normative` against a 15,000-word ceiling — a 3.6x overshoot, not a trim.
Without a mechanical gate the ratio reverts within two sprints, so the ceiling is
ratcheted down in CI rather than asserted in prose.

A word is a whitespace-separated token in the markdown **body** (YAML frontmatter is
excluded, since it is metadata, not prose the retriever will ever surface).

Usage:
    uv run python scripts/docs_budget.py                 # report, always exit 0
    uv run python scripts/docs_budget.py --max 54000     # exit 1 if normative total exceeds
    uv run python scripts/docs_budget.py --format md     # committable into docs/STATUS.md
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"

#: Frontmatter values that count against the normative budget. `rationale` and
#: `historical` are the declared escape hatches; anything else is reported as untagged
#: so a doc cannot dodge the budget by inventing a new status value.
BUDGETED_STATUSES = frozenset({"normative"})
DECLARED_STATUSES = frozenset({"normative", "rationale", "historical"})

#: ADRs are exempt from the budget (guidelines §4.3): they are short, high-value, and
#: each one *replaces* long-form derivation elsewhere. Budgeting them would incentivise
#: exactly the wrong trade — prose in an architecture doc instead of a decision record.
#:
#: Matched as a path *component*, not a prefix. The prefix form (`"08-decisions/"`) broke
#: silently when the archive reorganisation moved the ADRs to `_archive/08-decisions/`:
#: 28 files and 5,779 words re-entered the budget and pushed it from 13,941 to 19,720,
#: which read as a content breach rather than the string drift it was. A component match
#: survives the next move; `assert_exemption_matches()` catches it if it does not.
EXEMPT_DIR_NAME = "decisions"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a `---`-delimited YAML frontmatter block off the body.

    Deliberately a flat `key: value` scan rather than a YAML parse: the docs tree uses
    only scalar keys, and this keeps the script stdlib-only like gen_event_catalog.py.
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            meta: dict[str, str] = {}
            for line in lines[1:idx]:
                key, sep, value = line.partition(":")
                if sep:
                    meta[key.strip()] = value.strip().strip("\"'")
            return meta, "\n".join(lines[idx + 1 :])
    return {}, text


def count_words(body: str) -> int:
    return len(body.split())


class DocEntry:
    __slots__ = ("path", "status", "retrieval", "words")

    def __init__(self, path: Path, status: str, retrieval: str, words: int) -> None:
        self.path = path
        self.status = status
        self.retrieval = retrieval
        self.words = words

    @property
    def exempt(self) -> bool:
        return EXEMPT_DIR_NAME in self.path.parts

    @property
    def budgeted(self) -> bool:
        if self.exempt:
            return False
        return self.status in BUDGETED_STATUSES


def collect(docs_root: Path) -> list[DocEntry]:
    entries: list[DocEntry] = []
    for md in sorted(docs_root.rglob("*.md")):
        meta, body = parse_frontmatter(md.read_text(encoding="utf-8"))
        entries.append(
            DocEntry(
                path=md.relative_to(docs_root),
                status=meta.get("status", "(untagged)"),
                retrieval=meta.get("retrieval", ""),
                words=count_words(body),
            )
        )
    return entries


def _by_directory(entries: list[DocEntry]) -> dict[str, tuple[int, int, int]]:
    """directory -> (files, total words, budgeted words)."""
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for e in entries:
        key = str(e.path.parent) if str(e.path.parent) != "." else "(root)"
        acc[key][0] += 1
        acc[key][1] += e.words
        if e.budgeted:
            acc[key][2] += e.words
    return {k: (v[0], v[1], v[2]) for k, v in sorted(acc.items())}


def render(entries: list[DocEntry], ceiling: int | None, fmt: str) -> str:
    budgeted = [e for e in entries if e.budgeted]
    total_words = sum(e.words for e in entries)
    budgeted_words = sum(e.words for e in budgeted)
    undeclared = [e for e in entries if e.status not in DECLARED_STATUSES]

    lines: list[str] = []

    def row(cells: list[str]) -> str:
        if fmt == "md":
            return "| " + " | ".join(cells) + " |"
        return "  " + "  ".join(cells)

    lines.append("## Docs Budget")
    lines.append("")
    lines.append(row(["Scope", "Files", "Words"]))
    if fmt == "md":
        lines.append("| :--- | ---: | ---: |")
    lines.append(row(["Whole `docs/` tree", str(len(entries)), f"{total_words:,}"]))
    lines.append(row(["Tagged `status: normative`", str(len(budgeted)), f"**{budgeted_words:,}**"]))
    if ceiling is not None:
        lines.append(row(["Ceiling (`--max`)", "—", f"{ceiling:,}"]))
        delta = budgeted_words - ceiling
        verdict = f"OVER by {delta:,}" if delta > 0 else f"under by {-delta:,}"
        lines.append(row(["Headroom", "—", verdict]))
    lines.append("")

    lines.append("### Per directory")
    lines.append("")
    lines.append(row(["Directory", "Files", "Words", "Normative"]))
    if fmt == "md":
        lines.append("| :--- | ---: | ---: | ---: |")
    for name, (files, words, budget) in _by_directory(entries).items():
        lines.append(row([f"`{name}`", str(files), f"{words:,}", f"{budget:,}"]))
    lines.append("")

    if budgeted:
        lines.append("### Largest normative files")
        lines.append("")
        lines.append(row(["File", "Words"]))
        if fmt == "md":
            lines.append("| :--- | ---: |")
        for e in sorted(budgeted, key=lambda x: -x.words)[:20]:
            lines.append(row([f"`{e.path}`", f"{e.words:,}"]))
        lines.append("")

    if undeclared:
        lines.append(
            f"### Files with an undeclared `status:` ({len(undeclared)}) — "
            f"declared taxonomy is {sorted(DECLARED_STATUSES)}"
        )
        lines.append("")
        for e in undeclared:
            lines.append(f"- `{e.path}` — `{e.status}`")
        lines.append("")

    excluded = [e for e in entries if e.retrieval == "excluded"]
    lines.append(f"`retrieval: excluded`: {len(excluded)} files, {sum(e.words for e in excluded):,} words")
    exempt = [e for e in entries if e.status in BUDGETED_STATUSES and e.exempt]
    lines.append(
        f"ADR exemption (`{EXEMPT_DIR_NAME}/`): {len(exempt)} files, "
        f"{sum(e.words for e in exempt):,} words excluded from the budget"
    )
    return "\n".join(lines)


def assert_exemption_matches(entries: list[DocEntry]) -> str | None:
    """Return an error message when the ADR exemption selects nothing.

    A path-keyed constant that matches no file does not announce itself: the budget
    simply gets larger and the breach is read as prose bloat. The exemption is only
    meaningful if it exempts something, so matching zero files is a defect in the
    constant, not a legitimate state of the tree.
    """
    if any(e.exempt for e in entries):
        return None
    return (
        f"FAIL: the ADR exemption `{EXEMPT_DIR_NAME}` matches no file under docs/.\n"
        f"Either the ADRs were removed, or they moved and this constant did not follow "
        f"them. Until it is corrected every ADR counts against the normative ceiling and "
        f"the resulting breach will look like a content problem."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="fail (exit 1) when the sum over `status: normative` files exceeds this",
    )
    parser.add_argument("--format", choices=("text", "md"), default="text")
    parser.add_argument("--docs-root", type=Path, default=DOCS_ROOT)
    args = parser.parse_args(argv)

    entries = collect(args.docs_root)
    print(render(entries, args.max, args.format))

    if args.max is None:
        return 0

    failed = False

    drift = assert_exemption_matches(entries)
    if drift is not None:
        print(f"\n{drift}", file=sys.stderr)
        failed = True

    # An untagged file is invisible to the budget, which makes "no `status:` key"
    # a loophole that evades the ceiling entirely (defect m-12). Listing them was
    # not enough — the gate has to fail.
    undeclared = [e for e in entries if e.status not in DECLARED_STATUSES]
    if undeclared:
        print(
            f"\nFAIL: {len(undeclared)} file(s) under `{args.docs_root}` declare no `status:`.\n"
            f"An untagged doc is not counted against the normative ceiling, so leaving one "
            f"untagged is a way to add normative words for free. Tag every file with one of "
            f"{sorted(DECLARED_STATUSES)}.",
            file=sys.stderr,
        )
        for e in undeclared:
            print(f"  {e.path}", file=sys.stderr)
        failed = True

    budgeted_words = sum(e.words for e in entries if e.budgeted)
    if budgeted_words > args.max:
        print(
            f"\nFAIL: normative word count {budgeted_words:,} exceeds ceiling {args.max:,} "
            f"(over by {budgeted_words - args.max:,}).\n"
            f"Demote a doc to `status: rationale`/`historical`, or delete words elsewhere — "
            f"a PR adding N normative words deletes N. ADRs are exempt by convention.",
            file=sys.stderr,
        )
        failed = True
    else:
        print(f"\nOK: normative word count {budgeted_words:,} is within ceiling {args.max:,}.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
