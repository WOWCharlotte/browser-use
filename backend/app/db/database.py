import aiosqlite
from app.config import Config


async def init_db():
	"""Initialize the database."""
	db_path = Config.DATABASE_PATH
	db_path.parent.mkdir(parents=True, exist_ok=True)
	async with aiosqlite.connect(db_path) as db:
		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS sessions (
				id TEXT PRIMARY KEY,
				created_at TEXT NOT NULL,
				updated_at TEXT NOT NULL,
				metadata TEXT
			)
			"""
		)
		await db.commit()