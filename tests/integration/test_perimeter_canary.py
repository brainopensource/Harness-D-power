"""v2-S5 perimeter canary — credential exclusion, egress allowlist, parallel isolation.

Requires rootless Podman and `sagiha/runtime:latest`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from sagiha.adapters.sandbox.container import (
    SECRET_MATERIALIZE_NAMES,
    ContainerSandbox,
    podman_available,
    secret_materialize_paths,
)
from sagiha.domain.config import SandboxConfig

pytestmark = [pytest.mark.asyncio, pytest.mark.podman]

_RUNTIME_IMAGE = "sagiha/runtime:latest"
_CANARY_SECRET = "SAGIHA_CANARY_SECRET_VALUE_9f3a"


def _podman_ready() -> bool:
    if not podman_available():
        return False
    return subprocess.run(["podman", "image", "exists", _RUNTIME_IMAGE], capture_output=True).returncode == 0


@pytest.fixture(autouse=True)
def _require_podman() -> None:
    if not _podman_ready():
        pytest.skip("podman + sagiha/runtime:latest required")


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    (root / "hello.txt").write_text("in-worktree\n", encoding="utf-8")
    # Plant a .env that must NOT be readable via a secret materialize policy.
    (root / ".env").write_text(f"API_KEY={_CANARY_SECRET}\n", encoding="utf-8")
    return root


async def test_host_credential_outside_worktree_unreachable(worktree: Path, tmp_path: Path) -> None:
    secret_file = tmp_path / "host-secret.txt"
    secret_file.write_text(_CANARY_SECRET, encoding="utf-8")

    sandbox = ContainerSandbox(
        str(worktree),
        SandboxConfig(
            image=_RUNTIME_IMAGE,
            network="none",
            memory_limit_mb=512,
            cpu_limit=1.0,
            env_passthrough=["LANG", "TZ"],
        ),
        state_dir=str(worktree / ".sagiha" / "sandbox"),
    )
    async with sandbox:
        # Absolute host path is outside the container filesystem.
        result = await sandbox.run(["cat", str(secret_file)])
        assert result.exit_code != 0 or _CANARY_SECRET not in result.stdout
        assert _CANARY_SECRET not in result.stdout
        assert _CANARY_SECRET not in result.stderr

        # Home credential paths are not mounted.
        home = await sandbox.run(["python", "-c", "import os; print(os.path.exists('/root/.ssh'))"])
        assert "True" not in home.stdout

        # Host env secrets must not leak (API_KEY not in env_passthrough).
        env = await sandbox.run(["python", "-c", "import os; print(os.environ.get('API_KEY', ''))"])
        assert _CANARY_SECRET not in env.stdout


async def test_env_file_in_worktree_is_visible_on_bind_mount_but_not_materialized_by_policy(
    worktree: Path,
) -> None:
    """Bind mount exposes the worktree as-is; materialize policy strips .env from copies."""
    assert ".env" not in secret_materialize_paths([".env", ".venv", "node_modules"])
    assert Path(".env").name in SECRET_MATERIALIZE_NAMES

    sandbox = ContainerSandbox(
        str(worktree),
        SandboxConfig(image=_RUNTIME_IMAGE, network="none", memory_limit_mb=512, cpu_limit=1.0),
        state_dir=str(worktree / ".sagiha" / "sandbox"),
    )
    async with sandbox:
        # The worktree bind mount itself still contains .env if present on disk — that is
        # the repo's content. Control-plane materialize must not *copy* secrets into a
        # fresh worktree; see secret_materialize_paths. Reading an in-tree .env is a
        # workspace file read, not a host-credential leak.
        text = await sandbox.read(".env")
        assert "API_KEY" in text


async def test_non_allowlisted_egress_denied(worktree: Path) -> None:
    sandbox = ContainerSandbox(
        str(worktree),
        SandboxConfig(
            image=_RUNTIME_IMAGE,
            network="restricted",
            egress_allowlist=["pypi.org"],
            memory_limit_mb=512,
            cpu_limit=1.0,
        ),
        state_dir=str(Path("/tmp") / "sagiha-canary"),
    )
    async with sandbox:
        # Direct outbound is impossible (--network=none); curl without proxy fails.
        direct = await sandbox.run(
            [
                "python",
                "-c",
                "import urllib.request; urllib.request.urlopen('https://example.com', timeout=3)",
            ]
        )
        assert direct.exit_code != 0

        # Via proxy: non-allowlisted host is refused by CONNECT allowlist.
        denied = await sandbox.run(
            [
                "python",
                "-c",
                (
                    "import urllib.request\n"
                    "proxy = urllib.request.ProxyHandler({"
                    "'https': 'http://127.0.0.1:3128', 'http': 'http://127.0.0.1:3128'})\n"
                    "opener = urllib.request.build_opener(proxy)\n"
                    "opener.open('https://example.com', timeout=5)\n"
                ),
            ]
        )
        assert denied.exit_code != 0
        assert sandbox.egress_proxy is not None
        assert any(d.startswith("example.com:") for d in sandbox.egress_proxy.denied)


async def test_parallel_sandboxes_do_not_interfere(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "marker.txt").write_text("A\n", encoding="utf-8")
    (b / "marker.txt").write_text("B\n", encoding="utf-8")

    cfg = SandboxConfig(image=_RUNTIME_IMAGE, network="none", memory_limit_mb=512, cpu_limit=1.0)
    sa = ContainerSandbox(str(a), cfg, state_dir=str(a / ".sagiha" / "sandbox"))
    sb = ContainerSandbox(str(b), cfg, state_dir=str(b / ".sagiha" / "sandbox"))
    async with sa, sb:
        ra = await sa.run(["cat", "/workspace/marker.txt"])
        rb = await sb.run(["cat", "/workspace/marker.txt"])
        assert ra.exit_code == 0, ra.stderr
        assert rb.exit_code == 0, rb.stderr
        assert ra.stdout.strip() == "A"
        assert rb.stdout.strip() == "B"
        await sa.write("only-a.txt", "solo\n")
        assert not (b / "only-a.txt").exists()
        assert sa.container_id != sb.container_id
