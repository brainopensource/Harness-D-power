"""H3 proving tests: remaining Block-5 stubs fail loud instead of fabricating success.

`ContainerSandbox` became real in v2-S5 — its loud-stub assertions moved to the Workspace
conformance suite. MCP and OTel remain stubs until v2-S7.
"""

from __future__ import annotations

import pytest

from sagiha.adapters.mcp.driver import MCPClientDriver
from sagiha.adapters.telemetry.otel import OTelEventObserver
from sagiha.domain.events import Event


@pytest.mark.asyncio
async def test_mcp_invoke_tool_raises() -> None:
    driver = MCPClientDriver()
    with pytest.raises(NotImplementedError, match="v2-S7"):
        await driver.invoke_tool("server", "tool", {})


@pytest.mark.asyncio
async def test_mcp_list_tools_may_return_empty() -> None:
    """The one permitted exception: empty discovery is a truthful null.

    No servers are configured, so no tools exist. That is a real answer, unlike
    `invoke_tool` returning "" for a call that never happened.
    """
    assert await MCPClientDriver().list_tools() == []


@pytest.mark.asyncio
async def test_otel_observer_raises() -> None:
    observer = OTelEventObserver()
    with pytest.raises(NotImplementedError, match="v2-S7"):
        await observer.on_event(Event(event="test.event", run_id="run-1"))
