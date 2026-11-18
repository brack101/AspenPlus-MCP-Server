"""Main MCP server implementation for Aspen Plus."""

import logging
import sys

from mcp.server.mcpserver import MCPServer

from .aspen_wrapper import AspenPlusWrapper
from .tools import register_tools
from .resources import register_resources

# Configure logging to stderr only (stdout is used for JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_server() -> MCPServer:
    """Create the Aspen Plus MCP server with all tools and resources registered."""
    mcp = MCPServer("aspenplus-mcp")

    # Initialize Aspen Plus wrapper
    aspen = AspenPlusWrapper()

    # Register tools and resources
    register_tools(mcp, aspen)
    register_resources(mcp, aspen)

    return mcp


def run():
    """Console script entry point (used by `aspenplus-mcp` / `uv run aspenplus-mcp`)."""
    logger.info("Starting Aspen Plus MCP server")
    create_server().run("stdio")


if __name__ == "__main__":
    run()
