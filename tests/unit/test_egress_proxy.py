"""Unit tests for the CONNECT allowlist egress proxy (no Podman required)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from sagiha.adapters.sandbox.egress import EgressProxy


@pytest.mark.asyncio
async def test_egress_proxy_denies_and_allows(tmp_path: Path) -> None:
    sock = tmp_path / "egress.sock"
    proxy = EgressProxy(["pypi.org"], sock)
    await proxy.start()
    try:
        # Denied host
        reader, writer = await asyncio.open_unix_connection(str(sock))
        writer.write(b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n")
        await writer.drain()
        resp = await reader.read(256)
        assert b"403" in resp
        writer.close()
        await writer.wait_closed()
        assert any(d.startswith("example.com:") for d in proxy.denied)

        # Allowed host — may 200 or 502 depending on network; must not be 403.
        reader, writer = await asyncio.open_unix_connection(str(sock))
        writer.write(b"CONNECT pypi.org:443 HTTP/1.1\r\nHost: pypi.org:443\r\n\r\n")
        await writer.drain()
        resp = await reader.read(256)
        assert b"403" not in resp
        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


def test_secret_materialize_paths_filters_env() -> None:
    from sagiha.adapters.sandbox.container import secret_materialize_paths

    assert secret_materialize_paths([".env", ".venv", "node_modules"]) == [".venv", "node_modules"]
