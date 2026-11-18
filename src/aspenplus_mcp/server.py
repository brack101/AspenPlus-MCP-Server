"""Main MCP server implementation for Aspen Plus."""

import asyncio
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .aspen_wrapper import AspenPlusWrapper
from .tools import register_tools
from .resources import register_resources

# Configure logging to stderr only (stdout is used for JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run the Aspen Plus MCP server."""
    server = Server("aspenplus-mcp")

    # Initialize Aspen Plus wrapper
    aspen = AspenPlusWrapper()

    # Register tools and resources
    register_tools(server, aspen)
    register_resources(server, aspen)

    logger.info("Starting Aspen Plus MCP server")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def run():
    """Console script entry point (used by `aspenplus-mcp` / `uv run aspenplus-mcp`)."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
