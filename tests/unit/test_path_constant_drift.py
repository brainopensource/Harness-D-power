"""Guard the path-keyed constants that select what a gate protects.

A gate keyed to a path does not fail when the path moves — it passes, over an empty
set. That is the worst failure mode a gate has, because a gate that protects nothing
is indistinguishable in CI from a gate with nothing to complain about.

The archive reorganisation demonstrated this twice in one commit:

- `docs_budget.EXEMPT_PREFIX` was `"08-decisions/"`. The ADRs moved to
  `_archive/08-decisions/`, the prefix stopped matching, 28 files and 5,779 words
  silently re-entered the normative budget, and the resulting 19,720/15,000 breach
  read as prose bloat rather than as the one-string defect it was.
- 19 relative links resolved one directory short of the repo root for the same reason.

The third instance has not fired yet and is the one that matters: `tcb-isolation` in
`.importlinter` and `TCB_PATHS` in `ci.yml` both name `src/sagiha/...`. When the tree
becomes `src/aether/`, the Trusted Computing Base enforcement does not break loudly —
it goes vacuous, and F6's entire mechanical guarantee evaporates while CI stays green.

Each test here asserts that a selector selects something.
"""

from __future__ import annotations

import configparser
import importlib.util
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"


def _load_docs_budget():
    spec = importlib.util.spec_from_file_location("docs_budget", REPO_ROOT / "scripts" / "docs_budget.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adr_exemption_matches_at_least_one_file() -> None:
    """The ADR budget exemption must exempt something."""
    docs_budget = _load_docs_budget()
    entries = docs_budget.collect(DOCS_ROOT)

    assert docs_budget.assert_exemption_matches(entries) is None, (
        f"`{docs_budget.EXEMPT_DIR_NAME}` selects no file under docs/"
    )
    assert sum(1 for e in entries if e.exempt) >= 1


def test_adr_exemption_reports_drift_when_it_matches_nothing() -> None:
    """The drift check has to be able to fail, or it is not a check.

    Every gate ships with a test proving it can fail — the standing rule this repo
    adopted after a remediation verified green and then regressed.
    """
    docs_budget = _load_docs_budget()
    docs_budget.EXEMPT_DIR_NAME = "a-directory-that-does-not-exist"
    entries = docs_budget.collect(DOCS_ROOT)

    message = docs_budget.assert_exemption_matches(entries)
    assert message is not None
    assert "matches no file" in message


def _importlinter_source_modules() -> dict[str, list[str]]:
    parser = configparser.ConfigParser()
    parser.read(REPO_ROOT / ".importlinter", encoding="utf-8")
    contracts: dict[str, list[str]] = {}
    for section in parser.sections():
        if not section.startswith("importlinter:contract:"):
            continue
        raw = parser[section].get("source_modules", "")
        modules = [m.strip() for m in raw.split("\n") if m.strip()]
        if modules:
            contracts[section.split(":")[-1]] = modules
    return contracts


def _module_exists(dotted: str) -> bool:
    base = REPO_ROOT / "src" / Path(*dotted.split("."))
    return base.is_dir() or base.with_suffix(".py").is_file()


@pytest.mark.parametrize("contract,modules", sorted(_importlinter_source_modules().items()))
def test_importlinter_source_modules_resolve(contract: str, modules: list[str]) -> None:
    """Every module an import-linter contract names must exist on disk.

    import-linter reports an unresolvable source module as an error, but only when the
    job runs against a tree where the package is importable at all. Asserting it here
    means a rename is caught by the unit suite rather than by whoever later wonders why
    `tcb-isolation` never flagged anything.
    """
    missing = [m for m in modules if not _module_exists(m)]
    assert not missing, (
        f"contract `{contract}` names source modules that do not exist: {missing}. "
        f"A forbidden-import contract over a module that is absent forbids nothing."
    )


#: `benchmarks/definitions` is named by `TCB_PATHS` and does not exist. This is a known,
#: recorded defect (audit register C18), not drift introduced here: `noise-floor.md` and
#: `auditoria_sagiha.md` §1.2 both describe `benchmarks/definitions/s0-core.json` as
#: "committed and pinned" and treat it as TCB, but `benchmarks/` is empty and untracked.
#: The consequence is that the `bench-aa` CI job, which is guarded on that file existing,
#: is a permanent silent no-op — a gate that cannot fail.
#:
#: It is listed here rather than deleted from `TCB_PATHS` because the protection is
#: correct and the suite is what is missing. Building the suite is the fix; when it lands,
#: the xfail below flips to XPASS and this entry has to be removed.
KNOWN_ABSENT_TCB_FRAGMENTS = frozenset({"benchmarks/definitions"})


def _tcb_fragments() -> list[str]:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    match = re.search(r"TCB_PATHS='([^']+)'", ci)
    assert match is not None, "TCB_PATHS not found in ci.yml — did the job get renamed?"
    # The value is a grep -E alternation over path fragments, with `.` escaped for grep.
    fragments = [frag.replace("\\.", ".") for frag in match.group(1).split("|")]
    assert fragments, "TCB_PATHS is empty"
    return fragments


def test_ci_tcb_paths_match_tracked_files() -> None:
    """Every `TCB_PATHS` fragment that is supposed to exist must select something.

    This is the one that will break at the `src/sagiha/` -> `src/aether/` migration.
    When it does, this test fails and names the constant, instead of letting the TCB
    job pass over an empty diff for the rest of the project's life.
    """
    fragments = [f for f in _tcb_fragments() if f not in KNOWN_ABSENT_TCB_FRAGMENTS]

    unmatched = [frag for frag in fragments if not list(REPO_ROOT.glob(f"{frag}*"))]
    assert not unmatched, (
        f"TCB_PATHS names path fragments that match nothing in the tree: {unmatched}. "
        f"The tcb-check job greps the PR diff against these; a fragment that matches no "
        f"file cannot protect one, and the job will pass vacuously."
    )


#: The forward direction (`test_ci_tcb_paths_match_tracked_files`) only proves every
#: `TCB_PATHS` fragment resolves to something; it says nothing about whether the fragments
#: *cover* what `spec.md` §6 actually declares immutable. An omission — a TCB module that
#: exists, is real, and is simply never named — passes the forward test cleanly, which is
#: exactly the failure mode T3 exists to close (sprint-04.md Task 3, point 3: `TCB_PATHS`
#: selected neither the evaluator, the manifest, the families, the validator nor the
#: executor before this change).
#:
#: This list is derived from two authoritative sources, cross-referenced:
#:   1. `docs/spec.md` §6 "Trusted Computing Base" table: "Policy engine · evaluator ·
#:      gates · task manifests and split assignment · gate-family declarations ·
#:      workflow schema, validator and executor · CI configuration · `.importlinter`".
#:   2. `.importlinter`'s `aether-tcb-isolation` and `aether-workflow-tcb-isolation`
#:      contracts' `source_modules` (the machine-checked forbidden-import boundary),
#:      which additionally names `aether.measurement.statistics` — not spelled out by
#:      name in spec.md §6 prose but covered by "evaluator" / "gates" in substance and
#:      enforced as TCB by import-linter today.
#: `src/aether/kernel/policy` and `src/aether/kernel/dispatch` are deliberately omitted
#: here even though they are TCB, because they were already covered by `TCB_PATHS`
#: before this sprint's change — this list exists to catch the *newly required* coverage,
#: not to duplicate the whole set.
SPEC_DECLARED_TCB_PATHS = frozenset(
    {
        "src/aether/measurement/evaluator.py",  # spec.md §6 "evaluator"
        "src/aether/measurement/manifest.py",  # spec.md §6 "task manifests and split assignment"
        "src/aether/measurement/schemas",  # spec.md §6 "task manifests" (schema)
        "src/aether/measurement/families",  # spec.md §6 "gate-family declarations"
        "src/aether/measurement/statistics.py",  # .importlinter aether-tcb-isolation
        "src/aether/workflow/validator.py",  # spec.md §6 "workflow schema, validator"
        "src/aether/workflow/executor.py",  # spec.md §6 "... and executor"
        "src/aether/workflow/schemas",  # spec.md §6 "workflow schema"
    }
)


def test_tcb_paths_cover_every_spec_declared_tcb_path() -> None:
    """Reverse direction: every spec-declared TCB path must be covered by a `TCB_PATHS` fragment.

    The forward test (`test_ci_tcb_paths_match_tracked_files`) proves each fragment
    resolves to something real; it cannot catch a spec-declared TCB module that simply
    has no fragment naming it at all. This is the direction that catches an omission.
    """
    fragments = _tcb_fragments()
    uncovered = [
        declared
        for declared in sorted(SPEC_DECLARED_TCB_PATHS)
        if not any(declared.startswith(frag) or frag.startswith(declared) for frag in fragments)
    ]
    assert not uncovered, (
        f"spec.md §6 declares these TCB paths but no `TCB_PATHS` fragment in ci.yml covers "
        f"them: {uncovered}. A spec-declared TCB module with no selecting fragment is "
        f"unprotected while `PHASE-0-LOCK.md` and STATUS.md record the TCB gate as enforced."
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "audit register C18: benchmarks/definitions/s0-core.json is documented as "
        "committed and pinned but benchmarks/ is empty and untracked, which makes the "
        "bench-aa job a permanent no-op. Recorded as a known gap rather than hidden; "
        "building the suite flips this to XPASS and the marker comes off."
    ),
)
def test_known_absent_tcb_fragments_are_still_absent() -> None:
    """Hold the C18 gap open and visible until the benchmark suite exists.

    `strict=True` matters: if someone builds the suite without touching this file, the
    unexpected pass fails the run and forces the exemption to be retired. A known gap
    that quietly stops being a gap is how the exemption in `docs_budget.py` survived
    long enough to break the budget.
    """
    for frag in sorted(KNOWN_ABSENT_TCB_FRAGMENTS):
        assert list(REPO_ROOT.glob(f"{frag}*")), f"{frag} now exists — remove it from the exemption"


def test_script_output_path_constants_have_an_existing_parent_directory() -> None:
    """`run_aa_floor.py` wrote its report to docs/rationale/benchmarks/, which
    does not exist, and `_write` mkdir's parents — so the floor run would have
    created a stray tree and left the canonical noise-floor.md saying "not yet
    taken". No gate caught it, because the drift test covered .importlinter and
    TCB_PATHS and nothing else.
    """
    from scripts.run_aa_floor import DEFAULT_REPORT

    assert DEFAULT_REPORT.parent.exists(), (
        f"DEFAULT_REPORT parent directory {DEFAULT_REPORT.parent} does not exist"
    )
