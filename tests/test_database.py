"""Unit tests for SQLite database operations, repositories, and persistence."""
import pytest
from backend.database.database import DatabaseManager
from backend.database.repositories import MemoryRepository, TaskHistoryRepository


@pytest.fixture
def temp_db(tmp_path):
    """Fixture providing a temporary SQLite database manager."""
    db_file = tmp_path / "test_jarvis.db"
    mgr = DatabaseManager(db_path=str(db_file))
    mgr.initialize_schema()
    return mgr


def test_task_history_repository(temp_db):
    """Test inserting, querying, and clearing task history records."""
    repo = TaskHistoryRepository(db=temp_db)

    # Insert record
    rec = repo.add_record(
        command="What time is it?",
        action="get_current_time",
        status="SUCCESS",
        result="09:30 AM",
        execution_time_ms=12.5,
    )
    assert rec.id is not None
    assert rec.command == "What time is it?"
    assert rec.action == "get_current_time"

    # Query recent
    recent = repo.get_recent(limit=10)
    assert len(recent) == 1
    assert recent[0].command == "What time is it?"

    # Stats
    stats = repo.get_stats()
    assert stats["total_commands"] == 1
    assert stats["successful_commands"] == 1

    # Clear
    deleted = repo.clear_history()
    assert deleted == 1
    assert len(repo.get_recent()) == 0


def test_memory_repository(temp_db):
    """Test key-value memory store."""
    repo = MemoryRepository(db=temp_db)

    # Set memory
    mem = repo.set_memory(
        category="USER_PREFERENCE",
        key="default_browser",
        value="Google Chrome",
    )
    assert mem.key == "default_browser"
    assert mem.value == "Google Chrome"

    # Get memory
    fetched = repo.get_memory("default_browser")
    assert fetched is not None
    assert fetched.value == "Google Chrome"

    # Update memory
    repo.set_memory(
        category="USER_PREFERENCE",
        key="default_browser",
        value="Brave Browser",
    )
    updated = repo.get_memory("default_browser")
    assert updated.value == "Brave Browser"

    # Delete memory
    assert repo.delete_memory("default_browser") is True
    assert repo.get_memory("default_browser") is None
