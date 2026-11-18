"""Tests for the MCP tool and resource layer (no Aspen Plus / Windows required)."""

import threading

import pytest
from mcp import Client

from conftest import FakeAspen

pytestmark = pytest.mark.anyio

EXPECTED_TOOLS = {
    "open_simulation": {"filepath"},
    "run_simulation": set(),
    "get_value": {"path"},
    "set_value": {"path", "value"},
    "close_simulation": set(),
    "place_block": {"block_name", "equipment_type"},
    "delete_block": {"block_name"},
    "place_stream": {"stream_name"},
    "connect_stream": {"block_name", "stream_name", "port_name"},
    "save_simulation": set(),
}


def text_of(result) -> str:
    assert len(result.content) == 1
    return result.content[0].text


# --- Tool listing ---------------------------------------------------------


async def test_lists_all_tools_with_required_params(client: Client):
    tools = {t.name: t for t in (await client.list_tools()).tools}

    assert set(tools) == set(EXPECTED_TOOLS)
    for name, required in EXPECTED_TOOLS.items():
        schema = tools[name].input_schema
        assert set(schema.get("required", [])) == required, name
        assert tools[name].description, f"{name} has no description"


async def test_all_parameters_have_descriptions(client: Client):
    for tool in (await client.list_tools()).tools:
        for param, spec in tool.input_schema.get("properties", {}).items():
            assert spec.get("description"), f"{tool.name}.{param} has no description"


# --- Argument forwarding --------------------------------------------------


@pytest.mark.parametrize(
    ("tool", "arguments", "expected_call", "expected_text"),
    [
        (
            "open_simulation",
            {"filepath": "C:/sim/a.bkp"},
            ("open_file", ("C:/sim/a.bkp", False)),
            "Successfully opened simulation (basic mode): C:/sim/a.bkp",
        ),
        (
            "open_simulation",
            {"filepath": "C:/sim/a.bkp", "use_enhanced": True},
            ("open_file", ("C:/sim/a.bkp", True)),
            "Successfully opened simulation (enhanced mode): C:/sim/a.bkp",
        ),
        ("run_simulation", {}, ("run_simulation", ()), "Simulation completed successfully"),
        ("close_simulation", {}, ("close", ()), "Simulation closed"),
        (
            "place_block",
            {"block_name": "MIX-01", "equipment_type": "Mixer"},
            ("place_block", ("MIX-01", "Mixer")),
            "Successfully placed Mixer block: MIX-01",
        ),
        (
            "delete_block",
            {"block_name": "MIX-01"},
            ("delete_block", ("MIX-01",)),
            "Successfully deleted block: MIX-01",
        ),
        (
            "place_stream",
            {"stream_name": "S1"},
            ("place_stream", ("S1", "MATERIAL")),
            "Successfully placed MATERIAL stream: S1",
        ),
        (
            "place_stream",
            {"stream_name": "Q1", "stream_type": "HEAT"},
            ("place_stream", ("Q1", "HEAT")),
            "Successfully placed HEAT stream: Q1",
        ),
        (
            "connect_stream",
            {"block_name": "MIX-01", "stream_name": "S1", "port_name": "IN1"},
            ("connect_stream", ("MIX-01", "S1", "IN1")),
            "Successfully connected S1 to MIX-01.IN1",
        ),
        ("save_simulation", {}, ("save_simulation", (None,)), "Saved simulation"),
        (
            "save_simulation",
            {"filename": "C:/sim/b.bkp"},
            ("save_simulation", ("C:/sim/b.bkp",)),
            "Saved as C:/sim/b.bkp",
        ),
    ],
)
async def test_tool_forwards_to_wrapper(
    client: Client, fake_aspen: FakeAspen, tool, arguments, expected_call, expected_text
):
    result = await client.call_tool(tool, arguments)

    assert not result.is_error, text_of(result)
    assert fake_aspen.calls == [expected_call]
    assert text_of(result) == expected_text


async def test_get_value_returns_wrapper_value(client: Client, fake_aspen: FakeAspen):
    fake_aspen.returns["get_value"] = 42.5
    path = "\\Data\\Streams\\S1\\Output\\TEMP_OUT\\MIXED\\MIXED"

    result = await client.call_tool("get_value", {"path": path})

    assert not result.is_error
    assert fake_aspen.calls == [("get_value", (path,))]
    assert text_of(result) == f"Value at {path}: 42.5"


@pytest.mark.parametrize(
    ("value", "expected_type"),
    [(25, int), (25.5, float), ("WATER", str)],
)
async def test_set_value_preserves_value_type(
    client: Client, fake_aspen: FakeAspen, value, expected_type
):
    result = await client.call_tool("set_value", {"path": "\\Data\\X", "value": value})

    assert not result.is_error, text_of(result)
    [(method, (path, forwarded))] = fake_aspen.calls
    assert (method, path) == ("set_value", "\\Data\\X")
    assert forwarded == value
    assert type(forwarded) is expected_type


# --- Error handling -------------------------------------------------------


async def test_wrapper_exception_becomes_tool_error(client: Client, fake_aspen: FakeAspen):
    fake_aspen.errors["run_simulation"] = RuntimeError("No Aspen Plus file is open")

    result = await client.call_tool("run_simulation", {})

    assert result.is_error
    assert "No Aspen Plus file is open" in text_of(result)


async def test_missing_required_argument_is_rejected(client: Client, fake_aspen: FakeAspen):
    result = await client.call_tool("get_value", {})

    assert result.is_error
    assert "path" in text_of(result)
    assert fake_aspen.calls == []


async def test_unknown_tool_is_rejected(client: Client, fake_aspen: FakeAspen):
    result = await client.call_tool("does_not_exist", {})

    assert result.is_error
    assert fake_aspen.calls == []


# --- COM thread affinity --------------------------------------------------


async def test_wrapper_calls_stay_on_event_loop_thread(client: Client, fake_aspen: FakeAspen):
    """Aspen Plus COM objects are apartment-threaded: every wrapper call must
    happen on the same thread. This fails if a tool is changed from
    ``async def`` to ``def`` (MCPServer runs sync tools in worker threads)."""
    loop_thread = threading.get_ident()

    await client.call_tool("open_simulation", {"filepath": "a.bkp", "use_enhanced": True})
    await client.call_tool("run_simulation", {})
    await client.call_tool("get_value", {"path": "\\Data\\X"})
    await client.call_tool("set_value", {"path": "\\Data\\X", "value": 1})
    await client.call_tool("place_block", {"block_name": "B1", "equipment_type": "Mixer"})
    await client.call_tool("delete_block", {"block_name": "B1"})
    await client.call_tool("place_stream", {"stream_name": "S1"})
    await client.call_tool(
        "connect_stream", {"block_name": "B1", "stream_name": "S1", "port_name": "IN1"}
    )
    await client.call_tool("save_simulation", {})
    await client.call_tool("close_simulation", {})

    assert len(fake_aspen.threads) == len(EXPECTED_TOOLS)
    assert set(fake_aspen.threads) == {loop_thread}


# --- Resources ------------------------------------------------------------


async def test_lists_status_resource(client: Client):
    resources = (await client.list_resources()).resources

    assert [str(r.uri) for r in resources] == ["simulation://status"]
    assert resources[0].mime_type == "text/plain"


@pytest.mark.parametrize(
    ("loaded", "expected"),
    [(False, "No simulation loaded"), (True, "Simulation loaded and ready")],
)
async def test_status_resource_reflects_wrapper_state(
    client: Client, fake_aspen: FakeAspen, loaded, expected
):
    fake_aspen.aspen = object() if loaded else None

    result = await client.read_resource("simulation://status")

    assert [c.text for c in result.contents] == [expected]
