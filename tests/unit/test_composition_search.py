"""Composition-root tests for v2-S4 candidate-search wiring (`build_candidate_search`,
`Kernel.candidate_search`)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from sagiha.adapters.search.best_of_n import BestOfNSearch
from sagiha.composition import build_candidate_search, build_kernel
from sagiha.domain.config import Config, ModelConfig, SandboxConfig, SearchConfig, WorkspaceConfig


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    (repo / "a.txt").write_text("x")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


def test_build_candidate_search_returns_none_when_search_disabled(tmp_path: Path) -> None:
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(tmp_path)),
        search=SearchConfig(enabled=False),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    assert build_candidate_search(config) is None


def test_build_candidate_search_returns_best_of_n_when_enabled(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(repo)),
        search=SearchConfig(enabled=True),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    search = build_candidate_search(config)
    assert isinstance(search, BestOfNSearch)


def test_build_candidate_search_max_concurrent_bounded_by_tier_capacity(tmp_path: Path) -> None:
    """A single-threaded local tier (`max_concurrent_requests=1`) must cap parallel launches at
    1 regardless of `governor.max_concurrent_sandboxes` — launching more parallel candidates
    than the model tier can serve gets one candidate repeated, not more candidates."""
    repo = _init_repo(tmp_path)
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(repo)),
        search=SearchConfig(enabled=True, launch_mode="parallel"),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    search = build_candidate_search(config)
    assert isinstance(search, BestOfNSearch)
    assert search._max_concurrent == 1  # type: ignore[attr-defined]


def _empty_cassette(tmp_path: Path) -> str:
    cassette = tmp_path / "cassette.json"
    cassette.write_text("[]")
    return str(cassette)


def test_build_kernel_wires_candidate_search_when_enabled(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(repo)),
        search=SearchConfig(enabled=True),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    kernel = build_kernel(config, cassette_path=_empty_cassette(tmp_path))
    assert kernel.candidate_search is not None
    assert kernel.worktree_manager is not None


def test_build_kernel_candidate_search_none_when_search_disabled(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(repo)),
        search=SearchConfig(enabled=False),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    kernel = build_kernel(config, cassette_path=_empty_cassette(tmp_path))
    assert kernel.candidate_search is None


def test_build_kernel_include_search_false_skips_candidate_search_even_when_enabled(
    tmp_path: Path,
) -> None:
    """Defect #7 (sprint_v2_s4_fixes.md): `KernelCandidateExecutor.execute` calls `build_kernel`
    once per Best-of-N candidate. Without `include_search=False`, every one of those per-candidate
    kernels would recursively build its own `BestOfNSearch` (and `GitWorktreeManager`) it can
    never use, purely from `search.enabled=True` still being set on the copied config."""
    repo = _init_repo(tmp_path)
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(repo)),
        search=SearchConfig(enabled=True),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    kernel = build_kernel(config, cassette_path=_empty_cassette(tmp_path), include_search=False)
    assert kernel.candidate_search is None
