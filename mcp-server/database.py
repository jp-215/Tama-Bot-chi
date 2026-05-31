"""
Database management for SQLite.
Handles user preferences and interaction logs.
"""
import aiosqlite
import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from config import Config

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for user preferences and interaction logs."""

    def __init__(self, db_path: str = Config.SQLITE_DB_PATH):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()

    def _ensure_db_directory(self) -> None:
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """
        Initialize database schema.

        Creates tables for user preferences and interaction logs if they don't exist.
        """
        async with aiosqlite.connect(self.db_path) as db:
            # User preferences table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    conversation_style TEXT NOT NULL,
                    permissions TEXT NOT NULL,
                    high_match_threshold REAL DEFAULT 0.75,
                    auto_schedule_enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Interaction logs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS interaction_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    other_user_id TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Index for faster queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_interactions_user_id
                ON interaction_logs(user_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_interactions_other_user_id
                ON interaction_logs(other_user_id)
            """)

            await db.commit()
            logger.info("Database initialized successfully")

    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user preferences from database.

        Args:
            user_id: User ID

        Returns:
            User preferences dict or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return {
                'user_id': row['user_id'],
                'conversation_style': json.loads(row['conversation_style']),
                'permissions': json.loads(row['permissions']),
                'high_match_threshold': row['high_match_threshold'],
                'auto_schedule_enabled': bool(row['auto_schedule_enabled'])
            }

    async def upsert_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """
        Insert or update user preferences.

        Args:
            user_id: User ID
            preferences: Preferences dictionary

        Returns:
            True if successful
        """
        async with aiosqlite.connect(self.db_path) as db:
            conversation_style = json.dumps(preferences.get('conversation_style', {}))
            permissions = json.dumps(preferences.get('permissions', {}))
            high_match_threshold = preferences.get('high_match_threshold', 0.75)
            auto_schedule_enabled = preferences.get('auto_schedule_enabled', True)

            await db.execute("""
                INSERT INTO user_preferences (
                    user_id, conversation_style, permissions,
                    high_match_threshold, auto_schedule_enabled, updated_at
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    conversation_style = excluded.conversation_style,
                    permissions = excluded.permissions,
                    high_match_threshold = excluded.high_match_threshold,
                    auto_schedule_enabled = excluded.auto_schedule_enabled,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, conversation_style, permissions, high_match_threshold, auto_schedule_enabled))

            await db.commit()
            return True

    async def log_interaction(
        self,
        user_id: str,
        other_user_id: str,
        interaction_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an interaction between users.

        Args:
            user_id: Primary user ID
            other_user_id: Other user ID
            interaction_type: Type of interaction
            metadata: Optional metadata

        Returns:
            Interaction log ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            metadata_json = json.dumps(metadata or {})

            cursor = await db.execute("""
                INSERT INTO interaction_logs (
                    user_id, other_user_id, interaction_type, metadata
                )
                VALUES (?, ?, ?, ?)
            """, (user_id, other_user_id, interaction_type, metadata_json))

            await db.commit()
            return cursor.lastrowid

    async def get_interaction_history(
        self,
        user_id: str,
        other_user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get interaction history for a user.

        Args:
            user_id: User ID
            other_user_id: Optional filter for specific other user
            limit: Maximum number of interactions to return

        Returns:
            List of interaction log dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if other_user_id:
                cursor = await db.execute("""
                    SELECT * FROM interaction_logs
                    WHERE user_id = ? AND other_user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id, other_user_id, limit))
            else:
                cursor = await db.execute("""
                    SELECT * FROM interaction_logs
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id, limit))

            rows = await cursor.fetchall()

            return [
                {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'other_user_id': row['other_user_id'],
                    'interaction_type': row['interaction_type'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at']
                }
                for row in rows
            ]


# Global database instance
db = Database()
