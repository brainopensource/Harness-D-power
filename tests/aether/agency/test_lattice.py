"""ADR-0018's lattice change, proven to fail (T1, `TASK-053`).

`lint-imports` staying green after the lattice edit is necessary and not
sufficient: a contract nobody can make fail is a comment (`vision.md` §4,
`coding_guidelines.md` §1.2). Both tests here write a real importing module
under `src/aether/agency/`, shell out to the real `lint-imports` CLI against
the real `.importlinter`, and assert it goes red — then delete the module.
This is a decision `capability_layer.md` §3.1 makes on purpose: `agency/`
must be structurally unable to reach the judge, and "structurally unable"
is only true if removing the guard makes a real import fail.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
_PROBE_DIR = REPO_ROOT / "src" / "aether" / "agency" / "_lattice_probe"
#: The console script, not `python -m importlinter` — the package has no
#: `__main__.py` and `sys.executable`'s own venv is where it is installed.
_LINT_IMPORTS = str(Path(sys.executable).parent / "lint-imports")


def _run_lint_imports() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_LINT_IMPORTS, "--config", str(REPO_ROOT / ".importlinter")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def probe_module():
    _PROBE_DIR.mkdir(parents=True, exist_ok=True)
    (_PROBE_DIR / "__init__.py").write_text("", encoding="utf-8")
    probe = _PROBE_DIR / "probe.py"
    try:
        yield probe
    finally:
        probe.unlink(missing_ok=True)
        (_PROBE_DIR / "__init__.py").unlink(missing_ok=True)
        try:
            _PROBE_DIR.rmdir()
        except OSError:
            pass


def test_an_agency_module_importing_workflow_breaks_lint_imports(probe_module: Path) -> None:
    """`agency/` sits below `workflow/` (ADR-0018): an upward import must be
    a lattice violation, not a style preference."""
    probe_module.write_text("from aether.workflow.step import WorkflowStep\n", encoding="utf-8")

    result = _run_lint_imports()

    assert result.returncode != 0, f"lint-imports did not fail:\n{result.stdout}"
    assert "AETHER: full architectural lattice" in result.stdout


def test_an_agency_module_importing_the_evaluator_breaks_lint_imports(probe_module: Path) -> None:
    """The finding recorded in the Sprint 5 dev prompt §4.2: layer order alone
    PERMITS agency -> measurement (measurement sits below agency), so this
    contract — not layer order — is the only thing standing between a
    capability and constructing its own `RealEvaluator`. I7 depends on there
    being exactly one judge."""
    probe_module.write_text("from aether.measurement.evaluator import RealEvaluator\n", encoding="utf-8")

    result = _run_lint_imports()

    assert result.returncode != 0, f"lint-imports did not fail:\n{result.stdout}"
    assert "cannot reach the TCB judge" in result.stdout


def test_lint_imports_is_green_on_the_real_tree() -> None:
    """The other half of the proof: the guard is not so strict that it fails
    on legitimate code. Runs against the actual `src/aether/agency/`, no probe."""
    result = _run_lint_imports()

    assert result.returncode == 0, f"lint-imports failed on the real tree:\n{result.stdout}"
    assert "Contracts: 11 kept, 0 broken." in result.stdout
