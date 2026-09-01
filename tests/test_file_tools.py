"""Unit tests for sandboxed file tools and security boundary containment."""
from pathlib import Path
import pytest

from backend.ai.agent import AgentState, JarvisAgent
from backend.core.config import Settings
from backend.core.permissions import PermissionLevel, ToolPermissionPolicy
from backend.core.security import SecurityManager
from backend.tools.file_tools import (
    copy_file,
    create_folder,
    delete_file,
    find_files,
    get_file_info,
    list_directory,
    move_file,
    read_file_content,
    rename_file,
)
from backend.tools.registry import default_registry


@pytest.fixture
def sandbox_env(tmp_path):
    """Fixture providing an isolated sandbox directory configured in Settings."""
    allowed_dir = tmp_path / "allowed_folder"
    allowed_dir.mkdir()
    settings = Settings(ALLOWED_DIRECTORIES=[str(allowed_dir)])
    sec_mgr = SecurityManager(settings=settings)
    return {
        "root": allowed_dir,
        "settings": settings,
        "security": sec_mgr,
        "forbidden": tmp_path / "forbidden_folder",
    }


def test_path_boundary_enforcement(sandbox_env):
    """Ensure accessing paths outside configured allowed directories is strictly blocked."""
    sec_mgr = sandbox_env["security"]
    allowed = sandbox_env["root"] / "test.txt"
    forbidden = sandbox_env["forbidden"] / "secret.txt"

    assert sec_mgr.is_path_allowed(allowed) is True
    assert sec_mgr.is_path_allowed(forbidden) is False
    assert sec_mgr.is_path_allowed("C:/Windows/System32") is False


def test_file_crud_operations(tmp_path, monkeypatch):
    """Test folder creation, file writing, info, copying, moving, renaming, and reading."""
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir()

    # Monkeypatch security manager to allow this temp directory
    from backend.core import security
    custom_sec = SecurityManager(settings=Settings(ALLOWED_DIRECTORIES=[str(test_dir)]))
    monkeypatch.setattr(security, "security_manager", custom_sec)
    monkeypatch.setattr("backend.tools.file_tools.security_manager", custom_sec)

    # 1. Create Folder
    sub_folder = test_dir / "my_docs"
    res_create = create_folder(str(sub_folder))
    assert res_create["status"] == "success"
    assert sub_folder.exists()

    # 2. Write test file
    sample_file = sub_folder / "notes.txt"
    sample_file.write_text("Line 1: JARVIS AI\nLine 2: Python Mentorship\nLine 3: Windows Assistant\n", encoding="utf-8")

    # 3. Read File Content
    read_res = read_file_content(str(sample_file), max_lines=2)
    assert read_res["lines_read"] == 2
    assert "Line 1: JARVIS AI" in read_res["content"]

    # 4. File Info
    info_res = get_file_info(str(sample_file))
    assert info_res["is_file"] is True
    assert info_res["extension"] == ".txt"

    # 5. List Directory
    list_res = list_directory(str(sub_folder))
    assert list_res["total_items"] == 1
    assert list_res["items"][0]["name"] == "notes.txt"

    # 6. Find Files
    find_res = find_files(query="notes", search_directory=str(test_dir))
    assert find_res["matches_found"] == 1
    assert "notes.txt" in find_res["files"][0]["name"]

    # 7. Rename File
    renamed_res = rename_file(str(sample_file), "renamed_notes.txt")
    assert renamed_res["status"] == "success"
    assert (sub_folder / "renamed_notes.txt").exists()
    assert not sample_file.exists()

    # 8. Copy File
    copy_dest = test_dir / "copied_notes.txt"
    copy_res = copy_file(str(sub_folder / "renamed_notes.txt"), str(copy_dest))
    assert copy_res["status"] == "success"
    assert copy_dest.exists()

    # 9. Move File
    move_dest = test_dir / "moved_notes.txt"
    move_res = move_file(str(copy_dest), str(move_dest))
    assert move_res["status"] == "success"
    assert move_dest.exists()
    assert not copy_dest.exists()

    # 10. Delete File (Level 3 tool directly executed)
    del_res = delete_file(str(move_dest))
    assert del_res["status"] == "success"
    assert not move_dest.exists()


@pytest.mark.asyncio
async def test_delete_confirmation_workflow(tmp_path, monkeypatch):
    """Test that delete_file triggers mandatory confirmation when executed by JarvisAgent."""
    test_dir = tmp_path / "delete_sandbox"
    test_dir.mkdir()
    target_file = test_dir / "important_document.txt"
    target_file.write_text("Critical data", encoding="utf-8")

    from backend.core import security
    custom_sec = SecurityManager(settings=Settings(ALLOWED_DIRECTORIES=[str(test_dir)]))
    monkeypatch.setattr(security, "security_manager", custom_sec)
    monkeypatch.setattr("backend.tools.file_tools.security_manager", custom_sec)

    settings = Settings(
        ALLOWED_DIRECTORIES=[str(test_dir)],
        AUTO_CONFIRM_LEVEL_3=False,
        AI_PROVIDER="mock",
    )

    from backend.ai.providers import BaseAIResponse, MockProvider, ToolCall

    class DeleteMock(MockProvider):
        async def generate_response(self, messages, tools_schema=None):
            return BaseAIResponse(
                content="Requesting deletion...",
                tool_calls=[ToolCall(name="delete_file", arguments={"file_path": str(target_file)})],
            )

    agent = JarvisAgent(
        settings=settings,
        provider=DeleteMock(settings=settings),
        registry=default_registry,
        permission_policy=ToolPermissionPolicy(settings=settings),
    )

    # Step 1: User says delete -> Agent must pause with AWAITING_CONFIRMATION
    resp1 = await agent.process_user_input("Delete my file")
    assert resp1.state == AgentState.AWAITING_CONFIRMATION
    assert agent.pending_action is not None
    assert target_file.exists()  # File MUST NOT be deleted yet

    # Step 2: User says yes -> Agent approves and executes deletion
    resp2 = await agent.process_user_input("yes")
    assert resp2.state == AgentState.SPEAKING
    assert not target_file.exists()  # File is now deleted
