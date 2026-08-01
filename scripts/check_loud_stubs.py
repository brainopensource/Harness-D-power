#!/usr/bin/env python3
"""Fail when an unimplemented adapter method returns a success-shaped literal.

See refactor_sagiha_v2_guidelines.md §5 PR-1.4 (H3). `ContainerSandbox.apply_edit`
returned `EditResult(applied=True, syntax_valid=True)` without touching anything, and
the scaffolding test suite pinned that as correct — the lie was regression-protected.
Making the stubs raise fixes today; this gate is what stops the next one landing.

The rule: a method whose body does nothing must not resolve to something a caller reads
as success. `raise NotImplementedError` is the only honest body for unimplemented work.

Scope is the adapters known to be scaffolding. This is deliberately a small allowlist
rather than a tree-wide scan: a real adapter legitimately returns `applied=True`, and a
gate that cries wolf on those gets disabled.

Usage:
    uv run python scripts/check_loud_stubs.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Scaffolding modules: placement is correct, bodies are pending. Every public async
#: method here must raise, with the documented exceptions below.
#: `adapters/sandbox/container.py` left this list in v2-S5 when ContainerSandbox became real.
STUB_MODULES = (
    "src/sagiha/adapters/mcp/driver.py",
    "src/sagiha/adapters/telemetry/otel.py",
)

#: `qualname` -> why returning is truthful here.
EXEMPT = {
    "MCPClientDriver.list_tools": (
        "empty discovery is a truthful null — no servers connected means no tools exist"
    ),
}


def _raises_not_implemented(node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    body = [s for s in node.body if not isinstance(s, ast.Expr) or not isinstance(s.value, ast.Constant)]
    return len(body) == 1 and isinstance(body[0], ast.Raise)


def check(repo_root: Path) -> list[str]:
    violations: list[str] = []
    for rel in STUB_MODULES:
        path = repo_root / rel
        if not path.exists():
            violations.append(f"{rel}: listed as a stub module but does not exist")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for fn in cls.body:
                if not isinstance(fn, ast.AsyncFunctionDef | ast.FunctionDef):
                    continue
                if fn.name.startswith("_"):
                    continue
                qualname = f"{cls.name}.{fn.name}"
                if qualname in EXEMPT:
                    continue
                if not _raises_not_implemented(fn):
                    violations.append(
                        f"{rel}:{fn.lineno}: {qualname} does not raise. An unimplemented "
                        f"method that returns a value lies to its caller (H3)."
                    )
    return violations


def main() -> int:
    violations = check(REPO_ROOT)
    if violations:
        print("Stub honesty check FAILED:\n", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print(
            '\nUse `raise NotImplementedError("<sprint> — see docs/STATUS.md")`. '
            "If the return is genuinely truthful (an empty discovery, say), add it to "
            "EXEMPT in this script with the reason.",
            file=sys.stderr,
        )
        return 1
    exempt = ", ".join(sorted(EXEMPT)) or "none"
    print(f"OK: every stub method in {len(STUB_MODULES)} modules raises. Exempt: {exempt}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
