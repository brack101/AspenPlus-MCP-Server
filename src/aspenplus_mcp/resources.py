"""MCP resource implementations for Aspen Plus data access."""

import logging

from mcp.server.mcpserver import MCPServer

from .aspen_wrapper import AspenPlusWrapper

logger = logging.getLogger(__name__)


def register_resources(mcp: MCPServer, aspen: AspenPlusWrapper) -> None:
    """Register all Aspen Plus resources with the MCP server."""

    @mcp.resource(
        "simulation://status",
        name="Simulation Status",
        description="Current status of the Aspen Plus simulation",
        mime_type="text/plain",
    )
    async def simulation_status() -> str:
        """Current status of the Aspen Plus simulation."""
        return "Simulation loaded and ready" if aspen.aspen else "No simulation loaded"
