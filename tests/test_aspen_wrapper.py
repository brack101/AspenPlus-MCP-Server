"""Tests for AspenPlusWrapper's enhanced mode via py2aspen (enhanced.py).

py2aspen needs Windows + comtypes + Aspen Plus, so it is replaced by a fake
module that mirrors the parts of its API we use, including its logger writing
to stdout (loguru's default configuration in py2aspen.log).
"""

import sys
import types
from typing import Any

import pytest

from aspenplus_mcp.aspen_wrapper import ASPEN_PROGID, AspenPlusWrapper

# --- fake py2aspen ------------------------------------------------------------


class FakeLogger:
    """Mimics the loguru logger exported as py2aspen.logger."""

    def __init__(self) -> None:
        self.sinks: list[Any] = [sys.stdout]  # py2aspen.log: logger.add(sys.stdout, ...)

    def remove(self) -> None:
        self.sinks.clear()

    def add(self, sink: Any, **kwargs: Any) -> None:
        self.sinks.append(sink)

    def _log(self, msg: str, *args: Any) -> None:
        for sink in self.sinks:
            # loguru accepts file-like objects and callables as sinks
            write = sink if callable(sink) else sink.write
            write(msg.format(*args) + "\n")

    info = success = _log


class FakeNode:
    def __init__(self, value: Any = None) -> None:
        self.Value = value


class FakeTree:
    def __init__(self) -> None:
        self.nodes: dict[str, FakeNode] = {}

    def FindNode(self, path: str) -> FakeNode:
        return self.nodes.setdefault(path, FakeNode())


class FakeApp:
    def __init__(self) -> None:
        self.Tree = FakeTree()


def build_fake_py2aspen() -> types.ModuleType:
    mod = types.ModuleType("py2aspen")
    mod.logger = logger = FakeLogger()

    class Block:
        def __init__(self, name: str | None = None) -> None:
            self.name = name

    class Stream:
        def __init__(self, name: str | None = None) -> None:
            self.name = name

    mod.Block, mod.Stream = Block, Stream

    for type_name in ("Mixer", "Heater", "Flash2", "Radfrac", "DSTWU", "RPlug", "RCSTR"):
        setattr(mod, type_name, type(type_name, (Block,), {"get_type": lambda s, t=type_name: t}))
    mod.RYield = type("RYield", (Block,), {"get_type": lambda s: "RYield"})
    mod.Splitter = type("Splitter", (Block,), {"get_type": lambda s: "Splitter"})
    for cls_name, stream_type in (
        ("MaterialStream", "MATERIAL"),
        ("HeatStream", "HEAT"),
        ("WorkStream", "WORK"),
        ("PowerStream", "POWER"),
    ):
        setattr(mod, cls_name, type(cls_name, (Stream,), {"get_type": lambda s, t=stream_type: t}))

    # flowsheet functions: return a list of recorded operations ("Action")
    mod.place = lambda *items: [("place", item) for item in items]
    mod.delete = lambda *items: [("delete", item) for item in items]

    def connect(stream, port):
        # like py2aspen.flowsheet.Action.connect: block from the bound method
        return [("connect", port.__self__, stream, port())]

    mod.connect = connect

    class UnitAspen:
        instances: list["UnitAspen"] = []
        fail_on: set[str] = set()  # method names that raise (simulate COM errors)

        def __init__(self, progid: str, machine: str | None = None) -> None:
            UnitAspen.instances.append(self)
            self.progid = progid
            self.app = FakeApp()
            self.calls: list[tuple[str, tuple[Any, ...]]] = []
            self.executed: list[tuple[Any, ...]] = []
            logger.success("Connected to Aspen Plus with progid {}", progid)

        def __getattr__(self, name: str):
            if name in {
                "lazybind",
                "suppress_dialogs",
                "open_bkp",
                "open_apw",
                "set_visible",
                "engine_run",
                "save",
                "save_as",
                "save_bkp",
                "exit",
            }:

                def record(*args: Any, **kwargs: Any) -> None:
                    self.calls.append((name, args + tuple(kwargs.items())))
                    logger.info("{} called", name)
                    if name in UnitAspen.fail_on:
                        raise RuntimeError(f"{name} failed")

                return record
            raise AttributeError(name)

        def exec(self, action: list[tuple[Any, ...]]) -> None:
            self.executed.extend(action)
            logger.success("Executed action with {} operation(s)", len(action))

    mod.UnitAspen = UnitAspen
    return mod


# --- fixtures -------------------------------------------------------------------


@pytest.fixture
def fake_py2aspen(monkeypatch) -> types.ModuleType:
    """Install a fresh fake py2aspen and force enhanced.py to re-import it."""
    mod = build_fake_py2aspen()  # built inside the test, so sys.stdout is pytest's capture
    monkeypatch.setitem(sys.modules, "py2aspen", mod)
    monkeypatch.delitem(sys.modules, "aspenplus_mcp.enhanced", raising=False)
    return mod


@pytest.fixture
def wrapper(fake_py2aspen) -> AspenPlusWrapper:
    """Wrapper that believes it runs on Windows."""
    w = AspenPlusWrapper()
    w._is_windows = True
    return w


@pytest.fixture
def opened(wrapper, capsys) -> AspenPlusWrapper:
    wrapper.open_file("C:/sims/process.bkp", use_enhanced=True)
    capsys.readouterr()  # discard output from opening
    return wrapper


def unit_of(w: AspenPlusWrapper):
    return w.session.unit


# --- open -----------------------------------------------------------------------


def test_enhanced_open_sequence(opened):
    unit = unit_of(opened)

    assert unit.progid == ASPEN_PROGID
    assert [name for name, _ in unit.calls] == [
        "lazybind",
        "suppress_dialogs",
        "open_bkp",
        "set_visible",
    ]
    assert unit.calls[1] == ("suppress_dialogs", (True,))
    assert unit.calls[2] == ("open_bkp", ("C:/sims/process.bkp",))
    assert unit.calls[3] == ("set_visible", (False,))


def test_enhanced_open_apw_uses_open_apw(wrapper):
    wrapper.open_file("C:/sims/process.apw", use_enhanced=True)

    assert ("open_apw", ("C:/sims/process.apw",)) in unit_of(wrapper).calls


def test_py2aspen_logging_goes_to_stderr_not_stdout(wrapper, capsys):
    wrapper.open_file("C:/sims/process.bkp", use_enhanced=True)
    wrapper.place_block("B1", "Mixer")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Connected to Aspen Plus" in captured.err
    assert "Executed action" in captured.err


def test_enhanced_falls_back_to_basic_when_py2aspen_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "py2aspen", None)  # import raises ImportError
    monkeypatch.delitem(sys.modules, "aspenplus_mcp.enhanced", raising=False)
    w = AspenPlusWrapper()
    w._is_windows = True
    w.win32com = types.SimpleNamespace(
        Dispatch=lambda progid: types.SimpleNamespace(InitFromArchive2=lambda path: None)
    )

    assert w.open_file("C:/sims/process.bkp", use_enhanced=True)
    assert w.session is None
    with pytest.raises(RuntimeError, match="Enhanced interface not available"):
        w.place_block("B1", "Mixer")


# --- node-path tools in enhanced mode -------------------------------------------


def test_get_value_works_in_enhanced_mode(opened):
    unit_of(opened).app.Tree.nodes["\\Data\\T"] = FakeNode(42.5)

    assert opened.aspen is unit_of(opened).app
    assert opened.get_value("\\Data\\T") == 42.5


def test_set_value_works_in_enhanced_mode(opened):
    opened.set_value("\\Data\\T", 25)

    assert unit_of(opened).app.Tree.nodes["\\Data\\T"].Value == 25


# --- flowsheet operations --------------------------------------------------------


@pytest.mark.parametrize(
    ("equipment_type", "expected_cls"),
    [("Mixer", "Mixer"), ("mixer", "Mixer"), ("RPLUG", "RPlug"), ("Splitter", "Splitter")],
)
def test_place_block_maps_type_case_insensitively(opened, equipment_type, expected_cls):
    opened.place_block("B1", equipment_type)

    [(op, block)] = unit_of(opened).executed
    assert op == "place"
    assert type(block).__name__ == expected_cls
    assert block.name == "B1"


def test_place_block_rejects_unknown_type(opened):
    with pytest.raises(ValueError, match="Unsupported equipment type 'Pump'.*Mixer"):
        opened.place_block("B1", "Pump")

    assert unit_of(opened).executed == []


@pytest.mark.parametrize(
    ("stream_type", "expected_cls"),
    [
        ("MATERIAL", "MaterialStream"),
        ("heat", "HeatStream"),
        ("WORK", "WorkStream"),
        ("POWER", "PowerStream"),
    ],
)
def test_place_stream_maps_type(opened, stream_type, expected_cls):
    opened.place_stream("S1", stream_type)

    [(op, stream)] = unit_of(opened).executed
    assert op == "place"
    assert type(stream).__name__ == expected_cls
    assert stream.name == "S1"


def test_place_stream_rejects_unknown_type(opened):
    with pytest.raises(ValueError, match="Unsupported stream type 'STEAM'"):
        opened.place_stream("S1", "STEAM")


def test_delete_block(opened, fake_py2aspen):
    opened.delete_block("B1")

    [(op, block)] = unit_of(opened).executed
    assert op == "delete"
    assert isinstance(block, fake_py2aspen.Block)
    assert block.name == "B1"


def test_connect_stream_passes_block_stream_and_port(opened, fake_py2aspen):
    opened.connect_stream("MIX-01", "S1", "F(IN)")

    [(op, block, stream, port)] = unit_of(opened).executed
    assert op == "connect"
    assert isinstance(block, fake_py2aspen.Block) and block.name == "MIX-01"
    assert isinstance(stream, fake_py2aspen.Stream) and stream.name == "S1"
    assert port == "F(IN)"


def test_run_simulation(opened):
    opened.run_simulation()

    assert unit_of(opened).calls[-1] == ("engine_run", ())


@pytest.mark.parametrize(
    ("filename", "expected_call"),
    [
        (None, ("save", ())),
        ("C:/out/copy.bkp", ("save_bkp", ("C:/out/copy.bkp",))),
        ("C:/out/copy.apw", ("save_as", ("C:/out/copy.apw", ("overwrite", True)))),
    ],
)
def test_save_simulation(opened, filename, expected_call):
    opened.save_simulation(filename)

    assert unit_of(opened).calls[-1] == expected_call


# --- close ------------------------------------------------------------------------


def test_close_in_enhanced_mode(opened):
    unit = unit_of(opened)

    opened.close()

    assert unit.calls[-1] == ("exit", ())
    assert opened.session is None
    assert opened.aspen is None


def test_enhanced_tools_require_enhanced_mode():
    w = AspenPlusWrapper()

    for call in (
        lambda: w.place_block("B1", "Mixer"),
        lambda: w.delete_block("B1"),
        lambda: w.place_stream("S1"),
        lambda: w.connect_stream("B1", "S1", "F(IN)"),
        lambda: w.save_simulation(),
    ):
        with pytest.raises(RuntimeError, match="Enhanced interface not available"):
            call()


# --- no orphaned Aspen instances ---------------------------------------------------


class FakeBasicDocument:
    """Stand-in for the pywin32 Apwn.Document used in basic mode."""

    def __init__(self) -> None:
        self.opened: list[str] = []
        self.closed = False

    def InitFromArchive2(self, path: str) -> None:
        self.opened.append(path)

    def Close(self) -> None:
        self.closed = True


def fake_win32com(documents: list[FakeBasicDocument]) -> types.SimpleNamespace:
    def dispatch(progid: str) -> FakeBasicDocument:
        documents.append(FakeBasicDocument())
        return documents[-1]

    return types.SimpleNamespace(Dispatch=dispatch)


def test_reopening_in_enhanced_mode_closes_previous_instance(opened, fake_py2aspen):
    first = unit_of(opened)

    opened.open_file("C:/sims/other.bkp", use_enhanced=True)

    assert first.calls[-1] == ("exit", ())
    assert unit_of(opened) is not first
    assert ("exit", ()) not in unit_of(opened).calls
    assert len(fake_py2aspen.UnitAspen.instances) == 2


def test_opening_basic_after_enhanced_closes_enhanced_instance(opened):
    enhanced_unit = unit_of(opened)
    documents: list[FakeBasicDocument] = []
    opened.win32com = fake_win32com(documents)

    opened.open_file("C:/sims/other.bkp", use_enhanced=False)

    assert enhanced_unit.calls[-1] == ("exit", ())
    assert opened.session is None
    assert opened.aspen is documents[0]
    assert documents[0].opened == ["C:/sims/other.bkp"]


def test_opening_enhanced_after_basic_closes_basic_document(wrapper):
    documents: list[FakeBasicDocument] = []
    wrapper.win32com = fake_win32com(documents)
    wrapper.open_file("C:/sims/basic.bkp", use_enhanced=False)

    wrapper.open_file("C:/sims/enhanced.bkp", use_enhanced=True)

    assert documents[0].closed
    assert wrapper.aspen is unit_of(wrapper).app


def test_basic_reopen_keeps_reusing_document(wrapper):
    documents: list[FakeBasicDocument] = []
    wrapper.win32com = fake_win32com(documents)

    wrapper.open_file("C:/sims/a.bkp")
    wrapper.open_file("C:/sims/b.bkp")

    assert len(documents) == 1
    assert documents[0].opened == ["C:/sims/a.bkp", "C:/sims/b.bkp"]
    assert not documents[0].closed


@pytest.mark.parametrize("failing_step", ["lazybind", "open_bkp", "set_visible"])
def test_failed_enhanced_open_closes_started_instance(wrapper, fake_py2aspen, failing_step):
    fake_py2aspen.UnitAspen.fail_on = {failing_step}
    wrapper.win32com = None  # no basic fallback available

    with pytest.raises(RuntimeError, match="pywin32 not available"):
        wrapper.open_file("C:/sims/missing.bkp", use_enhanced=True)

    [unit] = fake_py2aspen.UnitAspen.instances
    assert unit.calls[-1] == ("exit", ())
    assert wrapper.session is None


def test_failed_open_reraises_original_error_if_close_also_fails(fake_py2aspen):
    fake_py2aspen.UnitAspen.fail_on = {"open_bkp", "exit"}
    from aspenplus_mcp.enhanced import EnhancedSession

    with pytest.raises(RuntimeError, match="open_bkp failed"):
        EnhancedSession("Apwn.Document", "C:/sims/missing.bkp")
