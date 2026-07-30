"""MCP stdio/HTTP client driver adapter for Block 5.

See docs/05-tech-stack/mcp-integration-guide.md.

SENIOR TODO: stdio and SSE transport connection management, tool discovery mapping,
             `trusted_output=False` sanitization, server health checks.
"""

from __future__ import annotations

import logging
from typing import Any

from sagiha.domain.config import MCPServerConfig
from sagiha.domain.content import ToolSchema

logger = logging.getLogger(__name__)


class MCPClientDriver:
    """Consumes external Model Context Protocol (MCP) servers."""

    def __init__(self, server_configs: tuple[MCPServerConfig, ...] = ()) -> None:
        self._configs = server_configs

    async def list_tools(self) -> list[ToolSchema]:
        """Discover tools available across configured MCP servers."""
        return []

    async def invoke_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> str:
        """Invoke a tool on a specific MCP server with untrusted output handling."""
        return ""
