import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
import aiosqlite
from core.srs import SRSStatus


logger = logging.getLogger(__name__)

class WordRepo:
    """Repository for managing word-related data and statistics."""

    def __init__(self, db: aiosqlite.Connection, tz: ZoneInfo = ZoneInfo("UTC")):
        """Initialize the WordRepo with a database connection."""
        self.db = db
        self.tz = tz

    # --- READ & SEARCH OPERATIONS ---

    async def get_word(self, word_id: int, user_id: int) -> dict | None:
        """Retrieve a single word by its ID."""
        cursor = await self.db.execute(
            "SELECT * FROM words WHERE id = ? AND user_id = ?",
            (word_id, user_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_word_by_text(self, user_id: int, language: str, word: str) -> dict | None:
        """Retrieve a word by its exact spelling (case-insensitive) for a user and language."""
        cursor = await self.db.execute(
            "SELECT * FROM words WHERE user_id = ? AND language = ? AND LOWER(word) = LOWER(?)",
            (user_id, language, word.strip()),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def search_words(self, user_id: int, language: str, query: str) -> list[dict]:
        """Search for words in the user's dictionary by word or translation."""
        q = f"%{query.lower()}%"
        cursor = await self.db.execute(
            """SELECT id, word, translation, example, level FROM words
                WHERE user_id = ? AND language = ?
                AND (LOWER(word) LIKE ? OR LOWER(translation) LIKE ?)
                ORDER BY word ASC LIMIT 100""",
            (user_id, language, q, q),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_words_by_status(self, user_id: int, language: str, status: str) -> list[dict]:
        """Get words filtered by learning status (total, difficult, learning, mastered)."""
        where_clause = ""
        if status == SRSStatus.TOTAL:
            where_clause = ""  # Show all words
        elif status == SRSStatus.DIFFICULT:
            where_clause = "AND started_at IS NOT NULL AND easiness <= 1.3"
        elif status == SRSStatus.LEARNING:
            where_clause = "AND started_at IS NOT NULL AND interval < 30"
        elif status == SRSStatus.MASTERED:
            where_clause = "AND started_at IS NOT NULL AND interval >= 30"
        else:
            return []

        cursor = await self.db.execute(
            f"""SELECT id, word, translation, example, level FROM words
                WHERE user_id = ? AND language = ? {where_clause}
                ORDER BY word ASC LIMIT 500""",
            (user_id, language),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_today_words(
        self, user_id: int, language: str, field: str = "created_at", tz: ZoneInfo | None = None
    ) -> list[dict]:
        """Get words filtered by the date field (created_at, started_at, or last_reviewed_at) for today (UTC)."""
        if field == "created_at":
            query = """SELECT id, word, translation, example, level FROM words
                       WHERE user_id = ? AND language = ? AND created_at >= ?
                       ORDER BY created_at DESC"""
        elif field == "started_at":
            query = """SELECT id, word, translation, example, level FROM words
                       WHERE user_id = ? AND language = ? AND started_at >= ?
                       ORDER BY started_at DESC"""
        elif field == "last_reviewed_at":
            query = """SELECT id, word, translation, example, level FROM words
                       WHERE user_id = ? AND language = ? AND last_reviewed_at >= ?
                       ORDER BY last_reviewed_at DESC"""
        else:
            raise ValueError("Invalid date field: %s" % field)

        current_tz = tz or self.tz
        start_local = datetime.now(tz=current_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start_local.astimezone(UTC)
        cursor = await self.db.execute(query, (user_id, language, start_utc.isoformat()))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _get_now() -> str:
        """Helper to get current UTC time in ISO format."""
        return datetime.now(tz=UTC).isoformat()

    async def _get_username(self, user_id: int) -> str:
        """Internal helper to get username for logging."""
        cursor = await self.db.execute("SELECT name FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return row["name"] if row else f"ID {user_id}"

    # --- ADD OPERATIONS ---

    async def add_single_word(
        self,
        user_id: int,
        language: str,
        word: str,
        translation: str,
        example: str | None = None,
        level: str | None = None,
    ) -> int | None:
        """Add a single word and return its database ID."""
        now = self._get_now()
        cursor = await self.db.execute(
            """INSERT OR IGNORE INTO words
                (user_id, word, translation, language, example, level, next_review, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, word, translation, language, example, level, now, now),
        )
        await self.db.commit()
        if cursor.rowcount > 0:
            word_id = cursor.lastrowid
            username = await self._get_username(user_id)
            logger.info("Word added: %s [%s] -> \"%s\"", username, language, word)
            return word_id

        return None

    # --- PRACTICE & SESSION OPERATIONS ---

    async def get_session_words(self, user_id: int, language: str, new_limit: int) -> list[dict]:
        """Get words for a practice session, including due reviews and new words."""
        now = self._get_now()
        cursor = await self.db.execute(
            """SELECT id, word, translation, example, level, repetitions, started_at,
                      easiness, interval, next_review, last_reviewed_at
                FROM words
                WHERE user_id = ? AND language = ? AND started_at IS NOT NULL AND next_review <= ?
                ORDER BY next_review ASC""",
            (user_id, language, now),
        )
        due = [dict(row) for row in await cursor.fetchall()]

        new_words = []
        if new_limit > 0:
            cursor = await self.db.execute(
                """SELECT id, word, translation, example, level, repetitions, started_at,
                          easiness, interval, next_review, last_reviewed_at
                    FROM words
                    WHERE user_id = ? AND language = ? AND started_at IS NULL
                    ORDER BY RANDOM()
                    LIMIT ?""",
                (user_id, language, new_limit),
            )
            new_words = [dict(row) for row in await cursor.fetchall()]

        username = await self._get_username(user_id)
        logger.info("Session started: %s [%s] (%d due, %d new)", username, language, len(due), len(new_words))
        return due + new_words

    async def update_word_after_review(
        self,
        user_id: int,
        word_id: int,
        repetitions: int,
        easiness: float,
        interval: int,
        next_review: str,
    ) -> None:
        """Update word statistics after a review session."""
        now = self._get_now()
        
        # Get word text before update for better logging
        word_data = await self.get_word(word_id, user_id)
        word_text = word_data.get('word', '???') if word_data else '???'
        
        await self.db.execute(
            """UPDATE words
                SET repetitions = ?, easiness = ?, interval = ?, next_review = ?,
                    last_reviewed_at = ?,
                    started_at = COALESCE(started_at, ?)
                WHERE id = ? AND user_id = ?""",
            (repetitions, easiness, interval, next_review, now, now, word_id, user_id),
        )
        await self.db.commit()
        
        username = await self._get_username(user_id)
        logger.info(
            "Practice result: %s -> \"%s\" (interval: %dd, next: %s)",
            username, word_text, interval, next_review[:16].replace('T', ' ')
        )

    async def undo_word_review(
        self,
        user_id: int,
        word_id: int,
        repetitions: int,
        easiness: float,
        interval: int,
        next_review: str,
        last_reviewed_at: str | None,
        started_at: str | None,
    ) -> None:
        """Revert word statistics to a previous state."""
        word_data = await self.get_word(word_id, user_id)
        word_text = word_data.get('word', '???') if word_data else '???'
        
        await self.db.execute(
            """UPDATE words
                SET repetitions = ?, easiness = ?, interval = ?, next_review = ?,
                    last_reviewed_at = ?, started_at = ?
                WHERE id = ? AND user_id = ?""",
            (repetitions, easiness, interval, next_review, last_reviewed_at, started_at, word_id, user_id),
        )
        await self.db.commit()
        
        username = await self._get_username(user_id)
        logger.info("Practice undo: %s -> \"%s\"", username, word_text)

    # --- STATS OPERATIONS ---

    async def get_full_stats(self, user_id: int, language: str, daily_limit: int = 20, tz: ZoneInfo | None = None) -> dict:
        """Get comprehensive statistics about the user's learning progress."""
        now_utc = datetime.now(tz=UTC)
        
        # Calculate start of today and start of next day in user's local timezone
        current_tz = tz or self.tz
        today_local = datetime.now(tz=current_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        today_start = today_local.astimezone(UTC)
        next_day_start = (today_local + timedelta(days=1)).astimezone(UTC)

        cursor = await self.db.execute(
            """SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN started_at IS NOT NULL THEN 1 ELSE 0 END) as learned,
                    SUM(CASE WHEN started_at IS NOT NULL AND next_review <= ? THEN 1 ELSE 0 END) as due,
                    COUNT(CASE WHEN started_at >= ? THEN 1 END) as today_new,
                    COUNT(CASE WHEN created_at >= ? THEN 1 END) as today_added,
                    COUNT(CASE WHEN last_reviewed_at >= ? THEN 1 END) as today_reviewed,
                    COUNT(CASE WHEN started_at IS NULL THEN 1 END) as st_new,
                    COUNT(CASE WHEN started_at IS NOT NULL AND easiness <= 1.3 THEN 1 END) as difficult,
                    COUNT(CASE WHEN started_at IS NOT NULL AND interval < 30 THEN 1 END) as learning,
                    COUNT(CASE WHEN started_at IS NOT NULL AND interval >= 30 THEN 1 END) as mastered,
                    MIN(CASE WHEN started_at IS NOT NULL AND next_review > ? THEN next_review END) as next_due_at
                FROM words WHERE user_id = ? AND language = ?""",
            (
                now_utc.isoformat(),
                today_start.isoformat(),
                today_start.isoformat(),
                today_start.isoformat(),
                now_utc.isoformat(),
                user_id,
                language,
            ),
        )
        row = await cursor.fetchone()

        defaults = {
            "total": 0,
            "learned": 0,
            "due": 0,
            "today_new": 0,
            "today_added": 0,
            "today_reviewed": 0,
            "st_new": 0,
            "difficult": 0,
            "learning": 0,
            "mastered": 0,
            "next_due_at": None,
            "session_total": 0,
            "next_day_start_utc": next_day_start.isoformat(),
        }
        if row:
            data = dict(row)
            due_count = data.get("due") or 0
            new_count = data.get("st_new") or 0
            today_done = data.get("today_new") or 0
            limit = daily_limit or 20

            available_new = max(0, min(new_count, limit - today_done))
            data["session_total"] = due_count + available_new

            res = {
                **defaults,
                **{k: v for k, v in data.items() if v is not None},
                "next_day_start_utc": next_day_start.isoformat(),
            }
            return res
        return defaults

    # --- EDIT & DELETE OPERATIONS ---

    async def update_word_text(
        self,
        word_id: int,
        user_id: int,
        word: str,
        translation: str,
        example: str | None,
        level: str | None,
    ) -> bool:
        """Update the text, translation, example, or level of a word. Returns True if successful."""
        try:
            cursor = await self.db.execute(
                """UPDATE words SET word = ?, translation = ?, example = ?, level = ?
                   WHERE id = ? AND user_id = ?""",
                (word, translation, example, level, word_id, user_id),
            )
            await self.db.commit()
            if cursor.rowcount > 0:
                username = await self._get_username(user_id)
                logger.info("Word updated: %s -> \"%s\"", username, word)
            return cursor.rowcount > 0
        except aiosqlite.IntegrityError as e:
            logger.warning("Failed to update word ID %d: duplicate word/translation", word_id)
            raise ValueError("Duplicate word/translation") from e

    async def delete_word(self, word_id: int, user_id: int) -> None:
        """Delete a specific word for a user."""
        # Get info before deletion
        word_data = await self.get_word(word_id, user_id)
        word_text = word_data.get('word', '???') if word_data else '???'
        
        await self.db.execute(
            "DELETE FROM words WHERE id = ? AND user_id = ?",
            (word_id, user_id),
        )
        await self.db.commit()
        username = await self._get_username(user_id)
        logger.info("Word deleted: %s -> \"%s\" (ID %d)", username, word_text, word_id)
