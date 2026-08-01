"""Materialize an imported benchmark task's upstream repository at its base commit.

The E0 runner allocates every task's worktree with `git worktree add <base_commit>`
against the harness repository. That is correct for a *harvested* suite, whose
tasks are commits of this repo — and wrong for an *imported* one, whose base
commits live in other projects entirely. Running `s0-core` (SWE-bench Lite, 12
upstream repos) without this produced 30 × `fatal: invalid reference`, which is
an infrastructure failure that reads exactly like 30 unsolved tasks.

Fetching is per-commit and shallow (`--depth 1 origin <sha>`), so a task costs
roughly a second and under a megabyte rather than a full clone of Django or
SymPy. Clones are bare-ish: `git init` plus a remote, never a checkout — the
runner's worktrees are the only working trees.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".sagiha") / "repo-cache"


class RepoCacheError(RuntimeError):
    """Raised when an upstream repository or commit could not be materialized."""


def _run(args: list[str], cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def commit_present(repo_root: Path, commit: str) -> bool:
    """Whether `commit` is already an object in the repo at `repo_root`."""
    probe = _run(["git", "cat-file", "-t", commit], repo_root, timeout=60)
    return probe.returncode == 0 and probe.stdout.strip() == "commit"


def cache_path(repo: str, cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    """Local clone location for an upstream `owner/name`."""
    return cache_dir / repo.replace("/", "__")


def ensure_repo(
    repo: str,
    base_commit: str,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    remote_template: str = "https://github.com/{repo}.git",
) -> Path:
    """Return a local git repo that contains `base_commit`, fetching if needed.

    Idempotent: a commit already present is not re-fetched, so a repeated bench
    run (an A/A pass, say) pays the network cost once.
    """
    root = cache_path(repo, cache_dir)
    if root.exists() and commit_present(root, base_commit):
        return root

    root.mkdir(parents=True, exist_ok=True)
    if not (root / ".git").exists():
        init = _run(["git", "init", "-q", "."], root)
        if init.returncode != 0:
            raise RepoCacheError(f"git init failed for {repo}: {init.stderr.strip()}")
        remote = remote_template.format(repo=repo)
        add = _run(["git", "remote", "add", "origin", remote], root)
        if add.returncode != 0 and "already exists" not in add.stderr:
            raise RepoCacheError(f"git remote add failed for {repo}: {add.stderr.strip()}")

    logger.info("repo-cache: fetching %s@%s", repo, base_commit[:10])
    fetch = _run(["git", "fetch", "--depth", "1", "-q", "origin", base_commit], root)
    if fetch.returncode != 0 or not commit_present(root, base_commit):
        raise RepoCacheError(
            f"could not fetch {repo}@{base_commit}: {fetch.stderr.strip() or 'commit not present after fetch'}"
        )
    return root


def resolve_task_root(
    repo: str,
    base_commit: str,
    *,
    workspace_root: str | Path,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Path:
    """Pick the repository a task's worktree should be cut from.

    A harvested task's base commit is in the harness repo and is used directly —
    so the local-suite path is unchanged and pays no network cost. Anything else
    is an imported task and comes from the cache.
    """
    local = Path(workspace_root)
    if commit_present(local, base_commit):
        return local
    return ensure_repo(repo, base_commit, cache_dir=cache_dir)
