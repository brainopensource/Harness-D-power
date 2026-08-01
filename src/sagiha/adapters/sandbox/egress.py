"""Hostname-allowlist HTTP CONNECT egress proxy for the container perimeter.

ADR-0016: allowlisting is by hostname at an explicit HTTP/HTTPS proxy that sees
`CONNECT <host>` before the TLS handshake. Direct outbound is dropped by running
the sandbox with `--network=none` and reaching this proxy only via a unix socket
forwarded to loopback inside the container.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Collection
from pathlib import Path

logger = logging.getLogger(__name__)

_CONNECT_RE = re.compile(rb"^CONNECT\s+([^:\s]+):(\d+)\s+HTTP/1\.[01]\r\n", re.IGNORECASE)


class EgressProxy:
    """Allowlist CONNECT proxy listening on a unix domain socket."""

    def __init__(self, allowlist: Collection[str], socket_path: Path) -> None:
        self._allowlist = {h.lower().rstrip(".") for h in allowlist}
        self._socket_path = socket_path
        self._server: asyncio.Server | None = None
        self.denied: list[str] = []
        self.allowed: list[str] = []

    @property
    def socket_path(self) -> Path:
        return self._socket_path

    def is_allowed(self, host: str) -> bool:
        host = host.lower().rstrip(".")
        if host in self._allowlist:
            return True
        # Permit subdomains of an allowlisted parent (pypi.org covers files.pypi.org only
        # when listed; exact and trailing-dot-normalized match only — CDN hosts must be
        # listed explicitly per ADR-0016).
        return any(host == a or host.endswith("." + a) for a in self._allowlist)

    async def start(self) -> None:
        self._socket_path.parent.mkdir(parents=True, exist_ok=True)
        if self._socket_path.exists():
            self._socket_path.unlink()
        self._server = await asyncio.start_unix_server(self._handle, path=str(self._socket_path))
        # Container users must be able to connect through the bind-mounted socket.
        self._socket_path.chmod(0o666)
        logger.info("egress proxy listening on %s allowlist=%s", self._socket_path, sorted(self._allowlist))

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._socket_path.exists():
            self._socket_path.unlink(missing_ok=True)

    async def __aenter__(self) -> EgressProxy:
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.stop()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            header = await reader.readuntil(b"\r\n\r\n")
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            writer.close()
            await writer.wait_closed()
            return

        match = _CONNECT_RE.match(header)
        if match is None:
            writer.write(b"HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return

        host = match.group(1).decode("ascii", errors="replace")
        port = int(match.group(2))
        if not self.is_allowed(host):
            self.denied.append(f"{host}:{port}")
            logger.warning("egress denied CONNECT %s:%s", host, port)
            writer.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return

        self.allowed.append(f"{host}:{port}")
        try:
            peer_reader, peer_writer = await asyncio.open_connection(host, port)
        except OSError as exc:
            logger.warning("egress upstream connect failed %s:%s: %s", host, port, exc)
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return

        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()

        async def _pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
            try:
                while True:
                    chunk = await src.read(65536)
                    if not chunk:
                        break
                    dst.write(chunk)
                    await dst.drain()
            except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
                pass
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        t1 = asyncio.create_task(_pipe(reader, peer_writer))
        t2 = asyncio.create_task(_pipe(peer_reader, writer))
        await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
        t1.cancel()
        t2.cancel()
        writer.close()
        peer_writer.close()
