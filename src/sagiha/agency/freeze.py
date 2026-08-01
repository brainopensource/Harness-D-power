"""Persist and load `FrozenRunState` without bumping `TrajectoryStore`.

Freeze files live under `{workspace_root}/.sagiha/freeze/{run_id}.json` so a kill-9
restart can find them next to the work the run was doing. The trajectory itself stays
in `TrajectoryStore`; this file is only the grants-absent control snapshot.
"""

from __future__ import annotations

from pathlib import Path

from sagiha.domain.control import FrozenRunState


def freeze_dir(workspace_root: str | Path) -> Path:
    return Path(workspace_root) / ".sagiha" / "freeze"


def freeze_path(workspace_root: str | Path, run_id: str) -> Path:
    return freeze_dir(workspace_root) / f"{run_id}.json"


def persist_freeze(state: FrozenRunState) -> Path:
    path = freeze_path(state.workspace_root, state.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(), encoding="utf-8")
    return path


def load_freeze(workspace_root: str | Path, run_id: str) -> FrozenRunState:
    path = freeze_path(workspace_root, run_id)
    if not path.is_file():
        raise FileNotFoundError(f"no freeze file for run {run_id!r} at {path}")
    return FrozenRunState.model_validate_json(path.read_text(encoding="utf-8"))


def clear_freeze(workspace_root: str | Path, run_id: str) -> None:
    path = freeze_path(workspace_root, run_id)
    if path.is_file():
        path.unlink()
