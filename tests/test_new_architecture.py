"""Unit tests for JARVIS Modular Upgrades:
- GestureEngine & Safety Subsystem
- FileTransferManager & 2-step confirmation
- PermissionCenter & EmergencyStopManager
- ModelRouter & FallbackProvider
- PluginManager & Plugins
"""
import pytest
from backend.plugins.gesture import gesture_engine, GestureType
from backend.plugins.files import file_transfer_manager
from backend.core.permissions import permission_center
from backend.core.emergency_stop import emergency_stop_manager
from backend.ai.providers import model_router, FallbackProvider, MockProvider, GeminiProvider
from backend.plugins import plugin_manager


def test_gesture_engine_privacy_and_toggle():
    """Test camera permission toggle and status text."""
    res = gesture_engine.enable_camera(False)
    assert res["camera_enabled"] is False
    assert res["camera_active"] is False

    res = gesture_engine.enable_camera(True)
    assert res["camera_enabled"] is True
    assert res["camera_active"] is True

    # Disable camera back for safety
    gesture_engine.enable_camera(False)


def test_gesture_landmark_classification():
    """Test local 3D landmark landmark classification without camera frames."""
    gesture_engine.enable_camera(True)
    
    # 21 mock landmarks (open palm)
    landmarks_open_palm = [(0.5, 0.8 - i*0.03, 0.0) for i in range(21)]
    # Set tips higher than MCPs
    landmarks_open_palm[8] = (0.5, 0.2, 0.0)   # Index tip
    landmarks_open_palm[5] = (0.5, 0.4, 0.0)   # Index mcp
    landmarks_open_palm[12] = (0.5, 0.2, 0.0)  # Middle tip
    landmarks_open_palm[9] = (0.5, 0.4, 0.0)   # Middle mcp
    landmarks_open_palm[16] = (0.5, 0.2, 0.0)  # Ring tip
    landmarks_open_palm[13] = (0.5, 0.4, 0.0)  # Ring mcp
    landmarks_open_palm[20] = (0.5, 0.2, 0.0)  # Pinky tip
    landmarks_open_palm[17] = (0.5, 0.4, 0.0)  # Pinky mcp

    det = gesture_engine.process_landmarks(landmarks_open_palm)
    assert det.finger_count >= 4
    assert det.gesture == GestureType.OPEN_PALM

    gesture_engine.enable_camera(False)


def test_file_transfer_manager_safety_and_preview(tmp_path):
    """Test file transfer preview generation and credential file safety blocking."""
    # 1. Safe file transfer
    safe_file = tmp_path / "project.pdf"
    safe_file.write_text("dummy PDF content")

    preview = file_transfer_manager.prepare_transfer(
        file_path=str(safe_file),
        recipient="Rahul",
        channel="WhatsApp",
    )
    assert preview.is_safe is True
    assert preview.requires_confirmation is True
    assert "Rahul" in preview.prompt_message

    # Confirm transfer
    req = file_transfer_manager.confirm_pending_transfer()
    assert req is not None
    assert req.recipient == "Rahul"

    # 2. Blocked credentials file transfer (.env)
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_KEY=12345")

    blocked_preview = file_transfer_manager.prepare_transfer(
        file_path=str(env_file),
        recipient="Rahul",
        channel="WhatsApp",
    )
    assert blocked_preview.is_safe is False
    assert "sensitive pattern" in blocked_preview.safety_message


def test_permission_center():
    """Test permission center status listing and toggle."""
    perms = permission_center.get_all_permissions()
    assert len(perms) >= 8

    # Toggle camera permission
    assert permission_center.set_permission("camera", True) is True
    assert permission_center.permissions["camera"].enabled is True

    assert permission_center.set_permission("camera", False) is True
    assert permission_center.permissions["camera"].enabled is False


def test_emergency_stop_manager():
    """Test EmergencyStopManager halt and reset."""
    halt_res = emergency_stop_manager.trigger_stop("Test emergency halt")
    assert emergency_stop_manager.is_halted is True
    assert halt_res["status"] == "EMERGENCY_STOPPED"

    reset_res = emergency_stop_manager.reset_stop()
    assert emergency_stop_manager.is_halted is False
    assert reset_res["status"] == "ACTIVE"


def test_model_router():
    """Test task-based AI routing."""
    provider = model_router.route_provider("what is the battery status")
    assert provider is not None


def test_plugin_manager():
    """Test PluginManager discovery and list."""
    plugins = plugin_manager.list_plugins()
    assert len(plugins) >= 6
    names = [p["name"] for p in plugins]
    assert "browser" in names
    assert "media" in names
    assert "system" in names
