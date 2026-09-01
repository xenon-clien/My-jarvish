"""Database connection and initialization module for JARVIS AI."""
import sqlite3
from pathlib import Path
from typing import Optional

from backend.core.config import Settings, get_settings
from backend.core.logger import get_logger

logger = get_logger("Database")


class DatabaseManager:
    """Manages SQLite database connections and baseline schema initialization."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            project_root = Path(__file__).resolve().parent.parent.parent
            self.db_path = str(project_root / "jarvis.db")

        self._initialized = False

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a new SQLite database connection, ensuring tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if not self._initialized:
            self._create_tables_if_needed(conn)
            self._initialized = True

        return conn

    def _create_tables_if_needed(self, conn: sqlite3.Connection) -> None:
        """Create initial database tables if they do not already exist."""
        cursor = conn.cursor()

        # Task History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                command TEXT NOT NULL,
                action TEXT,
                status TEXT NOT NULL,
                result TEXT,
                execution_time_ms REAL
            );
        """)

        # Key-Value Memory Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'GENERAL',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Contacts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                relationship TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Auto-seed core contacts (Harsh and Shivam)
        cursor.execute("""
            INSERT OR IGNORE INTO contacts (name, phone, relationship)
            VALUES 
                ('Harsh', '8054840494', 'friend'),
                ('Shivam', '9501445740', 'owner')
        """)
        conn.commit()

    def initialize_schema(self) -> None:
        """Explicitly create database tables."""
        with self.get_connection() as conn:
            self._create_tables_if_needed(conn)
            logger.info("Initialized SQLite database schema successfully.")


# Global instance
db_manager = DatabaseManager()
