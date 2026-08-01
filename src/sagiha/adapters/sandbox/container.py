"""Rootless Podman ContainerSandbox — the security perimeter (ADR-0006, ADR-0016).

File I/O runs on the host side of the worktree bind mount (same semantics as
LocalWorkspace, including .py syntax checks). Command execution always goes through
`podman exec` so the network and credential perimeter holds.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
import uuid
from pathlib import Path

from sagiha.adapters.sandbox.egress import EgressProxy
from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.domain.config import SandboxConfig
from sagiha.domain.content import CommandResult
from sagiha.domain.work import EditRequest, EditResult

logger = logging.getLogger(__name__)

CONTAINER_WORKSPACE = "/workspace"
EGRESS_SOCK_IN_CONTAINER = "/run/sagiha/egress.sock"
EGRESS_FORWARD_PORT = 3128

# Paths that must never be bind-mounted or materialized into a container worktree.
SECRET_MATERIALIZE_NAMES = frozenset({".env", ".env.local", ".env.production", ".netrc", ".npmrc"})

_FORWARDER_SCRIPT = f"""\
import asyncio, os, socket, sys
SOCK = {EGRESS_SOCK_IN_CONTAINER!r}
PORT = {EGRESS_FORWARD_PORT}

async def pipe(r, w):
    try:
        while True:
            data = await r.read(65536)
            if not data:
                break
            w.write(data)
            await w.drain()
    except Exception:
        pass
    finally:
        try:
            w.close()
        except Exception:
            pass

async def handle(reader, writer):
    try:
        up_r, up_w = await asyncio.open_unix_connection(SOCK)
    except OSError as e:
        writer.close()
        return
    await asyncio.gather(pipe(reader, up_w), pipe(up_r, writer))

async def main():
    # Wait briefly for the bind-mounted socket to appear.
    for _ in range(50):
        if os.path.exists(SOCK):
            break
        await asyncio.sleep(0.05)
    server = await asyncio.start_server(handle, "127.0.0.1", PORT)
    async with server:
        await server.serve_forever()

asyncio.run(main())
"""


def podman_available() -> bool:
    return shutil.which("podman") is not None


def secret_materialize_paths(paths: list[str]) -> list[str]:
    """Filter materialize paths that would leak credentials into a container."""
    return [p for p in paths if Path(p).name not in SECRET_MATERIALIZE_NAMES]


class ContainerSandbox:
    """Rootless Podman container perimeter implementation of Workspace."""

    def __init__(
        self,
        worktree_root: str,
        sandbox: SandboxConfig | None = None,
        *,
        state_dir: str | None = None,
        ro_mounts: list[tuple[str, str]] | None = None,
    ) -> None:
        self._sandbox = sandbox or SandboxConfig()
        self._host_root = Path(worktree_root).resolve()
        self._files = LocalWorkspace(str(self._host_root))
        # Keep egress socket paths short — AF_UNIX has a ~108-byte path limit; pytest
        # tmp_path trees routinely exceed it.
        self._state_dir = Path(state_dir) if state_dir else Path("/tmp") / "sagiha-sandbox"
        self._ro_mounts = ro_mounts or []
        self._container_id: str | None = None
        self._name = f"sagiha-{uuid.uuid4().hex[:12]}"
        self._proxy: EgressProxy | None = None
        self._started = False
        self._lock = asyncio.Lock()

    @property
    def root(self) -> Path:
        """Host path of the bind-mounted worktree (concrete-adapter helper for builtins)."""
        return self._host_root

    @property
    def container_id(self) -> str | None:
        return self._container_id

    @property
    def egress_proxy(self) -> EgressProxy | None:
        return self._proxy

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
            await self._start_unlocked()

    async def _start_unlocked(self) -> None:
        if not podman_available():
            raise RuntimeError(
                "sandbox.runtime='container' requires rootless Podman on PATH "
                "(ADR-0016). Install podman or set sandbox.runtime='subprocess' for "
                "interactive local development only."
            )

        self._state_dir.mkdir(parents=True, exist_ok=True)
        # Short path under /tmp — never nest under pytest's deep tmp_path.
        sock_path = Path("/tmp") / f"{self._name}.sock"

        network_args: list[str] = []
        env_args: list[str] = [
            # Bind mounts look like a filesystem boundary to git; without this,
            # `git rev-parse` fails inside the container even when .git is mounted.
            "--env",
            "GIT_DISCOVERY_ACROSS_FILESYSTEM=1",
        ]
        volume_args: list[str] = [
            "--volume",
            # `:Z` private SELinux relabel — required on enforcing hosts (Fedora); ignored elsewhere.
            f"{self._host_root}:{CONTAINER_WORKSPACE}:rw,Z",
        ]
        for host_path, container_path in self._ro_mounts:
            volume_args.extend(["--volume", f"{host_path}:{container_path}:ro,Z"])

        # Scrubbed environment — never inherit host secrets.
        for key in self._sandbox.env_passthrough:
            val = os.environ.get(key)
            if val is not None:
                env_args.extend(["--env", f"{key}={val}"])

        if self._sandbox.network == "none":
            network_args = ["--network=none"]
        elif self._sandbox.network == "restricted":
            # No host network stack: direct outbound is impossible. Egress is only via
            # the unix-socket CONNECT proxy (hostname allowlist) forwarded to loopback.
            network_args = ["--network=none"]
            self._proxy = EgressProxy(self._sandbox.egress_allowlist, sock_path)
            await self._proxy.start()
            # Unix socket mount: do NOT use :Z — relabeling the socket inode breaks the
            # host-side listener's ability to accept connections from the forwarder.
            volume_args.extend(["--volume", f"{sock_path}:{EGRESS_SOCK_IN_CONTAINER}:rw"])
            proxy_url = f"http://127.0.0.1:{EGRESS_FORWARD_PORT}"
            env_args.extend(
                [
                    "--env",
                    f"HTTP_PROXY={proxy_url}",
                    "--env",
                    f"HTTPS_PROXY={proxy_url}",
                    "--env",
                    f"http_proxy={proxy_url}",
                    "--env",
                    f"https_proxy={proxy_url}",
                    "--env",
                    "NO_PROXY=",
                    "--env",
                    "no_proxy=",
                ]
            )
        elif self._sandbox.network == "host":
            network_args = ["--network=host"]
        else:
            raise RuntimeError(f"unknown sandbox.network={self._sandbox.network!r}")

        memory = f"{self._sandbox.memory_limit_mb}m"
        cpus = str(self._sandbox.cpu_limit)

        create_cmd = [
            "podman",
            "create",
            "--name",
            self._name,
            "--replace",
            "--userns=keep-id",
            # Rootless bind mounts + unix-socket egress need this on SELinux-enforcing
            # hosts; user namespaces, network=none, and mount policy remain the perimeter.
            "--security-opt",
            "label=disable",
            "--memory",
            memory,
            "--cpus",
            cpus,
            "--workdir",
            CONTAINER_WORKSPACE,
            *network_args,
            *volume_args,
            *env_args,
            # Do not pass host env; do not mount home.
            "--tz=local",
            self._sandbox.image,
        ]

        proc = await asyncio.create_subprocess_exec(
            *create_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await proc.communicate()
        if proc.returncode != 0:
            await self._cleanup_proxy()
            raise RuntimeError(
                f"podman create failed (image={self._sandbox.image!r}): "
                f"{stderr_b.decode(errors='replace').strip()}"
            )
        self._container_id = stdout_b.decode().strip() or self._name

        start = await asyncio.create_subprocess_exec(
            "podman",
            "start",
            self._container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, start_err = await start.communicate()
        if start.returncode != 0:
            await self.aclose()
            raise RuntimeError(f"podman start failed: {start_err.decode(errors='replace').strip()}")

        if self._proxy is not None:
            await self._start_egress_forwarder()
            # Confirm the forwarder accepted a connection before returning.
            for _ in range(20):
                probe = await asyncio.create_subprocess_exec(
                    "podman",
                    "exec",
                    self._container_id,
                    "python",
                    "-c",
                    ("import socket; s=socket.create_connection(('127.0.0.1', 3128), 1); s.close()"),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await probe.wait()
                if probe.returncode == 0:
                    break
                await asyncio.sleep(0.1)

        self._started = True
        logger.info("ContainerSandbox started name=%s id=%s", self._name, self._container_id)

    async def _start_egress_forwarder(self) -> None:
        """Bridge 127.0.0.1:3128 inside the container to the host unix-socket proxy."""
        assert self._container_id is not None
        proc = await asyncio.create_subprocess_exec(
            "podman",
            "exec",
            "-d",
            self._container_id,
            "python",
            "-c",
            _FORWARDER_SCRIPT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"failed to start egress forwarder: {err.decode(errors='replace').strip()}")
        # Give the forwarder a moment to bind.
        await asyncio.sleep(0.15)

    async def _ensure_started(self) -> None:
        if not self._started:
            await self.start()

    async def _cleanup_proxy(self) -> None:
        if self._proxy is not None:
            await self._proxy.stop()
            self._proxy = None

    async def aclose(self) -> None:
        async with self._lock:
            cid = self._container_id
            self._container_id = None
            self._started = False
            if cid is not None:
                proc = await asyncio.create_subprocess_exec(
                    "podman",
                    "rm",
                    "-f",
                    cid,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            await self._cleanup_proxy()

    async def __aenter__(self) -> ContainerSandbox:
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def read(self, path: str, offset: int = 0, limit: int | None = None) -> str:
        await self._ensure_started()
        return await self._files.read(path, offset=offset, limit=limit)

    async def write(self, path: str, content: str) -> None:
        await self._ensure_started()
        await self._files.write(path, content)

    async def apply_edit(self, request: EditRequest) -> EditResult:
        await self._ensure_started()
        return await self._files.apply_edit(request)

    async def run(self, command: list[str]) -> CommandResult:
        await self._ensure_started()
        assert self._container_id is not None
        if not command:
            raise ValueError("command must be a non-empty argv list")
        start = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            "podman",
            "exec",
            "-w",
            CONTAINER_WORKSPACE,
            self._container_id,
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await proc.communicate()
        duration_ms = (time.monotonic() - start) * 1000.0
        return CommandResult(
            exit_code=proc.returncode or 0,
            stdout=stdout_b.decode("utf-8", errors="replace"),
            stderr=stderr_b.decode("utf-8", errors="replace"),
            duration_ms=duration_ms,
        )

    async def checkpoint(self, label: str) -> str:
        result = await self.run(["git", "rev-parse", "HEAD"])
        if result.exit_code != 0:
            raise RuntimeError(
                f"checkpoint({label!r}) failed: workspace at {self.root} is not a git "
                f"repository or has no commits — {result.stderr.strip()}"
            )
        return result.stdout.strip()

    async def restore(self, commit_sha: str) -> None:
        result = await self.run(["git", "reset", "--hard", commit_sha])
        if result.exit_code != 0:
            raise RuntimeError(f"restore({commit_sha!r}) failed at {self.root}: {result.stderr.strip()}")
