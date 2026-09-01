"""Unit tests for tool permission and confirmation policy."""
from backend.core.config import Settings
from backend.core.permissions import PermissionLevel, ToolPermissionPolicy


def test_level_0_auto_confirm():
    """Verify Level 0 is auto-approved when flag is enabled."""
    settings = Settings(AUTO_CONFIRM_LEVEL_0=True)
    policy = ToolPermissionPolicy(settings=settings)
    result = policy.evaluate("get_current_time", PermissionLevel.LEVEL_0_SAFE)
    assert result.allowed is True
    assert result.requires_confirmation is False


def test_level_3_requires_confirmation_by_default():
    """Verify Level 3 destructive action requires confirmation."""
    settings = Settings(AUTO_CONFIRM_LEVEL_3=False)
    policy = ToolPermissionPolicy(settings=settings)
    result = policy.evaluate("delete_file", PermissionLevel.LEVEL_3_DESTRUCTIVE, "file.txt")
    assert result.allowed is True
    assert result.requires_confirmation is True
    assert "WARNING" in (result.confirmation_message or "")
