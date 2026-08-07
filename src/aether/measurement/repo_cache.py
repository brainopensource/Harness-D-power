"""Manifest-Driven Upstream Repository Cache (TASK-010, Blocker B1).

Standalone utility resolving base commits for repositories named by pinned manifests.
Content-addressed, offline-replayable, zero hard-coded repo lists.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "aether" / "repo_cache"

SUITE_ALIASES = {
    "swe-ver": Path("docs/benchmarks/swe_verified_sample.md"),
    "swe-pro": Path("docs/benchmarks/swe_pro_sample.md"),
}


class TaskTarget(NamedTuple):
    task_id: str
    repo: str
    base_commit: str


def parse_manifest(manifest_path: Path) -> list[TaskTarget]:
    """Extract (task_id, repo, base_commit) targets from Markdown or JSON manifests."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    content = manifest_path.read_text(encoding="utf-8")
    targets: list[TaskTarget] = []

    # Try markdown table / spec parsing
    # Table format: | Index | Difficulty | Task ID | Repository | GitHub Issue URL | Base Commit SHA | ...
    table_rows = re.findall(
        r"\|\s*\d+\s*\|\s*.*?\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*.*?\|\s*`([^`]+)`",
        content,
    )
    if table_rows:
        for task_id, repo, commit_prefix in table_rows:
            # Match task section header and extract its Base Commit
            pattern = rf"### Task \d+:\s*`{re.escape(task_id)}`[\s\S]*?\* \*\*Base Commit\*\*: `([a-f0-9]+)`"
            commit_match = re.search(pattern, content)
            full_commit = commit_match.group(1) if commit_match else commit_prefix
            targets.append(TaskTarget(task_id=task_id, repo=repo, base_commit=full_commit))
        return targets

    # Try JSON manifest format
    if manifest_path.suffix == ".json":
        import json

        data = json.loads(content)
        tasks = data.get("tasks", [])
        for t in tasks:
            targets.append(
                TaskTarget(
                    task_id=t.get("task_id", ""),
                    repo=t.get("repo", ""),
                    base_commit=t.get("base_commit", ""),
                )
            )
        return targets

    raise ValueError(f"Could not parse task targets from manifest: {manifest_path}")


class RepoCache:
    """Content-addressed local repository cache for benchmark tasks."""

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR) -> None:
        self.cache_dir = cache_dir

    def get_repo_dir(self, repo: str) -> Path:
        """Sanitized local path for a git repository."""
        safe_name = repo.replace("/", "__")
        return self.cache_dir / safe_name

    def is_commit_present(self, repo_dir: Path, commit: str) -> bool:
        """Check if commit exists in local repo without network access."""
        if not repo_dir.exists():
            return False
        res = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=repo_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0

    def resolve_task(self, target: TaskTarget, dry_run: bool = False) -> bool:
        """Fetch repo and ensure target base_commit is locally available."""
        repo_dir = self.get_repo_dir(target.repo)
        
        if dry_run:
            status = "CACHED" if self.is_commit_present(repo_dir, target.base_commit) else "PENDING_DOWNLOAD"
            print(f"  [{status}] Task `{target.task_id}` -> repo `{target.repo}` @ `{target.base_commit[:10]}`")
            return True

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not repo_dir.exists():
            print(f"Cloning upstream repo `{target.repo}` into `{repo_dir}`...")
            url = f"https://github.com/{target.repo}.git"
            res = subprocess.run(["git", "clone", "--bare", url, str(repo_dir)])
            if res.returncode != 0:
                print(f"Error cloning `{target.repo}`", file=sys.stderr)
                return False

        if not self.is_commit_present(repo_dir, target.base_commit):
            print(f"Fetching commit `{target.base_commit[:10]}` for `{target.repo}`...")
            res = subprocess.run(
                ["git", "fetch", "origin", target.base_commit],
                cwd=repo_dir,
            )
            if res.returncode != 0:
                print(f"Error fetching commit `{target.base_commit}` in `{repo_dir}`", file=sys.stderr)
                return False

        return True

    def resolve_manifest(self, manifest_path: Path, dry_run: bool = False) -> dict[str, int]:
        """Resolve base commits for all tasks in a manifest."""
        targets = parse_manifest(manifest_path)
        unique_repos = set(t.repo for t in targets)

        print(f"Manifest: {manifest_path}")
        print(f"Total Tasks: {len(targets)} | Unique Repositories: {len(unique_repos)}")
        print(f"Cache Location: {self.cache_dir}")
        print(f"Mode: {'DRY RUN (No network/disk changes)' if dry_run else 'ACTIVE RESOLUTION'}\n")

        success_count = 0
        for t in targets:
            ok = self.resolve_task(t, dry_run=dry_run)
            if ok:
                success_count += 1

        print(f"\nResolution Summary: {success_count}/{len(targets)} tasks resolved successfully.")
        return {"total": len(targets), "resolved": success_count, "repos": len(unique_repos)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manifest-driven repository cache (TASK-010)")
    parser.add_argument(
        "--suite",
        choices=["swe-ver", "swe-pro"],
        help="Predefined suite alias ('swe-ver' or 'swe-pro')",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to custom manifest Markdown or JSON file",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help=f"Local cache directory (default: {DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check and display targets without cloning or fetching",
    )

    args = parser.parse_args(argv)

    if args.suite:
        manifest_path = SUITE_ALIASES[args.suite]
    elif args.manifest:
        manifest_path = args.manifest
    else:
        parser.error("Must specify either --suite (swe-ver|swe-pro) or --manifest <path>")

    cache = RepoCache(cache_dir=args.cache_dir)
    res = cache.resolve_manifest(manifest_path, dry_run=args.dry_run)
    return 0 if res["resolved"] == res["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
