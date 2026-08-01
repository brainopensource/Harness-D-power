"""Generate ``AGENTS.md`` from toolchain sniff and repository layout."""

from __future__ import annotations

import re
from pathlib import Path

from anyio import Path as APath

from sagiha.adapters.indexer.walk import SKIP_DIRS
from sagiha.ports.code_graph import CodeGraph


async def generate_agents_md(root: Path, *, graph: CodeGraph | None, force: bool) -> Path:
    """Write ``AGENTS.md`` at ``root``; fail if it exists unless ``force``."""
    target = root / "AGENTS.md"
    if await APath(target).exists() and not force:
        raise FileExistsError(f"{target} already exists (pass --force to overwrite)")

    content = _render_agents_md(root, graph=graph)
    await APath(target).write_text(content, encoding="utf-8")
    return target


def _project_name(root: Path) -> str:
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r"""name\s*=\s*['"]([^'"]+)['"]""", text)
        if match:
            return match.group(1)
    return root.name


def _detect_toolchains(root: Path) -> list[str]:
    toolchains: list[str] = []
    if (root / "pyproject.toml").is_file():
        toolchains.append("Python (`pyproject.toml`)")
    if (root / "package.json").is_file():
        toolchains.append("Node.js (`package.json`)")
    if (root / "Cargo.toml").is_file():
        toolchains.append("Rust (`Cargo.toml`)")
    return toolchains or ["Unknown — no standard manifest detected"]


def _discover_python_modules(root: Path) -> list[str]:
    modules: list[str] = []
    for file_path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in file_path.parts):
            continue
        rel = file_path.relative_to(root).as_posix()
        if rel.endswith("__init__.py"):
            modules.append(rel[: -len("/__init__.py")].replace("/", "."))
        elif "/" not in rel:
            modules.append(rel[:-3])
    return sorted(set(modules))


def _layout_lines(root: Path) -> list[str]:
    lines: list[str] = []
    for name in ("src", "lib", "tests", "docs"):
        if (root / name).is_dir():
            lines.append(f"- `{name}/`")
    for child in sorted(root.iterdir()):
        if child.is_file() and child.suffix in {".py", ".toml", ".json", ".md"}:
            lines.append(f"- `{child.name}`")
    return lines or ["- (no top-level layout markers detected)"]


def _conventions(toolchains: list[str]) -> list[str]:
    lines = [
        "- Follow existing naming and import style in touched files.",
        "- Prefer small, focused diffs; do not modify test files unless the task requires it.",
    ]
    if any("Python" in item for item in toolchains):
        lines.extend(
            [
                "- Python runtime and tooling are declared in `pyproject.toml`.",
                "- Run `ruff format` and `ruff check` before committing.",
            ]
        )
    if any("Node.js" in item for item in toolchains):
        lines.append("- Node dependencies are declared in `package.json`.")
    if any("Rust" in item for item in toolchains):
        lines.append("- Rust crate metadata lives in `Cargo.toml`.")
    return lines


def _render_agents_md(root: Path, *, graph: CodeGraph | None) -> str:
    name = _project_name(root)
    toolchains = _detect_toolchains(root)
    modules = _discover_python_modules(root)

    sections = [
        "# AGENTS.md",
        "",
        "## Project",
        f"- Name: **{name}**",
        f"- Root: `{root.resolve().as_posix()}`",
        "",
        "## Toolchain",
        *[f"- {item}" for item in toolchains],
        "",
        "## Layout",
        *_layout_lines(root),
    ]

    if modules:
        sections.extend(
            [
                "",
                "## Modules",
                *[f"- `{module}`" for module in modules[:40]],
            ]
        )
        if len(modules) > 40:
            sections.append(f"- … and {len(modules) - 40} more")

    if graph is not None:
        sections.extend(
            [
                "",
                "## Code graph",
                "- Indexed structure is available for retrieval and code-intelligence tools.",
            ]
        )

    sections.extend(
        [
            "",
            "## Conventions",
            *_conventions(toolchains),
            "",
        ]
    )
    return "\n".join(sections)
