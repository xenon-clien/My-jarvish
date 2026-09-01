"""Unit tests for Windows Power Management tools."""
import pytest
from backend.tools.power_tools import (
    cancel_shutdown,
    lock_pc,
    restart_pc,
    shutdown_pc,
    sleep_pc,
)


def test_shutdown_pc_mock(monkeypatch):
    """Test shutdown command generation with mock os.system."""
    executed_cmds = []
    monkeypatch.setattr("os.system", lambda cmd: executed_cmds.append(cmd))

    res = shutdown_pc(close_all_apps=False, delay_seconds=5)
    assert res["status"] == "success"
    assert any("shutdown /s /t 5" in cmd for cmd in executed_cmds)


def test_restart_pc_mock(monkeypatch):
    """Test restart command generation with mock os.system."""
    executed_cmds = []
    monkeypatch.setattr("os.system", lambda cmd: executed_cmds.append(cmd))

    res = restart_pc(close_all_apps=False, delay_seconds=10)
    assert res["status"] == "success"
    assert any("shutdown /r /t 10" in cmd for cmd in executed_cmds)


def test_lock_pc_mock(monkeypatch):
    """Test workstation locking command."""
    executed_cmds = []
    monkeypatch.setattr("os.system", lambda cmd: executed_cmds.append(cmd))

    res = lock_pc()
    assert res["status"] == "success"
    assert any("LockWorkStation" in cmd for cmd in executed_cmds)


def test_cancel_shutdown_mock(monkeypatch):
    """Test aborting scheduled shutdown."""
    executed_cmds = []
    monkeypatch.setattr("os.system", lambda cmd: executed_cmds.append(cmd))

    res = cancel_shutdown()
    assert res["status"] == "success"
    assert any("shutdown /a" in cmd for cmd in executed_cmds)
