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
	conn = await get_db()
	
	# Check if browser_states table exists and check its columns for migration
	try:
		async with conn.execute("PRAGMA table_info(browser_states)") as cursor:
			columns = await cursor.fetchall()
			if columns:
				has_id = any(col['name'] == 'id' for col in columns)
				if not has_id:
					# Old schema without 'id' column exists, drop it to migrate
					await conn.execute("DROP TABLE browser_states")
					await conn.commit()
	except Exception:
		pass

	await conn.executescript("""
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
			id TEXT PRIMARY KEY,
			session_id TEXT NOT NULL,
			url TEXT,
			title TEXT,
			screenshot TEXT,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (session_id) REFERENCES sessions(id)
		);
		CREATE INDEX IF NOT EXISTS idx_browser_states_session_id ON browser_states(session_id);
		CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
	""")
	await conn.commit()
	await conn.close()