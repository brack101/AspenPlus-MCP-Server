# AspenPlusMCP Project Plan

## Overview
Build an MCP (Model Context Protocol) server to enable AI assistants to interact with Aspen Plus chemical process simulations through a standardized interface.

## Project Scope

### Core Capabilities
1. **Process Simulation Control**
   - Open/close Aspen Plus simulation files (.bkp, .apw)
   - Run simulations and monitor execution status
   - Reinitialize and reset simulations

2. **Data Access & Manipulation**
   - Read stream properties (temperature, pressure, flow rates, compositions)
   - Read block/unit operation parameters
   - Modify input parameters and specifications
   - Access simulation results

3. **Analysis & Optimization**
   - Run sensitivity analyses
   - Perform parameter sweeps
   - Extract data for external optimization
   - Generate simulation reports

## Technical Architecture

### Technology Stack
- **Language**: Python (Windows-compatible for COM interface)
- **MCP SDK**: Python MCP SDK from Anthropic
- **Aspen Interface**:
  - `win32com.client` (pywin32) for basic COM access
  - [py2aspen](https://github.com/adk23333/py2aspen) (BSD-3-Clause, comtypes) for enhanced flowsheet manipulation
- **Dependencies**: mcp, pydantic, pywin32, py2aspen
- **Transport**: stdio and HTTP with SSE support

### Project Structure
```
AspenPlusMCP/
├── src/
│   ├── aspenplus_mcp/
│   │   ├── __init__.py
│   │   ├── server.py          # Main MCP server
│   │   ├── aspen_wrapper.py   # COM interface wrapper (dual-mode)
│   │   ├── enhanced.py        # Enhanced mode via py2aspen
│   │   ├── tools.py           # MCP tool implementations (10 tools)
│   │   ├── resources.py       # MCP resource implementations
│   │   └── prompts.py         # MCP prompt templates
├── tests/
├── examples/
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

### MCP Components

**Tools** (executable functions):
- Basic Mode:
  - `open_simulation` - Open Aspen Plus simulation file
  - `run_simulation` - Execute Aspen Plus simulation
  - `get_value` - Retrieve values using node paths
  - `set_value` - Modify parameters using node paths
  - `close_simulation` - Close simulation
- Enhanced Mode (via py2aspen):
  - `place_block` - Add equipment to flowsheet
  - `delete_block` - Remove equipment from flowsheet
  - `place_stream` - Create material/heat/work/power streams
  - `connect_stream` - Wire blocks together
  - `save_simulation` - Save changes to file

**Resources** (data exposure):
- `simulation://status` - Current simulation state
- `simulation://streams` - All stream data
- `simulation://blocks` - All block/unit data
- `simulation://properties` - Physical properties

**Prompts** (templates):
- Optimize process parameters
- Troubleshoot convergence issues
- Generate process reports

## Implementation Status

### ✅ Completed
- **Phase 1: Foundation**
  - ✅ Set up Python project with MCP SDK
  - ✅ Implement basic Aspen Plus COM wrapper
  - ✅ Create stdio transport MCP server

- **Phase 2: Core Tools**
  - ✅ Implement file operations (open/close)
  - ✅ Add simulation control (run)
  - ✅ Create basic data access tools (get/set value)

- **Phase 3: Enhanced Integration**
  - ✅ Integrated AspenPlus-Python-Interface library
  - ✅ Implemented dual-mode wrapper (basic/enhanced)
  - ✅ Added flowsheet manipulation tools (11 total tools)
  - ✅ Created comprehensive documentation
  - ✅ Replaced vendored AspenPlus-Python-Interface with py2aspen (BSD-3-Clause, PyPI)

### 🚧 In Progress / Future
- **Phase 4: Advanced Features**
  - ⏳ Add parameter modification capabilities
  - ⏳ Implement sensitivity analysis tools
  - ⏳ Create optimization helpers

- **Phase 5: Production Ready**
  - ⏳ Add HTTP/SSE transport support
  - ⏳ Implement comprehensive error handling
  - ✅ Set up testing suite (MCP layer + enhanced mode with fakes; no Windows integration tests yet)
  - ✅ Create documentation and examples

## References

### MCP Resources
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-06-18)
- [MCP GitHub Organization](https://github.com/modelcontextprotocol)
- [MCP Server Examples](https://github.com/modelcontextprotocol/servers)

### Aspen Plus Automation
- [py2aspen](https://github.com/adk23333/py2aspen)
- [Aspen Plus Python Interface](https://github.com/YouMayCallMeJesus/AspenPlus-Python-Interface) (used in earlier versions)
- [Aspen Plus Automation](https://github.com/zwang1995/Aspen-Plus-Automation)
- [ap-python package](https://github.com/bsha0/ap-python)
