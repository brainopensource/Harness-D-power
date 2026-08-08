"""Prove the two documentation gates can fail.

House rule: *every gate ships with a test proving it can fail* (`docs/measurement.md` §5).
Both docs gates were exempt from that rule and both were wrong because of it — the Phase 0
lock audit found `docs/STATUS.md` reporting "Docs word budget, relative links — Green" while
`check_links.py` was returning 7 dead links and `docs_budget.py` was failing on 5 files with
no `status:` frontmatter.

Neither failure was subtle. Nobody had run them, because a gate whose green is never checked
against a planted red is indistinguishable from a gate that always passes.

Each test plants exactly one defect in a temporary docs tree and asserts the gate returns
non-zero, then asserts the same tree clean returns zero. Stdlib + pytest only, no `src/`
import: these must not be breakable by a dependency change unrelated to docs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_links  # noqa: E402
import docs_budget  # noqa: E402

_CLEAN_DOC = """\
---
status: normative
updated: 2026-08-06
---

# Clean

A link that resolves: [sibling](./sibling.md).
"""

_SIBLING = """\
---
status: rationale
updated: 2026-08-06
---

# Sibling
"""


@pytest.fixture
def docs_tree(tmp_path: Path) -> Path:
    """A minimal docs tree that both gates pass, plus the ADR exemption directory.

    `docs_budget.assert_exemption_matches` fails when the exemption selects nothing, so the
    fixture has to contain a `decisions/` file for the *clean* case to be genuinely clean.
    """
    root = tmp_path / "docs"
    (root / "decisions").mkdir(parents=True)
    (root / "index.md").write_text(_CLEAN_DOC, encoding="utf-8")
    (root / "sibling.md").write_text(_SIBLING, encoding="utf-8")
    (root / "decisions" / "0001-example.md").write_text(_SIBLING, encoding="utf-8")
    return root


def _links(root: Path) -> int:
    return check_links.main(["--docs-root", str(root)])


def _budget(root: Path, ceiling: int = 15000) -> int:
    return docs_budget.main(["--docs-root", str(root), "--max", str(ceiling)])


# --------------------------------------------------------------------------- clean baseline


def test_both_gates_pass_on_a_clean_tree(docs_tree: Path) -> None:
    assert _links(docs_tree) == 0
    assert _budget(docs_tree) == 0


# ------------------------------------------------------------------------------ link gate


def test_link_gate_fails_on_a_planted_dead_link(docs_tree: Path) -> None:
    """The exact defect that shipped: a link to a directory that does not exist.

    All seven live dead links were `docs/00/` — the directory is `docs/concepts/`.
    """
    (docs_tree / "index.md").write_text(
        _CLEAN_DOC + "\nA link that does not: [phase 0](./00/).\n", encoding="utf-8"
    )
    assert _links(docs_tree) == 1


def test_link_gate_fails_on_a_deleted_target(docs_tree: Path) -> None:
    """`docs/STATUS.md` was deleted out from under four inbound references before anyone
    noticed. Deleting the target must be as loud as writing a wrong link."""
    (docs_tree / "sibling.md").unlink()
    assert _links(docs_tree) == 1


def test_link_gate_ignores_external_urls_and_bare_anchors(docs_tree: Path) -> None:
    """Guard against over-tightening: a network call in CI is a flake source, not a gate."""
    (docs_tree / "index.md").write_text(
        _CLEAN_DOC + "\n[ext](https://example.invalid/nope) and [anchor](#heading).\n",
        encoding="utf-8",
    )
    assert _links(docs_tree) == 0


def test_link_gate_ignores_links_inside_fenced_code(docs_tree: Path) -> None:
    """Shell transcripts and code samples contain bracket/paren pairs that are not links."""
    (docs_tree / "index.md").write_text(
        _CLEAN_DOC + "\n```python\nx = foo[0](./does_not_exist.md)\n```\n", encoding="utf-8"
    )
    assert _links(docs_tree) == 0


# ---------------------------------------------------------------------------- budget gate


def test_budget_gate_fails_on_an_untagged_file(docs_tree: Path) -> None:
    """The defect that was actually red: five files under `docs/` carried no `status:`.

    An untagged file is invisible to the budget, so leaving one untagged adds normative
    words for free. The audit diagnosed an inflated ceiling and missed this entirely.
    """
    (docs_tree / "untagged.md").write_text("# No frontmatter\n\nwords\n", encoding="utf-8")
    assert _budget(docs_tree) == 1


def test_budget_gate_fails_on_an_invented_status(docs_tree: Path) -> None:
    """A file cannot dodge the ceiling by inventing a status value outside the taxonomy."""
    (docs_tree / "invented.md").write_text("---\nstatus: operational\n---\n\nwords\n", encoding="utf-8")
    assert _budget(docs_tree) == 1


def test_budget_gate_fails_when_over_the_ceiling(docs_tree: Path) -> None:
    (docs_tree / "fat.md").write_text("---\nstatus: normative\n---\n\n" + ("word " * 500), encoding="utf-8")
    assert _budget(docs_tree, ceiling=100) == 1


def test_budget_gate_fails_when_the_adr_exemption_selects_nothing(docs_tree: Path) -> None:
    """The C21 defect, generalised: the exemption matched `08-decisions/` by prefix, the
    archive move renamed the path, and 28 files silently re-entered the budget.

    A path-keyed constant that matches nothing does not announce itself — the number just
    gets bigger and the breach reads as prose bloat. Same class as a `tcb-isolation`
    contract that selects no module.
    """
    (docs_tree / "decisions" / "0001-example.md").unlink()
    (docs_tree / "decisions").rmdir()
    assert _budget(docs_tree) == 1


def test_budget_gate_does_not_count_rationale_or_historical(docs_tree: Path) -> None:
    """Guard against over-tightening in the other direction: the declared escape hatches
    must keep working, or the ceiling becomes unmeetable and gets raised instead of obeyed."""
    (docs_tree / "hist.md").write_text("---\nstatus: historical\n---\n\n" + ("word " * 500), encoding="utf-8")
    assert _budget(docs_tree, ceiling=100) == 0


_EXCLUDED_DOC = """\
---
status: historical
retrieval: excluded
updated: 2026-08-07
---

# Superseded

A link that does not resolve: [gone](./deleted-in-a-rename.md).
"""


def test_a_retrieval_excluded_file_is_skipped_but_counted(tmp_path: Path) -> None:
    """The link gate skips `retrieval: excluded` files — the same predicate the
    word budget already uses.

    The gate had been permanently red on 109 links, 96 of them inside
    `docs/_archive/`, which `README.md` describes as deletable "without breaking
    a link or losing a binding claim". A gate that is red for content the tree
    has declared non-load-bearing gets reported green from memory rather than
    re-run — which is what `STATUS.md` did.

    The skip is only defensible if it is *visible*, so this asserts the file is
    reported as unchecked rather than silently dropped.
    """
    (tmp_path / "clean.md").write_text(_CLEAN_DOC, encoding="utf-8")
    (tmp_path / "sibling.md").write_text(_SIBLING, encoding="utf-8")
    (tmp_path / "superseded.md").write_text(_EXCLUDED_DOC, encoding="utf-8")

    skipped: list[Path] = []
    dead = check_links.check(tmp_path, skipped=skipped)

    assert dead == []
    assert [p.name for p in skipped] == ["superseded.md"]
    assert check_links.main(["--docs-root", str(tmp_path)]) == 0


def test_the_exclusion_does_not_hide_a_dead_link_in_a_live_file(tmp_path: Path) -> None:
    """The half that makes the skip safe: excluding history must not become a
    way to exclude anything. A live document is still checked when an excluded
    one sits beside it."""
    (tmp_path / "superseded.md").write_text(_EXCLUDED_DOC, encoding="utf-8")
    (tmp_path / "live.md").write_text(
        "---\nstatus: normative\nupdated: 2026-08-07\n---\n\n# Live\n\n[gone](./missing.md)\n",
        encoding="utf-8",
    )

    assert check_links.main(["--docs-root", str(tmp_path)]) == 1


def test_retrieval_excluded_is_read_from_frontmatter_only() -> None:
    """The phrase in prose — this project writes about `retrieval: excluded`
    constantly — must not exempt a document that never declared it."""
    assert check_links.is_retrieval_excluded(_EXCLUDED_DOC) is True
    assert check_links.is_retrieval_excluded(_CLEAN_DOC) is False
    assert (
        check_links.is_retrieval_excluded(
            "---\nstatus: normative\n---\n\nWe tag the archive `retrieval: excluded`.\n"
        )
        is False
    )
