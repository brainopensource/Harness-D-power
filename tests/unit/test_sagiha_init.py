"""Unit tests for `sagiha init` and AGENTS.md generation."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sagiha.agency.context.system_prompt import resolve_system_prompt
from sagiha.agency.run_loop import DEFAULT_SYSTEM_PROMPT
from sagiha.cli import app

runner = CliRunner()


@pytest.mark.asyncio
async def test_init_writes_agents_md(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "demo.py").write_text("def main():\n    pass\n", encoding="utf-8")
    from sagiha.outer_loop.init.generate import generate_agents_md

    path = await generate_agents_md(tmp_path, graph=None, force=False)
    text = path.read_text(encoding="utf-8")
    assert path.name == "AGENTS.md"
    assert "Python" in text or "demo" in text.lower()
    assert "## Project" in text
    assert "## Toolchain" in text
    assert "## Layout" in text
    assert "## Conventions" in text


@pytest.mark.asyncio
async def test_init_refuses_overwrite_without_force(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# existing\n", encoding="utf-8")
    from sagiha.outer_loop.init.generate import generate_agents_md

    with pytest.raises(FileExistsError, match="already exists"):
        await generate_agents_md(tmp_path, graph=None, force=False)


@pytest.mark.asyncio
async def test_init_force_overwrites(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# old\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    from sagiha.outer_loop.init.generate import generate_agents_md

    path = await generate_agents_md(tmp_path, graph=None, force=True)
    text = path.read_text(encoding="utf-8")
    assert "## Project" in text
    assert "# old" not in text


def test_cli_init_writes_agents_md(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    result = runner.invoke(app, ["init", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "AGENTS.md").is_file()
    assert "Wrote" in result.output


def test_cli_init_refuses_existing(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# existing\n", encoding="utf-8")
    result = runner.invoke(app, ["init", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    assert "already exists" in result.output


@pytest.mark.asyncio
async def test_resolve_system_prompt_absent_is_byte_stable(tmp_path: Path) -> None:
    prompt = await resolve_system_prompt(tmp_path)
    assert prompt == DEFAULT_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_resolve_system_prompt_loads_agents_md(tmp_path: Path) -> None:
    agents = "# Project rules\nUse ruff.\n"
    (tmp_path / "AGENTS.md").write_text(agents, encoding="utf-8")
    prompt = await resolve_system_prompt(tmp_path)
    assert prompt.startswith(DEFAULT_SYSTEM_PROMPT)
    assert agents.strip() in prompt
