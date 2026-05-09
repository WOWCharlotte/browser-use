import aiosqlite
from pathlib import Path
from app.config import Config

DB_PATH = Config.DATABASE_PATH
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


async def get_db() -> aiosqlite.Connection:
	"""Return a database connection as an async context manager."""
	conn = await aiosqlite.connect(DB_PATH, check_same_thread=False)
	conn.row_factory = aiosqlite.Row
	return conn


async def init_db():
	"""Initialize the database with sessions, messages, and browser_states tables."""
	async with await get_db() as db:
		await db.executescript("""
			CREATE TABLE IF NOT EXISTS sessions (
				id TEXT PRIMARY KEY,
				title TEXT NOT NULL,
				created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
				updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
			);
			CREATE TABLE IF NOT EXISTS messages (
				id TEXT PRIMARY KEY,
				session_id TEXT NOT NULL,
				role TEXT NOT NULL,
				content TEXT NOT NULL,
				attachments TEXT,
				created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
				FOREIGN KEY (session_id) REFERENCES sessions(id)
			);
			CREATE TABLE IF NOT EXISTS browser_states (
				session_id TEXT PRIMARY KEY,
				url TEXT,
				title TEXT,
				screenshot TEXT,
				updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
				FOREIGN KEY (session_id) REFERENCES sessions(id)
			);
		""")
		await db.commit()