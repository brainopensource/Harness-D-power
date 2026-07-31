"""H3 proving tests: Block-5 stubs fail loud instead of fabricating success.

INVERTED from the original scaffolding suite, which asserted the lies. It pinned
`sandbox.run(...).exit_code == 0` and `invoke_tool(...) == ""` as *correct behaviour* —
so the stubs were not merely wrong, they were regression-protected.

`ContainerSandbox.apply_edit` returned `EditResult(applied=True, syntax_valid=True)`
without touching anything. Anything that mounted it — a benchmark run, a gate — would
have recorded a successful edit that never happened. A stub that lies is worse than an
absent adapter, because an absent adapter fails at composition where you can see it.

These tests still pin that the files and methods EXIST, which is what the original
suite was protecting and is still worth protecting: placement is correct, only the
bodies are missing.
"""

from __future__ import annotations

import pytest

from sagiha.adapters.mcp.driver import MCPClientDriver
from sagiha.adapters.sandbox.container import ContainerSandbox
from sagiha.adapters.telemetry.otel import OTelEventObserver
from sagiha.domain.events import Event
from sagiha.domain.work import Edit, EditRequest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("read", ("some/path",)),
        ("write", ("some/path", "content")),
        ("run", (["echo", "hello"],)),
        ("checkpoint", ("label",)),
        ("restore", ("deadbeef",)),
    ],
)
async def test_container_sandbox_methods_raise(method: str, args: tuple[object, ...]) -> None:
    sandbox = ContainerSandbox()
    with pytest.raises(NotImplementedError, match="v2-S5"):
        await getattr(sandbox, method)(*args)


@pytest.mark.asyncio
async def test_container_sandbox_apply_edit_does_not_fabricate_a_successful_edit() -> None:
    """The worst of the three: it reported a landed edit for a file it never opened."""
    sandbox = ContainerSandbox()
    request = EditRequest(path="mod.py", edits=(Edit(old_string="a", new_string="b"),))
    with pytest.raises(NotImplementedError, match="v2-S5"):
        await sandbox.apply_edit(request)


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
