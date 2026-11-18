# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AspenPlusMCP - A Model Context Protocol (MCP) server for Aspen Plus integration. This server enables AI assistants to interact with Aspen Plus chemical process simulations through a standardized interface.

## Development Commands

### Setup
```bash
# Create .venv and install package (editable) + dev dependencies
uv sync

# Add dependencies
uv add <package>          # runtime
uv add --dev <package>    # dev (dependency-groups)
```

### Running
```bash
# Run the MCP server
uv run aspenplus-mcp

# Run tests
uv run pytest

# Format code
uv run black src/
```

## Architecture

### Core Components

- **server.py**: Main MCP server using stdio transport
- **aspen_wrapper.py**: COM interface wrapper for Aspen Plus with dual-mode support (Windows-only)
  - Basic mode: Direct COM access for reading/writing values
  - Enhanced mode: Advanced interface with flowsheet manipulation capabilities
- **aspen_interface.py**: Extended Aspen Plus automation library (vendored from AspenPlus-Python-Interface)
- **tools.py**: MCP tool implementations with 11 tools including flowsheet editing
- **resources.py**: MCP resource endpoints (simulation status)

### Aspen Plus Integration

The project uses `win32com.client` (pywin32) to communicate with Aspen Plus via COM automation. Key concepts:

- **Node Paths**: Aspen Plus uses tree-based paths to access data (e.g., `\\Data\\Streams\\S1\\Output\\TEMP_OUT\\MIXED\\MIXED`)
- **COM Dispatch**: Connection established via `win32com.client.Dispatch("Apwn.Document")`
- **File Formats**: Supports .bkp (backup) and .apw (work) files
- **Dual Interface**:
  - Basic mode: Simple get/set operations on existing simulations
  - Enhanced mode: Full flowsheet manipulation (add/delete blocks, streams, connections)
- **Vendored Library**: `aspen_interface.py` is vendored from [AspenPlus-Python-Interface](https://github.com/YouMayCallMeJesus/AspenPlus-Python-Interface) (by Richard ten Hagen), providing ~5000 lines of advanced functionality
  - Requires `numpy` dependency
  - Not available as pip package, so included directly in codebase

### MCP Implementation

Tools are registered using decorators from the MCP SDK:
- `@server.list_tools()` - Define available tools
- `@server.call_tool()` - Handle tool execution
- `@server.list_resources()` - Define resources
- `@server.read_resource()` - Handle resource reads

### Platform Limitations

The Aspen Plus wrapper only works on Windows with pywin32 installed. The code includes checks for platform compatibility and gracefully degrades on non-Windows systems.
