"""MCP tool implementations for Aspen Plus operations."""

import logging
from collections.abc import Callable
from typing import Annotated, Any, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from .aspen_wrapper import AspenPlusWrapper

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _call(tool: str, fn: Callable[..., T], *args: Any) -> T:
    """Run a wrapper call and turn failures into ToolError.

    ToolError messages are passed to the model (with is_error=True); any other
    exception would only be reported as a generic "Error executing tool".
    """
    try:
        return fn(*args)
    except Exception as e:
        logger.error(f"Tool {tool} failed: {e}")
        raise ToolError(str(e)) from e


def register_tools(mcp: MCPServer, aspen: AspenPlusWrapper) -> None:
    """Register all Aspen Plus tools with the MCP server.

    The tools are declared ``async`` on purpose: MCPServer runs sync tools in
    worker threads, but the Aspen Plus COM objects are apartment-threaded and
    must be used from the thread that created them. Async tools run on the
    event loop thread, so all COM calls stay on one thread.
    """

    @mcp.tool()
    async def open_simulation(
        filepath: Annotated[str, Field(description="Path to the Aspen Plus simulation file")],
        use_enhanced: Annotated[
            bool,
            Field(description="Use enhanced interface with block/stream manipulation capabilities"),
        ] = False,
    ) -> str:
        """Open an Aspen Plus simulation file (.bkp or .apw)"""
        _call("open_simulation", aspen.open_file, filepath, use_enhanced)
        mode = "enhanced" if use_enhanced else "basic"
        return f"Successfully opened simulation ({mode} mode): {filepath}"

    @mcp.tool()
    async def run_simulation() -> str:
        """Run the current Aspen Plus simulation"""
        _call("run_simulation", aspen.run_simulation)
        return "Simulation completed successfully"

    @mcp.tool()
    async def get_value(
        path: Annotated[
            str,
            Field(
                description="Node path (e.g., \\Data\\Streams\\S1\\Output\\TEMP_OUT\\MIXED\\MIXED)"
            ),
        ],
    ) -> str:
        """Get a value from the simulation using a node path"""
        value = _call("get_value", aspen.get_value, path)
        return f"Value at {path}: {value}"

    @mcp.tool()
    async def set_value(
        path: Annotated[str, Field(description="Node path to the parameter")],
        value: Annotated[int | float | str, Field(description="Value to set (number or string)")],
    ) -> str:
        """Set a value in the simulation using a node path"""
        _call("set_value", aspen.set_value, path, value)
        return f"Successfully set {path} to {value}"

    @mcp.tool()
    async def close_simulation() -> str:
        """Close the current Aspen Plus simulation"""
        _call("close_simulation", aspen.close)
        return "Simulation closed"

    @mcp.tool()
    async def place_block(
        block_name: Annotated[str, Field(description="Name for the new block")],
        equipment_type: Annotated[
            str,
            Field(
                description=(
                    "Type of equipment (case-insensitive): Mixer, Heater, Flash2, Radfrac, "
                    "DSTWU, RPlug, RCSTR, RYield, Splitter"
                )
            ),
        ],
    ) -> str:
        """Place a new equipment block in the flowsheet (requires enhanced interface)"""
        _call("place_block", aspen.place_block, block_name, equipment_type)
        return f"Successfully placed {equipment_type} block: {block_name}"

    @mcp.tool()
    async def delete_block(
        block_name: Annotated[str, Field(description="Name of the block to delete")],
    ) -> str:
        """Delete an equipment block from the flowsheet (requires enhanced interface)"""
        _call("delete_block", aspen.delete_block, block_name)
        return f"Successfully deleted block: {block_name}"

    @mcp.tool()
    async def place_stream(
        stream_name: Annotated[str, Field(description="Name for the new stream")],
        stream_type: Annotated[
            str, Field(description="Type of stream: MATERIAL, HEAT, WORK, or POWER")
        ] = "MATERIAL",
    ) -> str:
        """Place a new stream in the flowsheet (requires enhanced interface)"""
        _call("place_stream", aspen.place_stream, stream_name, stream_type)
        return f"Successfully placed {stream_type} stream: {stream_name}"

    @mcp.tool()
    async def connect_stream(
        block_name: Annotated[str, Field(description="Name of the block")],
        stream_name: Annotated[str, Field(description="Name of the stream")],
        port_name: Annotated[
            str,
            Field(
                description=(
                    "Aspen port name on the block, e.g. F(IN), P(OUT), V(OUT), L(OUT), "
                    "D(OUT), B(OUT), LD(OUT)"
                )
            ),
        ],
    ) -> str:
        """Connect a stream to a block port (requires enhanced interface)"""
        _call("connect_stream", aspen.connect_stream, block_name, stream_name, port_name)
        return f"Successfully connected {stream_name} to {block_name}.{port_name}"

    @mcp.tool()
    async def save_simulation(
        filename: Annotated[
            str | None, Field(description="Optional: new filename to save as")
        ] = None,
    ) -> str:
        """Save the simulation to file (requires enhanced interface)"""
        _call("save_simulation", aspen.save_simulation, filename)
        return f"Saved as {filename}" if filename else "Saved simulation"
