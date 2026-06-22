import aiosqlite
import logging

logger = logging.getLogger(__name__)


async def init_db(db_path: str) -> aiosqlite.Connection:
    """Create all tables if they do not exist, return the open connection."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row

    await db.execute("PRAGMA foreign_keys = ON")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
    """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER NOT NULL,
            language TEXT DEFAULT 'de',
            daily_limit INTEGER DEFAULT 20,
            notification_time INTEGER DEFAULT 720,
            PRIMARY KEY (user_id, language),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            language TEXT NOT NULL,
            word TEXT NOT NULL,
            translation TEXT NOT NULL,
            example TEXT,
            level TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            repetitions INTEGER DEFAULT 0,
            easiness REAL DEFAULT 2.5,
            interval INTEGER DEFAULT 1,
            next_review TEXT NOT NULL,
            last_reviewed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, word, translation, language)
        )
    """)


    await db.execute("CREATE INDEX IF NOT EXISTS idx_words_session ON words(user_id, language, next_review, started_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_words_stats ON words(user_id, language, started_at)")

    await db.commit()

    async with db.execute("PRAGMA user_version") as cursor:
        row = await cursor.fetchone()
        current_version = row[0] if row else 0

    migrations = {
        1: "ALTER TABLE users ADD COLUMN telegram_chat_id TEXT;"
    }
    for version, sql in sorted(migrations.items()):
        if version > current_version:
            logger.info("Applying database migrations to version %d...", version)
            try:
                await db.execute(sql)
                await db.execute(f"PRAGMA user_version = {version}")
                await db.commit()
                logger.info("Database migration applied to version %d", version)
            except Exception as e:
                await db.rollback()
                logger.error("Database migration failed to apply to version %d", version)
                raise e

    return db
