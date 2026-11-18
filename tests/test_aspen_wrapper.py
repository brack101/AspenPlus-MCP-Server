"""Tests for AspenPlusWrapper's integration of the vendored aspen_interface library.

The real library needs Windows + Aspen Plus, so it is replaced by a fake module
that reproduces its problematic side effects: print() to stdout and os.chdir().
"""

import os
import sys
import types
from typing import Any

import pytest

from aspenplus_mcp.aspen_wrapper import AspenPlusWrapper


class FakeNode:
    def __init__(self, value: Any = None) -> None:
        self.Value = value


class FakeTree:
    def __init__(self) -> None:
        self.nodes: dict[str, FakeNode] = {}

    def FindNode(self, path: str) -> FakeNode:
        return self.nodes.setdefault(path, FakeNode())


class FakeDocument:
    """Stand-in for the Apwn.Document COM object."""

    def __init__(self) -> None:
        self.Tree = FakeTree()
        self.closed = False

    def Close(self, *args: Any) -> None:
        self.closed = True


class FakeSimulation:
    """Mimics aspen_interface.Simulation, including its side effects."""

    def __init__(self, AspenFileName: str, WorkingDirectoryPath: str, VISIBILITY: bool = True):
        print("The current Directory is :  ")
        os.chdir(WorkingDirectoryPath)
        print("The Aspen is active now.")
        self.AspenSimulation = FakeDocument()
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def _noisy(self, name: str, *args: Any) -> None:
        print(f"{name} {args}")
        self.calls.append((name, args))

    def CloseAspen(self) -> None:
        self._noisy("CloseAspen")
        self.AspenSimulation.closed = True

    def EngineRun(self) -> None:
        self._noisy("EngineRun")

    def BlockPlace(self, *args: Any) -> None:
        self._noisy("BlockPlace", *args)

    def BlockDelete(self, *args: Any) -> None:
        self._noisy("BlockDelete", *args)

    def StreamPlace(self, *args: Any) -> None:
        self._noisy("StreamPlace", *args)

    def StreamConnect(self, *args: Any) -> None:
        self._noisy("StreamConnect", *args)

    def Save(self) -> None:
        self._noisy("Save")

    def SaveAs(self, *args: Any) -> None:
        self._noisy("SaveAs", *args)


class FailingSimulation(FakeSimulation):
    def BlockPlace(self, *args: Any) -> None:
        os.chdir("/")
        print("about to fail")
        raise RuntimeError("COM error")


@pytest.fixture
def fake_library(monkeypatch):
    """Install a fake aspenplus_mcp.aspen_interface module."""
    module = types.ModuleType("aspenplus_mcp.aspen_interface")
    module.Simulation = FakeSimulation
    monkeypatch.setitem(sys.modules, "aspenplus_mcp.aspen_interface", module)
    return module


@pytest.fixture
def wrapper(fake_library) -> AspenPlusWrapper:
    """Wrapper that believes it runs on Windows with pywin32 available."""
    w = AspenPlusWrapper()
    w._is_windows = True
    w.win32com = object()
    return w


@pytest.fixture
def sim_file(tmp_path) -> str:
    sim_dir = tmp_path / "sims"
    sim_dir.mkdir()
    return str(sim_dir / "process.bkp")


@pytest.fixture
def opened(wrapper, sim_file, capsys) -> AspenPlusWrapper:
    wrapper.open_file(sim_file, use_enhanced=True)
    capsys.readouterr()  # discard output from opening
    return wrapper


# --- open -----------------------------------------------------------------


def test_enhanced_open_keeps_stdout_clean(wrapper, sim_file, capsys):
    wrapper.open_file(sim_file, use_enhanced=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "The Aspen is active now." in captured.err


def test_enhanced_open_restores_working_directory(wrapper, sim_file):
    cwd = os.getcwd()

    wrapper.open_file(sim_file, use_enhanced=True)

    assert os.getcwd() == cwd


def test_enhanced_open_passes_file_and_directory(wrapper, sim_file, monkeypatch):
    seen = {}

    class RecordingSimulation(FakeSimulation):
        def __init__(self, AspenFileName, WorkingDirectoryPath, VISIBILITY=True):
            seen.update(name=AspenFileName, dir=WorkingDirectoryPath, visible=VISIBILITY)
            super().__init__(AspenFileName, WorkingDirectoryPath, VISIBILITY)

    monkeypatch.setattr(
        sys.modules["aspenplus_mcp.aspen_interface"], "Simulation", RecordingSimulation
    )

    wrapper.open_file(sim_file, use_enhanced=True)

    assert seen == {"name": "process.bkp", "dir": os.path.dirname(sim_file), "visible": False}


# --- node-path tools in enhanced mode ---------------------------------------


def test_get_value_works_in_enhanced_mode(opened):
    doc = opened.simulation.AspenSimulation
    doc.Tree.nodes["\\Data\\T"] = FakeNode(42.5)

    assert opened.aspen is doc
    assert opened.get_value("\\Data\\T") == 42.5


def test_set_value_works_in_enhanced_mode(opened):
    opened.set_value("\\Data\\T", 25)

    assert opened.simulation.AspenSimulation.Tree.nodes["\\Data\\T"].Value == 25


# --- vendored calls ---------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "args", "expected_call"),
    [
        ("run_simulation", (), ("EngineRun", ())),
        ("place_block", ("B1", "Mixer"), ("BlockPlace", ("B1", "Mixer"))),
        ("delete_block", ("B1",), ("BlockDelete", ("B1",))),
        ("place_stream", ("S1", "MATERIAL"), ("StreamPlace", ("S1", "MATERIAL"))),
        ("connect_stream", ("B1", "S1", "IN1"), ("StreamConnect", ("B1", "S1", "IN1"))),
        ("save_simulation", (), ("Save", ())),
        ("save_simulation", ("out.bkp",), ("SaveAs", ("out.bkp",))),
    ],
)
def test_vendored_calls_keep_stdout_clean(opened, capsys, method, args, expected_call):
    getattr(opened, method)(*args)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert expected_call[0] in captured.err
    assert opened.simulation.calls == [expected_call]


def test_working_directory_restored_when_library_raises(wrapper, sim_file, capsys, monkeypatch):
    monkeypatch.setattr(
        sys.modules["aspenplus_mcp.aspen_interface"], "Simulation", FailingSimulation
    )
    wrapper.open_file(sim_file, use_enhanced=True)
    cwd = os.getcwd()

    with pytest.raises(RuntimeError, match="COM error"):
        wrapper.place_block("B1", "Mixer")

    assert os.getcwd() == cwd
    assert capsys.readouterr().out == ""


# --- close ------------------------------------------------------------------


def test_close_in_enhanced_mode(opened, capsys):
    doc = opened.simulation.AspenSimulation

    opened.close()

    assert doc.closed
    assert opened.simulation is None
    assert opened.aspen is None
    assert capsys.readouterr().out == ""


def test_stdout_restored_after_vendored_call(opened):
    stdout = sys.stdout

    opened.place_block("B1", "Mixer")

    assert sys.stdout is stdout
