"""Shared fixtures: a fake AspenPlusWrapper and an in-process MCP client."""

import threading
from collections.abc import AsyncIterator
from typing import Any

import pytest
from mcp import Client

from aspenplus_mcp.server import create_server


class FakeAspen:
    """Stand-in for AspenPlusWrapper that records calls instead of talking to COM.

    - ``calls``: list of (method_name, args) in call order
    - ``threads``: thread id for each call (to check COM thread affinity)
    - ``returns``: per-method return values (default: True)
    - ``errors``: per-method exceptions to raise
    """

    def __init__(self) -> None:
        self.aspen: Any = None
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.threads: list[int] = []
        self.returns: dict[str, Any] = {}
        self.errors: dict[str, Exception] = {}

    def _record(self, method: str, *args: Any) -> Any:
        self.calls.append((method, args))
        self.threads.append(threading.get_ident())
        if method in self.errors:
            raise self.errors[method]
        return self.returns.get(method, True)

    def open_file(self, filepath: str, use_enhanced: bool = False) -> bool:
        return self._record("open_file", filepath, use_enhanced)

    def close(self) -> None:
        return self._record("close")

    def run_simulation(self) -> bool:
        return self._record("run_simulation")

    def get_value(self, path: str) -> Any:
        return self._record("get_value", path)

    def set_value(self, path: str, value: Any) -> bool:
        return self._record("set_value", path, value)

    def place_block(self, block_name: str, equipment_type: str) -> bool:
        return self._record("place_block", block_name, equipment_type)

    def delete_block(self, block_name: str) -> bool:
        return self._record("delete_block", block_name)

    def place_stream(self, stream_name: str, stream_type: str = "MATERIAL") -> bool:
        return self._record("place_stream", stream_name, stream_type)

    def connect_stream(self, block_name: str, stream_name: str, port_name: str) -> bool:
        return self._record("connect_stream", block_name, stream_name, port_name)

    def save_simulation(self, filename: str | None = None) -> bool:
        return self._record("save_simulation", filename)


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests with anyio on asyncio (the MCP SDK is built on anyio)."""
    return "asyncio"


@pytest.fixture
def fake_aspen() -> FakeAspen:
    return FakeAspen()


@pytest.fixture
async def client(fake_aspen: FakeAspen) -> AsyncIterator[Client]:
    """MCP client connected in-process to a server backed by ``fake_aspen``."""
    async with Client(create_server(fake_aspen)) as c:
        yield c
