"""Unit tests for Block 5 scaffolding — sandbox, MCP, and telemetry adapters."""

from __future__ import annotations

import pytest

from sagiha.adapters.mcp.driver import MCPClientDriver
from sagiha.adapters.sandbox.container import ContainerSandbox
from sagiha.adapters.telemetry.otel import OTelEventObserver
from sagiha.domain.events import Event


@pytest.mark.asyncio
async def test_container_sandbox_placeholder() -> None:
    sandbox = ContainerSandbox()
    result = await sandbox.run(["echo", "hello"])
    assert result.exit_code == 0
    read_val = await sandbox.read("some/path")
    assert read_val == ""


@pytest.mark.asyncio
async def test_mcp_driver_placeholder() -> None:
    driver = MCPClientDriver()
    tools = await driver.list_tools()
    assert tools == []
    output = await driver.invoke_tool("server", "tool", {})
    assert output == ""


@pytest.mark.asyncio
async def test_otel_observer_placeholder() -> None:
    observer = OTelEventObserver()
    event = Event(event="test.event", run_id="run-1")
    await observer.on_event(event)
