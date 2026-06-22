import logging
import aiosqlite

logger = logging.getLogger(__name__)


class UserRepo:
    """Repository for managing user-related data and settings."""

    def __init__(self, db: aiosqlite.Connection):
        """Initialize the UserRepo with a database connection."""
        self.db = db

    # --- USER OPERATIONS ---

    async def create_user(self, name: str, email: str) -> int | None:
        """Create a new user and return the ID."""
        cursor = await self.db.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (name, email.strip().lower()),
        )
        await self.db.commit()
        user_id = cursor.lastrowid
        logger.info("User %d (%s) created", user_id, name)
        return user_id

    async def get_user_by_email(self, email: str) -> dict | None:
        """Retrieve user by email."""
        cursor = await self.db.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_user(self, user_id: int) -> dict | None:
        """Retrieve basic user information."""
        cursor = await self.db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def delete_user(self, user_id: int):
        """Delete a user. Related data will be deleted via ON DELETE CASCADE."""
        await self.db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await self.db.commit()
        logger.info("User %d deleted", user_id)

    async def list_users(self) -> list[dict]:
        """Get all registered users."""
        cursor = await self.db.execute("SELECT id, name, email FROM users")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def update_user_name(self, user_id: int, name: str):
        """Update user display name."""
        await self.db.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
        await self.db.commit()
        logger.info("User %d name updated to %s", user_id, name)

    async def update_user_email(self, user_id: int, email: str):
        """Update user email."""
        await self.db.execute("UPDATE users SET email = ? WHERE id = ?", (email.strip().lower(), user_id))
        await self.db.commit()
        logger.info("User %d email updated to %s", user_id, email)

    async def update_user_telegram_chat_id(self, user_id: int, telegram_chat_id: str | None):
        """Update user Telegram Chat ID."""
        await self.db.execute("UPDATE users SET telegram_chat_id = ? WHERE id = ?", (telegram_chat_id, user_id))
        await self.db.commit()
        logger.info("User %d telegram_chat_id updated to %s", user_id, telegram_chat_id)

    async def get_users_with_telegram(self) -> list[dict]:
        """Get all users who have registered a Telegram chat ID."""
        cursor = await self.db.execute("SELECT id, telegram_chat_id FROM users WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id != ''")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


    # --- SETTINGS OPERATIONS ---

    async def _ensure_settings(self, user_id: int, language: str):
        """Internal helper to ensure the settings row exists for user/language."""
        await self.db.execute(
            "INSERT OR IGNORE INTO user_settings (user_id, language) VALUES (?, ?)",
            (user_id, language),
        )

    async def get_settings(self, user_id: int, language: str) -> dict:
        """Retrieve user settings, creates defaults if not found."""
        await self._ensure_settings(user_id, language)
        await self.db.commit()

        cursor = await self.db.execute(
            "SELECT * FROM user_settings WHERE user_id = ? AND language = ?",
            (user_id, language),
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}

    async def update_settings(self, user_id: int, language: str, daily_limit: int | None = None, notification_time: int | None = None, notification_threshold: int | None = None):
        """Update user settings (limit, notification time and notification threshold) gracefully."""
        # 1. Ensure the setting row exists
        await self._ensure_settings(user_id, language)

        # 2. Dynamically update only provided fields
        fields = []
        params = []
        if daily_limit is not None:
            fields.append("daily_limit = ?")
            params.append(daily_limit)
        if notification_time is not None:
            fields.append("notification_time = ?")
            params.append(notification_time)
        if notification_threshold is not None:
            fields.append("notification_threshold = ?")
            params.append(notification_threshold)
        
        if fields:
            params.extend([user_id, language])
            query = f"UPDATE user_settings SET {', '.join(fields)} WHERE user_id = ? AND language = ?"
            await self.db.execute(query, params)
        
        await self.db.commit()
        
        # Enhanced logging
        user = await self.get_user(user_id)
        username = user.get('name', 'Unknown') if user else 'Unknown'
        changes = []
        if daily_limit is not None: changes.append(f"limit={daily_limit}")
        if notification_time is not None: changes.append(f"notif={notification_time}m")
        if notification_threshold is not None: changes.append(f"threshold={notification_threshold}")
        
        logger.info("Settings updated: %s [%s] -> %s", username, language, ", ".join(changes))

    async def get_all_user_languages(self, user_id: int) -> list[str]:
        """Get a list of all languages the user is currently learning."""
        cursor = await self.db.execute(
            "SELECT language FROM user_settings WHERE user_id = ? ORDER BY rowid",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [row["language"] for row in rows]
