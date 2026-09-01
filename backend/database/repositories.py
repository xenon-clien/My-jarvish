"""Repository layer for database operations in JARVIS AI.

Abstracts raw SQLite queries into clean Python objects.
"""
from typing import Any, Dict, List, Optional
from backend.core.logger import get_logger
from backend.database.database import DatabaseManager, db_manager
from backend.database.models import ContactRecord, MemoryRecord, TaskHistoryRecord

logger = get_logger("Repositories")


class TaskHistoryRepository:
    """Handles CRUD operations for task execution audit history."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    def add_record(
        self,
        command: str,
        action: Optional[str] = None,
        status: str = "SUCCESS",
        result: Optional[str] = None,
        execution_time_ms: float = 0.0,
    ) -> TaskHistoryRecord:
        """Insert a new task execution record into task_history."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO task_history (command, action, status, result, execution_time_ms)
                VALUES (?, ?, ?, ?, ?)
                """,
                (command, action, status, result, execution_time_ms),
            )
            record_id = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT * FROM task_history WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            return TaskHistoryRecord(**dict(row))

    def get_recent(self, limit: int = 50) -> List[TaskHistoryRecord]:
        """Fetch the most recent task history records."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM task_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [TaskHistoryRecord(**dict(r)) for r in rows]

    def clear_history(self) -> int:
        """Clear all task history records and return count of deleted records."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM task_history")
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleared {deleted_count} records from task_history")
            return deleted_count

    def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics of task executions."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM task_history")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM task_history WHERE status = 'SUCCESS'")
            successful = cursor.fetchone()[0]

            cursor.execute("""
                SELECT action, COUNT(*) as count 
                FROM task_history 
                WHERE action IS NOT NULL 
                GROUP BY action 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_tools = [{"tool": r[0], "count": r[1]} for r in cursor.fetchall()]

            return {
                "total_commands": total,
                "successful_commands": successful,
                "success_rate_percent": round((successful / total * 100), 1) if total > 0 else 100.0,
                "top_tools": top_tools,
            }


class MemoryRepository:
    """Handles CRUD operations for long-term memory key-values."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    def set_memory(self, category: str, key: str, value: str) -> MemoryRecord:
        """Insert or update a memory item."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memories (category, key, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    category = excluded.category,
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (category.upper(), key.lower().strip(), value.strip()),
            )
            conn.commit()

            cursor.execute("SELECT * FROM memories WHERE key = ?", (key.lower().strip(),))
            row = cursor.fetchone()
            return MemoryRecord(**dict(row))

    def get_memory(self, key: str) -> Optional[MemoryRecord]:
        """Fetch a memory by key."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE key = ?", (key.lower().strip(),))
            row = cursor.fetchone()
            return MemoryRecord(**dict(row)) if row else None

    def list_all(self, category: Optional[str] = None) -> List[MemoryRecord]:
        """Fetch all memories, optionally filtered by category."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "SELECT * FROM memories WHERE category = ? ORDER BY key ASC",
                    (category.upper(),),
                )
            else:
                cursor.execute("SELECT * FROM memories ORDER BY category ASC, key ASC")
            rows = cursor.fetchall()
            return [MemoryRecord(**dict(r)) for r in rows]

    def delete_memory(self, key: str) -> bool:
        """Delete a memory item by key."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE key = ?", (key.lower().strip(),))
            conn.commit()
            return cursor.rowcount > 0


class ContactRepository:
    """Handles CRUD operations for user contacts and address book."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    def save_contact(
        self,
        name: str,
        phone: str,
        email: Optional[str] = None,
        relationship: Optional[str] = None,
    ) -> ContactRecord:
        """Create or update a contact in the database."""
        name_clean = name.strip().title()
        phone_clean = phone.strip().replace(" ", "").replace("-", "")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO contacts (name, phone, email, relationship)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    phone = excluded.phone,
                    email = COALESCE(excluded.email, contacts.email),
                    relationship = COALESCE(excluded.relationship, contacts.relationship)
                """,
                (name_clean, phone_clean, email, relationship),
            )
            conn.commit()

            cursor.execute("SELECT * FROM contacts WHERE name = ?", (name_clean,))
            row = cursor.fetchone()
            return ContactRecord(**dict(row))

    def get_contact(self, name: str) -> Optional[ContactRecord]:
        """Fetch contact by exact name or substring match."""
        name_clean = name.strip()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Try exact match first
            cursor.execute("SELECT * FROM contacts WHERE LOWER(name) = LOWER(?)", (name_clean,))
            row = cursor.fetchone()
            if row:
                return ContactRecord(**dict(row))

            # Try partial substring match
            cursor.execute("SELECT * FROM contacts WHERE LOWER(name) LIKE LOWER(?)", (f"%{name_clean}%",))
            row = cursor.fetchone()
            return ContactRecord(**dict(row)) if row else None

    def list_all(self) -> List[ContactRecord]:
        """Fetch all contacts sorted by name."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contacts ORDER BY name ASC")
            rows = cursor.fetchall()
            return [ContactRecord(**dict(r)) for r in rows]

    def delete_contact(self, name: str) -> bool:
        """Delete a contact by name."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM contacts WHERE LOWER(name) = LOWER(?)", (name.strip(),))
            conn.commit()
            return cursor.rowcount > 0


# Global repository instances
task_history_repo = TaskHistoryRepository()
memory_repo = MemoryRepository()
contact_repo = ContactRepository()
