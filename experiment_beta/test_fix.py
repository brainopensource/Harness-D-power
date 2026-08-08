#!/usr/bin/env python3
"""Offline regression test for `improved_edit_format.py` — no network, no
Ollama. Reproduces exactly the near-miss cases found in the small-model
investigation, run through both the real (unmodified) parser and the
experimental one, so the delta is visible side by side.

Also re-asserts every existing security/behaviour guarantee from
tests/aether/workflow/test_edit_format.py, to make sure tolerance was not
bought by weakening a guard.

Run: uv run python3 experiment_beta/test_fix.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aether.workflow.edit_format import WholeFileCodeblockFormat  # noqa: E402
from improved_edit_format import ImprovedWholeFileCodeblockFormat  # noqa: E402

CODE = "def is_even(n: int) -> bool:\n    return n % 2 == 0"

REGRESSION_CASES: list[tuple[str, str, bool]] = [
    # (label, raw model output, should the ORIGINAL parser already pass it?)
    ("canonical ```python:main.py", f"```python:main.py\n{CODE}\n```", True),
    ("```python + '# main.py'", f"```python\n# main.py\n{CODE}\n```", True),
    ("```python + '# filename: main.py'", f"```python\n# filename: main.py\n{CODE}\n```", True),
    ("qwen2.5 empty label ```python:", f"```python:\n{CODE}\n```", False),
    ("llama3.2 '### main.py'", f"```python\n### main.py\n{CODE}\n```", False),
    ("llama3.2 earlier leading '/'", f"```python:/main.py\n{CODE}\n```", False),
    ("no label at all, single retrieved file", f"```python\n{CODE}\n```", False),
]

SECURITY_CASES = [
    "/storage.py",
    "/etc/passwd.py",
    "../outside.py",
    "a/../../up.py",
]


def _passes(fmt: object, raw: str) -> tuple[bool, list[str]]:
    parsed = fmt.parse(raw)  # type: ignore[attr-defined]
    return bool(parsed.files), [f.repo_rel_path for f in parsed.files]


def main() -> int:
    original = WholeFileCodeblockFormat()
    improved = ImprovedWholeFileCodeblockFormat(known_files=("main.py",), test_paths=("run_tests.py",))

    print("=" * 78)
    print("REGRESSION: near-miss recovery")
    print("=" * 78)
    failures = 0
    for label, raw, original_should_pass in REGRESSION_CASES:
        orig_pass, orig_paths = _passes(original, raw)
        imp_pass, imp_paths = _passes(improved, raw)

        if orig_pass != original_should_pass:
            print(f"UNEXPECTED BASELINE  {label!r}: original parser pass={orig_pass}, expected {original_should_pass}")
            failures += 1

        status = "OK " if imp_pass else "FAIL"
        delta = "(fixed by experiment)" if imp_pass and not orig_pass else ("(already passed)" if orig_pass else "")
        print(f"{status} {label:38s} original={orig_pass!s:5} improved={imp_pass!s:5} {imp_paths} {delta}")
        if not imp_pass:
            failures += 1

    print()
    print("=" * 78)
    print("SECURITY GUARD: must still refuse every worktree-escaping path")
    print("=" * 78)
    for path in SECURITY_CASES:
        raw = f"```python:{path}\n{CODE}\n```"
        imp_pass, imp_paths = _passes(improved, raw)
        status = "OK  refused" if not imp_pass else "FAIL ADMITTED"
        print(f"{status:14s} {path}")
        if imp_pass:
            failures += 1

    print()
    print("=" * 78)
    print("SECURITY GUARD: leading '/' only recovered when it matches a KNOWN file")
    print("=" * 78)
    unknown = f"```python:/nonexistent_elsewhere.py\n{CODE}\n```"
    imp_pass, _ = _passes(improved, unknown)
    status = "OK  refused (not a known file)" if not imp_pass else "FAIL ADMITTED an unknown absolute path"
    print(f"{status}")
    if imp_pass:
        failures += 1

    print()
    if failures:
        print(f"RESULT: {failures} check(s) FAILED")
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
