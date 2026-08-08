"""Named deviations from the pre-registered baseline (TASK-049b, measurement.md §4.1).

Scope discipline: `AblationFlags` only. The full `RunConfig` is `TASK-058`,
Sprint 5 — this module must not grow beyond this one type this sprint.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from aether.domain.budget import BudgetDims
from aether.domain.ids import Frozen


class AblationFlags(Frozen):
    """Every field defaults to the pre-registered baseline. A run that
    deviates says so in its own config hash, which is what makes it a
    declared *arm* rather than a contaminated run."""

    #: Baseline is `False`: "no retrieval beyond benchmark-provided context."
    #: `True` embeds the pinned test file's full text in the task prompt —
    #: measuring assertion-fitting, not bug-fixing (measurement.md §4.1).
    inject_test_source: bool = False


class ModelRoute(Frozen):
    role: str = ""
    base_url: str = ""
    model: str = ""
    api_key_env: str | None = None


class SandboxConfig(Frozen):
    runtime: str | None = None
    image_digest: str = ""


class RunConfig(Frozen):
    """One frozen parameter replacing 15 keyword arguments.

    `sha256(RunConfig)` IS `measurement.md` §6's instrument tuple.
    """

    topology_path: str
    manifest_hash: str = ""
    split: Literal["dev", "holdout", "sealed"] = "dev"
    mode: Literal["benchmark", "interactive"] = "benchmark"
    routes: tuple[ModelRoute, ...] = ()
    budget: BudgetDims = BudgetDims()
    sandbox: SandboxConfig = SandboxConfig()
    ablation: AblationFlags = AblationFlags()
    seed: int = 0
    repo_path: str = ""
    worktrees_root: str = ""
    trajectory_db_path: str = ":memory:"
    entry_files: tuple[str, ...] = ()
    test_command: str = ""


def config_hash(flags: AblationFlags) -> str:
    """Same convention as `measurement/manifest.py::canonical_json` — sorted
    keys, no whitespace, so the hash is reproducible across processes."""
    canonical = json.dumps(flags.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def instrument_hash(config: RunConfig, *, topology_hash: str = "", lockfile_hash: str = "") -> str:
    """Computes the instrument tuple hash for a RunConfig."""
    payload = config.model_dump(mode="json")
    payload["topology_hash"] = topology_hash
    payload["lockfile_hash"] = lockfile_hash
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


__all__ = [
    "AblationFlags",
    "ModelRoute",
    "RunConfig",
    "SandboxConfig",
    "config_hash",
    "instrument_hash",
]
