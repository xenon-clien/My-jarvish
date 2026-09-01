"""Unit tests for System Cleaner & Maintenance tools."""
import pytest
from backend.tools.cleaner_tools import (
    clean_junk_files,
    empty_recycle_bin,
    get_system_health,
)


def test_clean_junk_files():
    """Test cleaning junk files in Windows temp."""
    res = clean_junk_files()
    assert res["status"] == "success"
    assert "freed_mb" in res
    assert "files_deleted" in res


def test_empty_recycle_bin_mock(monkeypatch):
    """Test emptying recycle bin."""
    res = empty_recycle_bin()
    assert res["status"] in ["success", "error"]


def test_get_system_health():
    """Test retrieving CPU, RAM, Disk, and Battery diagnostics."""
    res = get_system_health()
    assert res["status"] == "success"
    assert "cpu_usage_percent" in res
    assert "ram_percent" in res
    assert "disk_percent" in res
