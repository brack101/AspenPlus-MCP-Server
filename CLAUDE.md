# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AspenPlusMCP - A Model Context Protocol (MCP) server for Aspen Plus integration. This server enables AI assistants to interact with Aspen Plus chemical process simulations through a standardized interface.

## Development Commands

### Setup
```bash
# Create .venv and install package (editable) + dev dependencies
uv sync --locked

# Add dependencies
uv add <package>          # runtime
uv add --dev <package>    # dev (dependency-groups)
```

### Running
```bash
# Run the MCP server
uv run --locked aspenplus-mcp

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
  - Enhanced mode: delegates to `enhanced.py`; shares the session's COM document as `self.aspen`, so node-path tools work in both modes
- **enhanced.py**: Enhanced mode via [py2aspen](https://github.com/adk23333/py2aspen) (`EnhancedSession`); imported lazily, Windows only
- **tools.py**: MCP tool implementations with 10 tools including flowsheet editing
- **resources.py**: MCP resource endpoints (simulation status)

### Aspen Plus Integration

Basic mode uses `win32com.client` (pywin32), enhanced mode uses py2aspen (comtypes). Key concepts:

- **Node Paths**: Aspen Plus uses tree-based paths to access data (e.g., `\\Data\\Streams\\S1\\Output\\TEMP_OUT\\MIXED\\MIXED`)
- **COM Dispatch**: Connection established via `win32com.client.Dispatch("Apwn.Document")`
- **File Formats**: Supports .bkp (backup) and .apw (work) files
- **Dual Interface**:
  - Basic mode: Simple get/set operations on existing simulations
  - Enhanced mode: Full flowsheet manipulation (add/delete blocks, streams, connections)
- **py2aspen** (BSD-3-Clause, PyPI, pinned `>=0.3,<0.4` because pre-1.0; Windows-only dependency):
  - `UnitAspen` with late binding (`lazybind()`), no generated type library needed
  - Flowsheet operations are recorded as actions (`place`, `delete`, `connect`) and run via `unit.exec(...)`
  - `connect` expects a bound port method (e.g. `mixer.f_in`); `enhanced.py` builds one for arbitrary port strings
  - **Its loguru logger writes to stdout by default** – `enhanced.py` re-routes it to stderr on import; never call `py2aspen.log.set_level()` (re-adds stdout)
  - Do not copy `tlb/v14/happ.tlb` from the py2aspen repo – it is AspenTech's proprietary type library

### MCP Implementation

Uses the high-level `MCPServer` API of the MCP Python SDK 2.x (`mcp.server.mcpserver`, formerly `FastMCP`):
- `@mcp.tool()` - Each tool is a typed function; the input schema is generated from type hints (`Annotated[..., Field(description=...)]`), the docstring becomes the tool description
- `@mcp.resource(uri, ...)` - Static resources (e.g. `simulation://status`)
- Errors: raise `ToolError` (from `mcp.server.mcpserver.exceptions`) so the message reaches the model with `isError: true`; other exceptions only yield a generic error
- **Tools must stay `async def`**: MCPServer runs sync tools in worker threads, but Aspen Plus COM objects are apartment-threaded and must be used from the thread that created them

### Testing

- `tests/test_tools.py` tests the MCP layer (tools + resources) in-process via `mcp.Client(create_server(fake))` – no Windows/Aspen Plus needed
- `tests/conftest.py` provides `FakeAspen`, a stand-in for `AspenPlusWrapper` that records calls, thread ids, and can return values or raise errors
- Async tests use the anyio pytest plugin (`pytestmark = pytest.mark.anyio`), not pytest-asyncio: the MCP client's anyio task groups break with pytest-asyncio async fixtures
- `test_wrapper_calls_stay_on_event_loop_thread` guards the COM thread-affinity requirement (fails if a tool becomes a sync `def`)
- `tests/test_aspen_wrapper.py` tests enhanced mode against a fake `py2aspen` module (`build_fake_py2aspen()`), whose logger writes to stdout like loguru does
- New tools: add them to `EXPECTED_TOOLS`, the forwarding parametrization, the thread test, and `FakeAspen`

### Dependency updates (supply chain)

The MCP server runs with the user's privileges and is started automatically by Claude, so dependencies are treated as untrusted until reviewed:

- **uv only, always `--locked`**: `uv.lock` pins every package with SHA-256 hashes; `uv sync --locked` / `uv run --locked` fail if it is out of date. There is deliberately no pip install path (pip ignores the lock file).
- **Cooldown**: `[tool.uv] exclude-newer` in `pyproject.toml` limits resolution to versions uploaded before that date. Never resolve against "now": when updating, set it to ~7 days before today, then `uv lock --upgrade` (or `--upgrade-package <name>`).
- **Never change `uv.lock` incidentally**: dependency updates go into their own commit (`pyproject.toml` + `uv.lock`), with the lock diff reviewed.
- **py2aspen** (single maintainer, pre-1.0) is pinned exactly (`==`). To update:
  1. Read the diff between the old and new tag on GitHub (~2000 lines, feasible)
  2. Check that the PyPI wheel matches the git tag (unzip the wheel, `diff -r` against `src/py2aspen` at the tag)
  3. Bump the pin and `exclude-newer`, `uv lock --upgrade-package py2aspen`, run tests, then test enhanced mode on Windows with Aspen Plus

### Platform Limitations

The Aspen Plus wrapper only works on Windows with pywin32 installed. The code includes checks for platform compatibility and gracefully degrades on non-Windows systems.
