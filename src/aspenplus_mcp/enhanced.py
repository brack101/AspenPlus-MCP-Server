"""Enhanced mode: flowsheet editing via py2aspen (Windows only).

py2aspen (https://github.com/adk23333/py2aspen, BSD-3-Clause) is imported at
module level, so this module must only be imported lazily, on Windows, when a
file is opened with ``use_enhanced=True``.
"""

import sys
import types
from pathlib import Path
from typing import Any

import py2aspen
from py2aspen import Block, Stream, UnitAspen

# py2aspen logs via loguru to sys.stdout (configured at import). In stdio mode
# stdout is the MCP JSON-RPC channel, so route its log output to stderr.
# contextlib.redirect_stdout would not help: loguru keeps a reference to the
# original stdout object. The sink looks up sys.stderr at write time, so it
# follows later replacements of sys.stderr instead of holding a stale object.
py2aspen.logger.remove()
py2aspen.logger.add(lambda message: sys.stderr.write(message), level="INFO")

BLOCK_TYPES: dict[str, type[Block]] = {
    cls.__name__.upper(): cls
    for cls in (
        py2aspen.Mixer,
        py2aspen.Heater,
        py2aspen.Flash2,
        py2aspen.Radfrac,
        py2aspen.DSTWU,
        py2aspen.RPlug,
        py2aspen.RCSTR,
        py2aspen.RYield,
        py2aspen.Splitter,
    )
}

STREAM_TYPES: dict[str, type[Stream]] = {
    "MATERIAL": py2aspen.MaterialStream,
    "HEAT": py2aspen.HeatStream,
    "WORK": py2aspen.WorkStream,
    "POWER": py2aspen.PowerStream,
}


class _ExistingBlock(Block):
    """Reference to a block already on the flowsheet, known only by name.

    Used for delete/connect, where py2aspen needs a Block object but only
    reads its name; the block's actual type is irrelevant there.
    """

    def get_type(self) -> str:
        raise NotImplementedError("type of an existing block is unknown")

    def set_input(self, inputs: Any) -> None:
        raise NotImplementedError

    def get_results(self, units: Any = None) -> Any:
        raise NotImplementedError


class _ExistingStream(Stream):
    """Reference to a stream already on the flowsheet, known only by name."""

    def get_type(self) -> str:
        raise NotImplementedError("type of an existing stream is unknown")

    def set_input(self, inputs: Any) -> None:
        raise NotImplementedError

    def get_results(self, units: Any = None) -> Any:
        raise NotImplementedError


def _lookup(kind: str, value: str, table: dict[str, Any]) -> Any:
    try:
        return table[value.upper()]
    except KeyError:
        supported = ", ".join(cls.__name__ for cls in table.values())
        raise ValueError(f"Unsupported {kind} '{value}'. Supported: {supported}") from None


class EnhancedSession:
    """An open Aspen Plus simulation driven through py2aspen."""

    def __init__(self, progid: str, filepath: str) -> None:
        self.unit = UnitAspen(progid)
        self.unit.lazybind()  # late binding, no generated type library needed
        self.unit.suppress_dialogs(True)
        if Path(filepath).suffix.lower() == ".apw":
            self.unit.open_apw(filepath)
        else:
            self.unit.open_bkp(filepath)
        self.unit.set_visible(False)

    @property
    def app(self) -> Any:
        """The Aspen Plus COM document (for node-path access)."""
        return self.unit.app

    def run(self) -> None:
        self.unit.engine_run()

    def place_block(self, block_name: str, equipment_type: str) -> None:
        block_cls = _lookup("equipment type", equipment_type, BLOCK_TYPES)
        self.unit.exec(py2aspen.place(block_cls(block_name)))

    def delete_block(self, block_name: str) -> None:
        self.unit.exec(py2aspen.delete(_ExistingBlock(block_name)))

    def place_stream(self, stream_name: str, stream_type: str) -> None:
        stream_cls = _lookup("stream type", stream_type, STREAM_TYPES)
        self.unit.exec(py2aspen.place(stream_cls(stream_name)))

    def connect_stream(self, block_name: str, stream_name: str, port_name: str) -> None:
        block = _ExistingBlock(block_name)
        # py2aspen expects a bound port method (e.g. mixer.f_in) and reads both
        # the block (__self__) and the port string from it; build one for an
        # arbitrary port name such as "F(IN)" or "P(OUT)".
        port = types.MethodType(lambda _self: port_name, block)
        self.unit.exec(py2aspen.connect(_ExistingStream(stream_name), port))

    def save(self, filename: str | None = None) -> None:
        if not filename:
            self.unit.save()
        elif Path(filename).suffix.lower() == ".bkp":
            self.unit.save_bkp(filename)
        else:
            self.unit.save_as(filename, overwrite=True)

    def close(self) -> None:
        self.unit.exit()
