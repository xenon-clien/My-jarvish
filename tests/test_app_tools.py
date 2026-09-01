"""Unit tests for safe Windows application control and allowlist enforcement."""
import pytest
from backend.tools.app_tools import (
    app_registry,
    clean_unused_apps,
    close_application,
    list_running_applications,
    open_application,
    register_application,
)


def test_app_registry_alias_resolution():
    """Test resolving application aliases and nicknames to registered entries."""
    chrome = app_registry.resolve_app("chrome")
    assert chrome is not None
    assert chrome["name"] == "Google Chrome"

    browser = app_registry.resolve_app("browser")
    assert browser is not None
    assert browser["name"] == "Google Chrome"

    vscode = app_registry.resolve_app("code editor")
    assert vscode is not None
    assert vscode["name"] == "Visual Studio Code"

    calc = app_registry.resolve_app("calc")
    assert calc is not None
    assert calc["name"] == "Windows Calculator"


def test_unregistered_app_rejection():
    """Ensure unauthorized applications outside the allowlist are strictly rejected."""
    with pytest.raises(PermissionError) as exc_info:
        open_application("unauthorized_trojan.exe")
    assert "not in the authorized application allowlist" in str(exc_info.value)


def test_register_new_application():
    """Test dynamically adding a custom application to the allowlist."""
    res = register_application(
        app_name="Custom Tool",
        executable_path="C:/Tools/custom.exe",
        aliases=["my tool", "custom"],
    )
    assert res["status"] == "success"

    resolved = app_registry.resolve_app("my tool")
    assert resolved is not None
    assert resolved["name"] == "Custom Tool"


def test_list_running_applications():
    """Test inspecting running desktop processes."""
    res = list_running_applications(limit=10)
    assert "applications" in res
    assert "total_active" in res
    assert isinstance(res["applications"], list)
    if res["applications"]:
        assert "pid" in res["applications"][0]
        assert "name" in res["applications"][0]


def test_clean_unused_apps():
    """Test bulk cleaning of idle taskbar applications."""
    res = clean_unused_apps(close_browsers=False)
    assert res["status"] == "success"
    assert "closed_count" in res
    assert "message" in res


def test_open_and_close_app_mock(monkeypatch):
    """Test launching and terminating applications with mocked system calls."""
    launched_commands = []

    def mock_system(cmd):
        launched_commands.append(cmd)
        return 0

    monkeypatch.setattr("os.system", mock_system)
    monkeypatch.setattr("os.startfile", mock_system, raising=False)

    # Launch Calculator
    res_open = open_application("calculator")
    assert res_open["status"] == "success"
    assert "Calculator" in res_open["application"]

    # Close non-existent app
    res_close = close_application("non_existent_app_name_12345")
    assert res_close["status"] == "not_found"
