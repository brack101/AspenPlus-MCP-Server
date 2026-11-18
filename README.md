# AspenPlus MCP Server

MCP (Model Context Protocol) server for Aspen Plus process simulation integration. This server enables AI assistants to interact with Aspen Plus simulations through a standardized interface.

## Features

- **Process Simulation Control**: Open, run, and manage Aspen Plus simulations
- **Data Access**: Read and write stream properties, block parameters, and simulation results
- **Flowsheet Manipulation**: Create, delete, and connect equipment blocks and streams (enhanced mode)
- **Equipment Support**: Mixer, Heater, Flash2, Radfrac, DSTWU, RPLUG, RCSTR, RYIELD
- **AI Integration**: Connect Claude and other AI assistants to Aspen Plus

## Requirements

- Python 3.10 or higher
- Windows OS (for Aspen Plus COM interface)
- Aspen Plus installed
- [uv](https://docs.astral.sh/uv/) (recommended) – installs Python and all dependencies (incl. pywin32) automatically

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd AspenPlus-MCP-Server
```

2. Install uv (if not already installed):
```powershell
winget install --id=astral-sh.uv -e
# or: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Create the environment and install all dependencies:
```bash
uv sync
```
This creates a `.venv` in the project folder, installs a suitable Python version if needed, and installs the package in editable mode (incl. dev tools).

<details>
<summary>Alternative: plain pip</summary>

```bash
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -e .
```
</details>

## Usage

### Running the Server

```bash
uv run aspenplus-mcp
```

The server communicates via stdio and is normally started by the MCP client (see below), not manually.

### Available Tools

#### Basic Mode Tools
- `open_simulation` - Open an Aspen Plus simulation file (set `use_enhanced: false`)
- `run_simulation` - Run the current simulation
- `get_value` - Get a value from the simulation using a node path
- `set_value` - Set a value in the simulation
- `close_simulation` - Close the current simulation

#### Enhanced Mode Tools (requires `use_enhanced: true`)
- `place_block` - Add a new equipment block to the flowsheet
- `delete_block` - Remove an equipment block from the flowsheet
- `place_stream` - Add a new stream to the flowsheet
- `connect_stream` - Connect a stream to a block port
- `save_simulation` - Save the simulation to file

### Example Node Paths

```
# Stream temperature
\\Data\\Streams\\S1\\Output\\TEMP_OUT\\MIXED\\MIXED

# Block parameter
\\Data\\Blocks\\B1\\Input\\TEMP

# Component flow rate
\\Data\\Streams\\S1\\Output\\MOLEFLOW\\MIXED\\WATER
```

## Development

`uv sync` already installs the dev dependencies (pytest, black, mypy).

Run tests:
```bash
uv run pytest
```

Format code:
```bash
uv run black src/
```

Add a dependency:
```bash
uv add <package>          # runtime dependency
uv add --dev <package>    # dev dependency
```

## Configuration with Claude

In all examples, replace `C:\\path\\to\\AspenPlus-MCP-Server` with the absolute path to your clone of this repository. `uv run` creates/updates the environment automatically on first start, so a prior `uv sync` is optional.

### Claude Code

```powershell
claude mcp add aspenplus --scope user -- uv --directory "C:\path\to\AspenPlus-MCP-Server" run aspenplus-mcp
```

- `--scope user` makes the server available in all projects; omit it (default `local`) to register it only for the current project, or use `--scope project` to write it to a shared `.mcp.json`.
- Check the connection with `claude mcp list` or `/mcp` inside Claude Code.

### Claude Desktop

Add to your Claude Desktop config file (Settings → Developer → Edit Config):

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "aspenplus": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\AspenPlus-MCP-Server",
        "run",
        "aspenplus-mcp"
      ]
    }
  }
}
```

**Important Notes:**
- In JSON, use double backslashes (`\\`) or forward slashes (`/`) in paths
- If Claude Desktop cannot find `uv`, use its full path as `command` (find it with `where uv`, e.g. `C:\\Users\\<you>\\.local\\bin\\uv.exe`)
- After editing the config file, fully quit and restart Claude Desktop (also from the system tray)
- The MCP server starts automatically when Claude Desktop launches

<details>
<summary>Alternative without uv (pip installation)</summary>

```json
{
  "mcpServers": {
    "aspenplus": {
      "command": "C:\\path\\to\\AspenPlus-MCP-Server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "aspenplus_mcp.server"]
    }
  }
}
```
</details>

## Usage Examples

### Basic Mode - Reading/Writing Values
```python
# Open simulation in basic mode
open_simulation(filepath="C:/simulations/myprocess.bkp", use_enhanced=False)

# Read stream temperature
get_value(path="\\Data\\Streams\\S1\\Output\\TEMP_OUT\\MIXED\\MIXED")

# Set feed temperature
set_value(path="\\Data\\Streams\\FEED\\Input\\TEMP", value=25.0)

# Run simulation
run_simulation()
```

### Enhanced Mode - Flowsheet Editing
```python
# Open simulation in enhanced mode
open_simulation(filepath="C:/simulations/myprocess.bkp", use_enhanced=True)

# Add a mixer block
place_block(block_name="MIX-01", equipment_type="Mixer")

# Add streams
place_stream(stream_name="STREAM-1", stream_type="MATERIAL")
place_stream(stream_name="STREAM-2", stream_type="MATERIAL")

# Connect streams to mixer
connect_stream(block_name="MIX-01", stream_name="STREAM-1", port_name="IN1")
connect_stream(block_name="MIX-01", stream_name="STREAM-2", port_name="IN2")

# Save changes
save_simulation()
```

## Credits

This project includes the [AspenPlus Python Interface](https://github.com/YouMayCallMeJesus/AspenPlus-Python-Interface) by Richard Wolfgang ten Hagen (version 2.1) as `src/aspenplus_mcp/aspen_interface.py` for advanced flowsheet manipulation capabilities. If you use it for academic research, please cite it (see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

## License

The code of this project is licensed under the MIT license.

**Exception:** `src/aspenplus_mcp/aspen_interface.py` is third-party code that is **not** covered by the MIT license. Its upstream repository has no license file; its terms of use are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
